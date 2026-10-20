"""Opt-in real tmux and Postgres: DEVSERVE_INTEGRATION=1 python3 -m unittest discover ...

Each test runs its own scratch tmux server (tmux -L devserve-test-<pid>) and creates only
devserve_test_<pid>* databases; cleanup kills that server and drops those databases.
DEVSERVE_TEST_PGPORT (default 5432) points the tests at a scratch cluster on localhost.
"""
import contextlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.parse
import urllib.request

SCRIPT = Path(__file__).with_name('devserve').resolve()
PGPORT = os.environ.get('DEVSERVE_TEST_PGPORT', '5432')
PYTHON = '/usr/bin/python3'
CANARY = 'devserve-unique-secret-canary'
STUB = '''import http.server, json, os, subprocess
from urllib.parse import urlsplit, unquote
u = urlsplit(os.environ['DATABASE_URL'])
env = dict(os.environ, PGHOST=u.hostname, PGPORT=str(u.port), PGUSER=unquote(u.username), PGPASSWORD=unquote(u.password or ''))
value = subprocess.check_output(['psql', '-XAt', '-d', u.path[1:], '-c', 'SELECT value FROM evidence'], env=env, text=True).strip()
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  body = json.dumps(dict(value=value, database=u.path[1:], preview=os.environ['PREVIEW'], pid=os.getpid(),
                         secret=os.environ.get('STUB_SECRET'), https=os.environ.get('HTTPS_PORT'),
                         db_user=u.username)).encode()
  self.send_response(200); self.end_headers(); self.wfile.write(body)
print('stub-ready', flush=True)
http.server.HTTPServer(('127.0.0.1', int(os.environ['PORT'])), Handler).serve_forever()
'''


def load_script():
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader('devserve_script', str(SCRIPT))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    return module


def pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


@unittest.skipUnless(os.environ.get('DEVSERVE_INTEGRATION') == '1', 'requires tmux and a throwaway Postgres login')
class IntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='devserve test-')
        self.root = Path(self.temp.name).resolve()
        self.socket = f'devserve-test-{os.getpid()}'
        self.state = self.root / 'state'
        self.env = dict(os.environ, DEVSERVE_CONFIG_DIR=str(self.root), FOREMAN_SESSION='stub-session',
                        DEVSERVE_TMUX_SOCKET=self.socket, DEVSERVE_STATE_DIR=str(self.state))
        for key in ('PGHOST', 'PGPORT', 'PGUSER', 'PGPASSWORD', 'PGDATABASE'):
            self.env.pop(key, None)
        self.pg = dict(os.environ, PGHOST='localhost', PGPORT=PGPORT, PGUSER='postgres', PGPASSWORD='postgres', PGDATABASE='postgres', PSQLRC='/dev/null')
        self.app = f'devserve_test_{os.getpid()}'
        self.source = self.app + '_source'
        self.addCleanup(self.cleanup)
        self.sql(f'CREATE DATABASE {self.source}')
        self.sql('CREATE TABLE evidence (value text); INSERT INTO evidence VALUES (\'copied-data\')', self.source)
        self.main = self.root / 'main'
        self.main.mkdir()
        self.run_cmd('git', 'init', '-q', '-b', 'main', cwd=self.main)
        (self.main / 'app.py').write_text(STUB)
        self.run_cmd('git', 'add', '.', cwd=self.main)
        self.run_cmd('git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'stub', cwd=self.main)
        self.trees = [self.root / 'one', self.root / 'two']
        for tree in self.trees:
            self.run_cmd('git', 'worktree', 'add', '-qb', tree.name, str(tree), cwd=self.main)
        self.secrets = self.root / 'secrets'
        self.secrets.write_text(f'PGHOST=localhost\nPGPORT={PGPORT}\nPGUSER=postgres\nPGPASSWORD=postgres\nSTUB_SECRET={CANARY}\n')
        self.secrets.chmod(0o600)
        self.port = self.free_block(20)
        self.config = f'''[[apps]]
name = "{self.app}"
path = "{self.main}"
ports = [{self.port}, {self.port + 9}]
start = ["{PYTHON}", "app.py"]
data = "copy"
source_database = "{self.source}"
migrate = ["/usr/bin/true"]
env_file = "{self.secrets}"
main_units = ["tcp:{self.port + 19}"]
'''
        self.write_config(self.config)
        self.transcript = []

    def free_block(self, size):
        import random
        for _ in range(50):
            # Below the ephemeral ranges (Linux 32768+, macOS 49152+), so client sockets never collide.
            first = random.randrange(20000, 32000 - size)
            if all(self.bindable(p) for p in range(first, first + size)):
                return first
        raise AssertionError('no free port block')

    @staticmethod
    def bindable(port):
        with socket.socket() as sock:
            try:
                sock.bind(('127.0.0.1', port))
                return True
            except OSError:
                return False

    def write_config(self, text):
        (self.root / 'apps.toml').write_text(text)

    def replace_config(self, old, new):
        self.assertIn(old, self.config)
        self.write_config(self.config.replace(old, new))

    def run_cmd(self, *args, **kwargs):
        return subprocess.run(args, text=True, capture_output=True, check=True, timeout=120, **kwargs).stdout.strip()

    def tmux(self, *args, check=True):
        result = subprocess.run(['tmux', '-L', self.socket, *args], text=True, capture_output=True, timeout=30)
        if check:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def sql(self, sql, db='postgres'):
        return self.run_cmd('psql', '-XAt', '-v', 'ON_ERROR_STOP=1', '-d', db, '-c', sql, env=self.pg)

    def preview_dbs(self):
        return self.sql(f"SELECT count(*) FROM pg_database WHERE datname LIKE '{self.app}_preview_%'")

    def cli(self, *args, ok=True):
        result = subprocess.run([PYTHON, str(SCRIPT), *map(str, args)], env=self.env,
                                text=True, capture_output=True, timeout=150)
        self.transcript.append('$ devserve ' + ' '.join(map(str, args)) + '\n' + result.stdout + result.stderr)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result.stdout.strip()

    def rows(self):
        return json.loads(self.cli('ls', '--json'))['previews']

    def page(self, url):
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.load(response)

    def windows(self):
        output = self.tmux('list-windows', '-t', '=devserve', '-F', '#{window_name}\t#{pane_pid}\t#{pane_dead}', check=False)
        return {line.split('\t')[0]: line.split('\t')[1:] for line in output.splitlines()}

    def pane_tree_argv(self, unit):
        name = unit.removesuffix('.service')
        pane = int(self.windows()[name][0])
        table = {}
        for line in self.run_cmd('ps', '-axww', '-o', 'pid=,ppid=,command=').splitlines():
            pid, ppid, command = line.strip().split(None, 2) + [''] * (3 - len(line.strip().split(None, 2)))
            table[int(pid)] = (int(ppid), command)
        tree, frontier = {pane}, [pane]
        while frontier:
            parent = frontier.pop()
            for pid, (ppid, _) in table.items():
                if ppid == parent and pid not in tree:
                    tree.add(pid)
                    frontier.append(pid)
        self.assertIn(pane, table, 'argv inspection must include the live pane launcher')
        self.assertGreater(len(tree), 1, 'argv inspection must include the app process')
        return {pid: table[pid][1] for pid in tree if pid in table}

    def assert_no_secrets(self, output, boundary):
        for secret in (CANARY, 'postgres:postgres', 'PGPASSWORD=postgres'):
            self.assertFalse(secret in output, f'secret in {boundary}')

    def cleanup(self):
        subprocess.run(['tmux', '-L', self.socket, 'kill-server'], capture_output=True)
        time.sleep(0.3)
        Path(os.environ.get('TMUX_TMPDIR', '/tmp'), f'tmux-{os.getuid()}', self.socket).resolve().unlink(missing_ok=True)
        dbs = self.sql(f"SELECT datname FROM pg_database WHERE datname LIKE '{self.app}%'")
        for db in dbs.splitlines():
            self.sql(f'DROP DATABASE "{db}" WITH (FORCE)')
        self.temp.cleanup()

    def test_copied_preview_lifecycle_and_secret_boundary(self):
        url = self.cli('up', self.trees[0])
        self.assertTrue(url.startswith('http://localhost:'), url)
        page = self.page(url)
        self.assertEqual((page['value'], page['preview'], page['secret']), ('copied-data', '1', CANARY))
        self.cli('up', self.trees[1])
        rows = self.rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(set(rows[0]), {'unit', 'app', 'worktree', 'branch', 'port', 'url', 'database', 'owner',
                                        'state', 'missing'})
        self.assertEqual(len({r['port'] for r in rows}), 2)
        self.assertEqual(len({r['database'] for r in rows}), 2)
        first = next(r for r in rows if r['worktree'] == str(self.trees[0]))
        self.assertRegex(first['unit'], r'^devserve-.*\.service$')
        self.assertEqual((first['owner'], first['branch'], first['state']), ('stub-session', 'one', 'running'))
        self.assertEqual(set(self.windows()), {r['unit'].removesuffix('.service') for r in rows})
        self.assertIn(f'tcp:{self.port + 19}', self.cli('ls'))
        unrelated = subprocess.Popen([PYTHON, '-c', 'import sys; sys.stdin.read()', CANARY], stdin=subprocess.PIPE)
        self.addCleanup(lambda: unrelated.communicate(timeout=5))
        for row in rows:
            for argv in self.pane_tree_argv(row['unit']).values():
                self.assert_no_secrets(argv, 'pane argv')
        for scope in (['-g'], ['-t', '=devserve']):
            self.assert_no_secrets(self.tmux('show-environment', *scope), 'tmux environment')
        state_text = (self.state / 'previews.json').read_text()
        self.assertIn(first['unit'], state_text)
        self.assert_no_secrets(state_text, 'state file')
        self.assert_no_secrets(json.dumps(rows), 'ls --json')
        self.assertIn('stub-ready', self.cli('logs', first['unit']))
        self.cli('down', first['unit'])
        self.assertNotIn(first['unit'].removesuffix('.service'), self.windows())
        self.assertEqual(self.sql(f"SELECT count(*) FROM pg_database WHERE datname = '{first['database']}'"), '1')
        self.assertEqual(next(r for r in self.rows() if r['unit'] == first['unit'])['state'], 'stopped')
        self.cli('down', first['unit'], '--drop-db')
        self.assertEqual(self.sql(f"SELECT count(*) FROM pg_database WHERE datname = '{first['database']}'"), '0')
        shutil.rmtree(self.trees[1])
        self.assertTrue(self.rows()[0]['missing'])
        self.cli('gc')
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.windows(), {})
        self.assertEqual(self.preview_dbs(), '0')
        print('\n'.join(self.transcript))

    def test_consumers_accept_the_listing_unchanged(self):
        self.cli('up', self.trees[0])
        for row in self.rows():  # Foreman.Previews.Devserve.valid?/1, transcribed
            self.assertRegex(row['unit'], r'\Adevserve-[a-zA-Z0-9_.-]+\.service\Z')
            self.assertTrue(Path(row['worktree']).is_absolute())
            self.assertIn(row['state'], ('starting', 'running', 'failed', 'stopped'))
            self.assertIsInstance(row['missing'], bool)
            url = urllib.parse.urlsplit(row['url'])
            self.assertEqual((url.scheme, url.hostname, url.username), ('http', 'localhost', None))
            self.assertTrue(1024 <= url.port <= 65535)
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        (bin_dir / 'devserve').symlink_to(SCRIPT)
        cleanup = SCRIPT.parents[2] / 'dispatch/scripts/preview-cleanup.py'
        env = dict(self.env, PATH=f'{bin_dir}:{os.environ["PATH"]}')
        result = subprocess.run([PYTHON, str(cleanup), 'stub-session'], env=env, text=True, capture_output=True, timeout=200)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.preview_dbs(), '0')

    def test_argv_inspection_detects_secret_in_preview_child(self):
        self.replace_config(f'start = ["{PYTHON}", "app.py"]', 'start = ' + json.dumps([PYTHON, 'app.py', CANARY]))
        self.cli('up', self.trees[0])
        commands = self.pane_tree_argv(self.rows()[0]['unit'])
        with self.assertRaisesRegex(AssertionError, 'secret in pane argv'):
            for argv in commands.values():
                self.assert_no_secrets(argv, 'pane argv')
        self.cli('down', self.rows()[0]['unit'], '--drop-db')

    def test_killing_the_tmux_server_stops_previews_and_gc_drops_them(self):
        url = self.cli('up', self.trees[0])
        app_pid = self.page(url)['pid']
        row = self.rows()[0]
        self.tmux('kill-server')
        deadline = time.monotonic() + 10
        while pid_alive(app_pid) and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertFalse(pid_alive(app_pid), 'app outlived its tmux server')
        self.assertEqual(self.rows()[0]['state'], 'stopped')
        report = self.cli('gc')
        self.assertIn(row['database'], report)
        self.assertEqual(self.sql(f"SELECT count(*) FROM pg_database WHERE datname = '{row['database']}'"), '1')
        self.cli('gc', '--stopped')
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.preview_dbs(), '0')

    def test_launcher_killed_without_cleanup_reads_stopped(self):
        self.cli('up', self.trees[0])
        row = self.rows()[0]
        pane = int(self.windows()[row['unit'].removesuffix('.service')][0])
        os.kill(pane, signal.SIGKILL)
        deadline = time.monotonic() + 5
        while self.rows()[0]['state'] != 'stopped' and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertEqual(self.rows()[0]['state'], 'stopped')
        self.cli('down', row['unit'], '--drop-db')
        self.assertEqual(self.preview_dbs(), '0')

    def test_restart_keeps_data_but_runs_migrations(self):
        self.cli('up', self.trees[0])
        row = self.rows()[0]
        self.sql("INSERT INTO evidence VALUES ('preview-only')", row['database'])
        self.cli('down', row['unit'])
        self.replace_config('migrate = ["/usr/bin/true"]', 'migrate = ' + json.dumps(
            [PYTHON, '-c', "import os, pathlib; pathlib.Path('migrated').write_text(os.environ['PREVIEW'])"]))
        self.cli('up', self.trees[0])
        self.assertEqual((self.trees[0] / 'migrated').read_text(), '1', 'restart must run migrate')
        self.assertEqual(self.sql('SELECT count(*) FROM evidence', row['database']), '2')
        self.assertEqual(self.sql('SELECT count(*) FROM evidence', self.source), '1')
        self.cli('down', row['unit'], '--drop-db')

    def test_failed_start_rolls_back_owned_database_and_keeps_window(self):
        self.replace_config(f'start = ["{PYTHON}", "app.py"]', 'start = ["/usr/bin/false"]')
        self.cli('up', self.trees[0], ok=False)
        row = self.rows()[0]
        self.assertEqual(row['state'], 'failed')
        self.assertEqual(self.windows()[row['unit'].removesuffix('.service')][1], '1', 'dead pane kept for inspection')
        self.assertEqual(self.preview_dbs(), '0')
        self.assertIn('failed', self.cli('logs', row['unit']))
        self.cli('down', row['unit'], '--drop-db')
        self.assertEqual(self.windows(), {})
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.sql('SELECT value FROM evidence', self.source), 'copied-data')

    def test_rollback_refusal_still_records_failed_state(self):
        code = ('import os, pathlib, subprocess, urllib.parse; '
                'db = urllib.parse.urlsplit(os.environ["DATABASE_URL"]).path[1:]; '
                'subprocess.run(["psql", "-X", "-d", "postgres", "-c", '
                '\'COMMENT ON DATABASE "\' + db + \'" IS \\\'manual-owner\\\'\'], check=True); '
                'pathlib.Path("ownership-changed").touch()')
        self.replace_config(f'start = ["{PYTHON}", "app.py"]', 'start = ' + json.dumps([PYTHON, '-c', code]))
        self.cli('up', self.trees[0], ok=False)
        self.assertTrue((self.trees[0] / 'ownership-changed').exists())
        row = self.rows()[0]
        self.assertEqual(row['state'], 'failed')
        self.cli('down', row['unit'], '--drop-db', ok=False)
        self.assertEqual(self.sql(f"SELECT count(*) FROM pg_database WHERE datname = '{row['database']}'"), '1')

    def test_down_failed_preview_records_stopped(self):
        self.replace_config(f'start = ["{PYTHON}", "app.py"]', 'start = ["/usr/bin/false"]')
        self.cli('up', self.trees[0], ok=False)
        row = self.rows()[0]
        self.cli('down', row['unit'])
        self.assertEqual(self.rows()[0]['state'], 'stopped')
        self.cli('down', row['unit'], '--drop-db')

    def test_migration_failure_removes_new_database(self):
        self.replace_config('migrate = ["/usr/bin/true"]', 'migrate = ["/usr/bin/false"]')
        self.cli('up', self.trees[0], ok=False)
        self.assertEqual(self.preview_dbs(), '0')
        self.cli('down', self.rows()[0]['unit'], '--drop-db')

    def test_failed_start_kills_child_process_group(self):
        code = f"import subprocess; subprocess.Popen(['{shutil.which('sleep')}', '9797'])"
        self.replace_config(f'start = ["{PYTHON}", "app.py"]', 'start = ' + json.dumps([PYTHON, '-c', code]))
        self.cli('up', self.trees[0], ok=False)
        leftovers = subprocess.run(['pgrep', '-f', 'sleep 9797'], capture_output=True, text=True).stdout.split()
        for pid in leftovers:
            os.kill(int(pid), signal.SIGKILL)
        self.assertEqual(leftovers, [], 'failed start left a process')
        self.cli('down', self.rows()[0]['unit'], '--drop-db')

    def test_unowned_collision_is_neither_started_nor_dropped(self):
        unit, database = load_script().names(self.app, self.trees[0])
        self.sql(f'CREATE DATABASE "{database}"')
        self.sql('CREATE TABLE precious (value text)', database)
        self.cli('up', self.trees[0], ok=False)
        self.cli('down', unit, '--drop-db', ok=False)
        self.assertEqual(self.sql("SELECT count(*) FROM pg_tables WHERE tablename = 'precious'", database), '1')

    def test_interrupt_during_migration_rolls_back(self):
        code = 'import pathlib, time; pathlib.Path("migrating").touch(); time.sleep(90)'
        self.replace_config('migrate = ["/usr/bin/true"]', 'migrate = ' + json.dumps([PYTHON, '-c', code]))
        process = subprocess.Popen([PYTHON, str(SCRIPT), 'up', str(self.trees[0])], env=self.env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 10
            while not (self.trees[0] / 'migrating').exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue((self.trees[0] / 'migrating').exists())
            process.send_signal(signal.SIGINT)
            process.communicate(timeout=30)
            self.assertNotEqual(process.returncode, 0)
            self.assertEqual(self.preview_dbs(), '0')
            self.assertEqual(self.rows()[0]['state'], 'stopped')
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=5)
        self.cli('down', self.rows()[0]['unit'], '--drop-db')

    def slow_migrate(self, seconds_for_one, seconds_for_others=0):
        code = ('import os, pathlib, time; pathlib.Path("migrating").touch(); '
                f'time.sleep({seconds_for_one} if os.path.basename(os.getcwd()) == "one" else {seconds_for_others})')
        self.replace_config('migrate = ["/usr/bin/true"]', 'migrate = ' + json.dumps([PYTHON, '-c', code]))

    def background_up(self, tree):
        process = subprocess.Popen([PYTHON, str(SCRIPT), 'up', str(tree)], env=self.env, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(lambda: process.poll() is None and process.kill())
        deadline = time.monotonic() + 10
        while not (tree / 'migrating').exists():
            self.assertLess(time.monotonic(), deadline, 'up never reached migrate')
            time.sleep(0.05)
        return process

    def test_up_does_not_hold_the_lock_while_waiting(self):
        self.slow_migrate(90)
        first = self.background_up(self.trees[0])
        started = time.monotonic()
        self.cli('up', self.trees[1])
        one = next(r for r in self.rows() if r['worktree'] == str(self.trees[0]))
        self.assertEqual(one['state'], 'starting')
        self.cli('down', one['unit'])
        self.assertLess(time.monotonic() - started, 30, 'other commands waited for the starting preview')
        _, err = first.communicate(timeout=30)
        self.assertNotEqual(first.returncode, 0)
        self.assertIn('preview', err)
        self.assertEqual(next(r for r in self.rows() if r['unit'] == one['unit'])['state'], 'stopped')
        self.assertEqual(self.sql(f"SELECT count(*) FROM pg_database WHERE datname = '{one['database']}'"), '0')
        for row in self.rows():
            self.cli('down', row['unit'], '--drop-db')

    def test_up_on_a_starting_preview_waits_for_the_same_preview(self):
        self.slow_migrate(3)
        first = self.background_up(self.trees[0])
        url = self.cli('up', self.trees[0])
        out, _ = first.communicate(timeout=60)
        self.assertEqual((first.returncode, out.strip()), (0, url))
        self.assertEqual([r['state'] for r in self.rows()], ['running'])
        self.cli('down', self.rows()[0]['unit'], '--drop-db')

    def test_migration_output_is_in_the_preview_log(self):
        code = 'import sys; print("migrate-canary-out"); print("migrate-canary-err", file=sys.stderr); sys.exit(3)'
        self.replace_config('migrate = ["/usr/bin/true"]', 'migrate = ' + json.dumps([PYTHON, '-c', code]))
        self.cli('up', self.trees[0], ok=False)
        log = self.cli('logs', self.rows()[0]['unit'])
        for text in ('migrate-canary-out', 'migrate-canary-err', 'exit 3'):
            self.assertIn(text, log)
        self.cli('down', self.rows()[0]['unit'], '--drop-db')

    def test_gc_continues_past_a_preview_it_cannot_clean(self):
        self.cli('up', self.trees[0])
        self.cli('down', self.rows()[0]['unit'])
        other = self.root / 'secrets2'
        other.write_text(self.secrets.read_text())
        other.chmod(0o600)
        self.replace_config(f'env_file = "{self.secrets}"', f'env_file = "{other}"')
        self.cli('up', self.trees[1])
        rows = {r['worktree']: r for r in self.rows()}
        self.secrets.chmod(0o644)
        for tree in self.trees:
            shutil.rmtree(tree)
        self.cli('gc', ok=False)
        self.assertIn('0600', self.transcript[-1])
        self.assertEqual([r['unit'] for r in self.rows()], [rows[str(self.trees[0])]['unit']])
        self.assertEqual(self.sql(f"SELECT count(*) FROM pg_database WHERE datname = '{rows[str(self.trees[1])]['database']}'"), '0')
        self.secrets.chmod(0o600)
        self.cli('gc')
        self.assertEqual(self.preview_dbs(), '0')

    def test_gc_finds_previews_known_only_by_their_database_comment(self):
        import hashlib
        module = load_script()
        databases = []
        for tree in self.trees:
            unit, database = module.names(self.app, tree)
            self.sql(f'CREATE DATABASE "{database}"')
            self.sql(f"COMMENT ON DATABASE \"{database}\" IS 'devserve:v1:{unit}:"
                     f"{hashlib.sha256(str(tree.resolve()).encode()).hexdigest()}'")
            databases.append(database)
        forged = f'{self.app}_preview_x_000000000000'
        self.sql(f'CREATE DATABASE "{forged}"')
        fake_hash = 'f' * 64
        self.sql(f"COMMENT ON DATABASE \"{forged}\" IS 'devserve:v1:devserve-{self.app}-x-000000000000.service:{fake_hash}'")
        shutil.rmtree(self.trees[1])
        report = self.cli('gc')
        self.assertIn(databases[0], report)
        exists = "SELECT count(*) FROM pg_database WHERE datname = '{}'"
        self.assertEqual([self.sql(exists.format(db)) for db in databases + [forged]], ['1', '0', '1'])
        self.cli('gc', '--stopped')
        self.assertEqual([self.sql(exists.format(db)) for db in databases + [forged]], ['0', '0', '1'])

    def test_listing_with_systemd_main_units_still_parses(self):
        self.write_config(self.config.replace(f'main_units = ["tcp:{self.port + 19}"]',
                                              'main_units = ["foreman-web.service"]'))
        result = subprocess.run([PYTHON, str(SCRIPT), 'ls', '--json'], env=self.env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(json.loads(result.stdout), dict(previews=[], main_units=[]))
        self.cli('ls')
        self.assertIn('warning: ', self.transcript[-1])
        self.assertIn('foreman-web.service skipped', self.transcript[-1])

    def test_worktree_path_is_literal_not_a_tmux_format(self):
        tree = self.root / 'percent%h #{pane_id} #(touch pwned)'
        self.run_cmd('git', 'worktree', 'add', '-qb', 'literal', str(tree), cwd=self.main)
        self.cli('up', tree)
        row = self.rows()[0]
        self.assertEqual((row['worktree'], row['state']), (str(tree), 'running'))
        self.assertFalse((self.root / 'pwned').exists())
        self.cli('down', row['unit'], '--drop-db')

    def test_port_range_exhaustion_never_spills_into_other_app(self):
        other = self.root / 'other'
        other.mkdir()
        self.run_cmd('git', 'init', '-q', cwd=other)
        config = self.config.replace(f'ports = [{self.port}, {self.port + 9}]', f'ports = [{self.port}, {self.port}]')
        config += self.config.replace(f'name = "{self.app}"', 'name = "other"').replace(
            f'path = "{self.main}"', f'path = "{other}"').replace(
            f'ports = [{self.port}, {self.port + 9}]', f'ports = [{self.port + 10}, {self.port + 18}]').replace(
            f'tcp:{self.port + 19}', f'tcp:{self.port + 18}')
        self.write_config(config)
        self.cli('up', self.trees[0])
        self.cli('down', self.rows()[0]['unit'])
        self.cli('up', self.trees[1], ok=False)
        self.assertEqual([r['port'] for r in self.rows()], [self.port])
        self.cli('down', self.rows()[0]['unit'], '--drop-db')

    def test_extra_ports_reserve_a_block_per_preview(self):
        self.replace_config('main_units', 'extra_ports = ["HTTPS_PORT"]\nmain_units')
        first = self.page(self.cli('up', self.trees[0]))
        second_url = self.cli('up', self.trees[1])
        second = self.page(second_url)
        ports = sorted(r['port'] for r in self.rows())
        self.assertEqual(ports, [self.port, self.port + 2])
        self.assertEqual({first['https'], second['https']}, {str(self.port + 1), str(self.port + 3)})
        for row in self.rows():
            self.cli('down', row['unit'], '--drop-db')

    def test_main_units_are_listed_and_tailed_without_mutation(self):
        self.write_config(self.config.replace(f'main_units = ["tcp:{self.port + 19}"]',
                                              f'main_units = ["tcp:{self.port + 19}", "tmux:mainsess:web"]'))
        self.tmux('new-session', '-d', '-s', 'mainsess', '-n', 'web', 'echo stub-main-log; exec sleep 300')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', self.port + 19))
            listener.listen()
            time.sleep(0.3)
            listing = json.loads(self.cli('ls', '--json'))
            self.assertEqual(listing['main_units'], [
                dict(app=self.app, unit=f'tcp:{self.port + 19}', state='active'),
                dict(app=self.app, unit='tmux:mainsess:web', state='active')])
        self.assertIn('stub-main-log', self.cli('logs', self.app))
        self.cli('gc')
        self.assertEqual(json.loads(self.cli('ls', '--json'))['main_units'][0]['state'], 'inactive')
        self.assertIn('web', self.tmux('list-windows', '-t', '=mainsess', '-F', '#{window_name}'))

    def test_logs_follow_receives_new_http_request(self):
        import selectors
        url = self.cli('up', self.trees[0])
        row = self.rows()[0]
        process = subprocess.Popen([PYTHON, str(SCRIPT), 'logs', row['unit'], '-f'],
                                   env=self.env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            urllib.request.urlopen(url + '/follow-canary', timeout=5).read()
            output = b''
            deadline = time.monotonic() + 10
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while b'follow-canary' not in output and time.monotonic() < deadline:
                    if selector.select(timeout=0.2):
                        output += os.read(process.stdout.fileno(), 65536)
            self.assertIn(b'follow-canary', output)
        finally:
            process.terminate()
            process.communicate(timeout=5)
        self.assertIn('follow-canary', self.tmux('capture-pane', '-p', '-t', '=devserve:' + row['unit'].removesuffix('.service')))
        self.cli('down', row['unit'], '--drop-db')

    def fresh_command(self, sql):
        code = ('import os, subprocess, urllib.parse; '
                'u = urllib.parse.urlsplit(os.environ["DATABASE_URL"]); '
                'env = dict(os.environ, PGDATABASE=u.path[1:], PGUSER=u.username, PGPASSWORD=urllib.parse.unquote(u.password or ""), PGHOST=u.hostname, PGPORT=str(u.port)); '
                f'subprocess.run(["psql", "-X", "-c", {sql!r}], check=True, env=env)')
        return json.dumps([PYTHON, '-c', code])

    def test_fresh_migrates_then_seeds(self):
        config = self.config.replace('data = "copy"', 'data = "fresh"').replace(
            'migrate = ["/usr/bin/true"]',
            'migrate = ' + self.fresh_command('CREATE TABLE evidence (value text)') + '\nseed = ' +
            self.fresh_command("INSERT INTO evidence VALUES ('seeded')"))
        self.write_config(config)
        self.assertEqual(self.page(self.cli('up', self.trees[0]))['value'], 'seeded')
        self.cli('down', self.rows()[0]['unit'], '--drop-db')

    def template_config(self):
        return self.config.replace('data = "copy"', f'data = "template"\ntemplate_database = "{self.app}_base"')

    def test_template_clones_a_refreshed_base_and_refuses_while_it_has_connections(self):
        self.write_config(self.template_config())
        self.cli('up', self.trees[0], ok=False)
        self.assertIn('base refresh', self.cli('logs', self.rows()[0]['unit']))
        with self.holding(self.source):
            self.cli('base', 'refresh', self.app, ok=False)
            self.assertIn('--dump', self.transcript[-1])
            self.assertIn('refreshed', self.cli('base', 'refresh', self.app, '--dump'))
        self.assertIn('refreshed', self.cli('base', 'refresh', self.app))
        self.assertEqual(self.sql(f"SELECT datallowconn FROM pg_database WHERE datname = '{self.app}_base'"), 'f')
        self.sql("INSERT INTO evidence VALUES ('after-refresh')", self.source)
        url = self.cli('up', self.trees[0])
        self.assertEqual(self.page(url)['value'], 'copied-data')
        self.sql(f'ALTER DATABASE "{self.app}_base" WITH ALLOW_CONNECTIONS true')
        holder = subprocess.Popen(['psql', '-X', '-d', f'{self.app}_base', '-c', 'SELECT pg_sleep(60)'], env=self.pg,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 10
            while self.sql(f"SELECT count(*) FROM pg_stat_activity WHERE datname = '{self.app}_base'") == '0':
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.1)
            self.cli('up', self.trees[1], ok=False)
            two = next(r for r in self.rows() if r['worktree'] == str(self.trees[1]))
            self.assertEqual(two['state'], 'failed')
            self.assertIn('has 1 connection', self.cli('logs', two['unit']))
            self.cli('base', 'refresh', self.app, ok=False)
            self.assertIn('connection', self.transcript[-1])
            self.assertEqual(self.sql(f"SELECT count(*) FROM pg_database WHERE datname = '{self.app}_base_next'"), '0')
        finally:
            holder.kill()
            holder.communicate()
            self.sql(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{self.app}_base'")
        self.cli('base', 'refresh', self.app)
        self.assertEqual(self.sql(f"SELECT string_agg(datname, ',') FROM pg_database WHERE datname LIKE '{self.app}_base%'"),
                         f'{self.app}_base')
        self.cli('down', two['unit'], '--drop-db')
        self.cli('up', self.trees[1])
        two = next(r for r in self.rows() if r['worktree'] == str(self.trees[1]))
        self.assertEqual(self.sql("SELECT string_agg(value, ',' ORDER BY value) FROM evidence", two['database']),
                         'after-refresh,copied-data')
        for row in self.rows():
            self.cli('down', row['unit'], '--drop-db')
        self.assertEqual(self.preview_dbs(), '0')

    @contextlib.contextmanager
    def holding(self, database):
        holder = subprocess.Popen(['psql', '-X', '-d', database, '-c', 'SELECT pg_sleep(60)'], env=self.pg,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 10
            while self.sql(f"SELECT count(*) FROM pg_stat_activity WHERE datname = '{database}'") == '0':
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.1)
            yield
        finally:
            holder.kill()
            holder.communicate()
            self.sql(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{database}'")

    def test_base_refresh_copies_files_so_unrestorable_data_survives(self):
        # Rows loaded with triggers off violate a validated foreign key, as in a dev database restored from
        # a dump with --disable-triggers; pg_restore cannot re-add that constraint.
        self.sql('CREATE TABLE parent (id int PRIMARY KEY); CREATE TABLE child (parent_id int REFERENCES parent);'
                 "SET session_replication_role = replica; INSERT INTO child VALUES (42);", self.source)
        self.write_config(self.template_config())
        self.cli('base', 'refresh', self.app, '--dump', ok=False)
        self.assertEqual(self.sql(f"SELECT count(*) FROM pg_database WHERE datname LIKE '{self.app}_base%'"), '0')
        self.assertIn('refreshed', self.cli('base', 'refresh', self.app))
        self.sql(f'ALTER DATABASE "{self.app}_base" WITH ALLOW_CONNECTIONS true')
        self.assertEqual(self.sql('SELECT count(*) FROM child', f'{self.app}_base'), '1')

    def test_base_refresh_refuses_an_unowned_base(self):
        self.write_config(self.template_config())
        self.sql(f'CREATE DATABASE "{self.app}_base"')
        self.cli('base', 'refresh', self.app, ok=False)
        self.assertIn('not created by devserve', self.transcript[-1])
        self.assertEqual(self.sql(f"SELECT count(*) FROM pg_database WHERE datname = '{self.app}_base'"), '1')

    def test_unexported_env_file_supplies_only_database_credentials(self):
        self.secrets.write_text(f'DATABASE_URL=ecto://postgres:postgres@localhost:{PGPORT}/ignored\n'
                                f'STUB_SECRET={CANARY}\nDYNAMIC=$(cat /nonexistent)\n')
        self.replace_config('main_units', 'env_file_export = false\nmain_units')
        page = self.page(self.cli('up', self.trees[0]))
        self.assertEqual((page['value'], page['secret'], page['db_user']), ('copied-data', None, 'postgres'))
        self.cli('down', self.rows()[0]['unit'], '--drop-db')

    def test_readable_env_file_is_refused(self):
        self.secrets.chmod(0o644)
        self.cli('up', self.trees[0], ok=False)
        self.assertIn('0600', self.cli('logs', self.rows()[0]['unit']))
        self.assertEqual(self.preview_dbs(), '0')


@unittest.skipUnless(os.environ.get('DEVSERVE_BENCH_SOURCE'), 'set DEVSERVE_BENCH_SOURCE=<large db> to time copy vs template')
class TemplateBenchmark(unittest.TestCase):
    """Reads DEVSERVE_BENCH_SOURCE only through pg_dump; all written databases are devserve_test_bench_*."""

    def test_template_clone_is_much_faster_than_copy(self):
        pg = dict(os.environ, PSQLRC='/dev/null')
        if 'DEVSERVE_TEST_PGPORT' in os.environ:
            pg.update(PGHOST='localhost', PGPORT=PGPORT, PGUSER='postgres', PGPASSWORD='postgres')
        source = os.environ['DEVSERVE_BENCH_SOURCE']
        base, clone, plain = 'devserve_test_bench_base', 'devserve_test_bench_clone', 'devserve_test_bench_plain'

        def sql(statement):
            return subprocess.run(['psql', '-XAt', '-v', 'ON_ERROR_STOP=1', '-d', 'postgres'], input=statement,
                                  env=pg, text=True, capture_output=True, check=True).stdout.strip()

        def drop_all():
            for db in (base, clone, plain):
                sql(f'DROP DATABASE IF EXISTS "{db}" WITH (FORCE);')
        self.addCleanup(drop_all)
        drop_all()
        with tempfile.TemporaryDirectory(prefix='devserve-bench-') as directory:
            dump = str(Path(directory) / 'data.dump')
            started = time.monotonic()
            sql(f'CREATE DATABASE "{base}";')
            subprocess.run(['pg_dump', '--format=custom', '--no-owner', '--no-acl', '--file', dump, source], env=pg, check=True)
            # No --exit-on-error: a dev database may hold rows pg_restore cannot re-validate; time the full load.
            subprocess.run(['pg_restore', '--no-owner', '--no-acl', '--dbname', base, dump], env=pg,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            copy_seconds = time.monotonic() - started
        size = sql(f"SELECT pg_size_pretty(pg_database_size('{base}'));")
        started = time.monotonic()
        sql(f'SET file_copy_method = clone;\nCREATE DATABASE "{clone}" TEMPLATE "{base}" STRATEGY FILE_COPY;')
        clone_seconds = time.monotonic() - started
        started = time.monotonic()
        sql(f'CREATE DATABASE "{plain}" TEMPLATE "{base}" STRATEGY FILE_COPY;')
        file_copy_seconds = time.monotonic() - started
        print(f'\nbench {source} -> {size}: copy (dump+restore) {copy_seconds:.1f}s, '
              f'template clone {clone_seconds:.1f}s, template file_copy {file_copy_seconds:.1f}s')
        self.assertLess(clone_seconds * 5, copy_seconds)


if __name__ == '__main__':
    unittest.main()
