import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('devserve')
loader = importlib.machinery.SourceFileLoader('devserve', str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
d = importlib.util.module_from_spec(spec)
loader.exec_module(d)

try:
    import tomllib
except ImportError:  # Python < 3.11: the parity check needs a newer interpreter.
    tomllib = None


class ConfigTest(unittest.TestCase):
    def config(self, text):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'apps.toml'
            path.write_text(text)
            return d.load_config(path)

    def test_valid_copy_and_overlap_rejected_with_both_names(self):
        app = '''[[apps]]
name = "stub"
path = "/tmp/main"
ports = [43000, 43010]
start = ["python3", "app.py"]
data = "copy"
source_database = "devserve_test_source"
migrate = ["true"]
'''
        self.assertEqual(self.config(app)['apps'][0]['name'], 'stub')
        for field in ('name', 'path', 'ports', 'start', 'data', 'source_database', 'migrate'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.config('\n'.join(line for line in app.splitlines() if not line.startswith(field + ' =')))
        with self.assertRaises(ValueError):
            self.config(app.replace('source_database = "devserve_test_source"', 'source_database = 12'))
        with self.assertRaisesRegex(ValueError, 'stub.*other'):
            self.config(app + app.replace('"stub"', '"other"'))
        with self.assertRaisesRegex(ValueError, 'stub.*other'):
            self.config(app + app.replace('"stub"', '"other"').replace('[43000, 43010]', '[43010, 43020]'))

    def test_required_fields_absolute_paths_and_types(self):
        app = '''[[apps]]
name = "stub"
path = "/tmp/main"
ports = [43000, 43010]
start = ["true"]
data = "fresh"
migrate = ["true"]
seed = ["true"]
'''
        for old, new in [('path = "/tmp/main"', 'path = "relative"'),
                         ('seed = ["true"]', ''), ('ports = [43000, 43010]', 'ports = [true, 43010]'),
                         ('start = ["true"]', 'start = "true"'),
                         ('name = "stub"', 'name = "../bad"')]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                self.config(app.replace(old, new))
        with self.assertRaises(ValueError):
            self.config(app + 'env_file = "relative"\n')

    REPORT = '''# ReportSystem-shaped entry
tmux_socket = "devserve-test"

[[apps]]
name = "report_system"
path = "/Users/me/dev/work/ReportSystem"
ports = [5110, 5199]   # PORT, HTTPS_PORT pairs
extra_ports = ["HTTPS_PORT"]
start = [
  "/Users/me/.asdf/shims/mix",
  "phx.server",
]
env_file = "/Users/me/dev/work/ReportSystem/.env"
env_file_export = false
env = { MIX_ENV = "dev", PATH = "/opt/homebrew/bin:/usr/bin:/bin" }
data = "template"
template_database = "report_system_preview_base"
source_database = "report_system_dev"
migrate = ["/Users/me/.asdf/shims/mix", "ecto.migrate"]
timeout = 900
main_units = ["tcp:5100", "tmux:work:server.0"]
'''

    def test_template_entry_with_extra_ports_and_main_targets(self):
        config = self.config(self.REPORT)
        self.assertEqual(config['tmux_socket'], 'devserve-test')
        app = config['apps'][0]
        self.assertEqual(app['extra_ports'], ['HTTPS_PORT'])
        self.assertEqual(app['start'], ['/Users/me/.asdf/shims/mix', 'phx.server'])
        self.assertEqual(app['env'], {'MIX_ENV': 'dev', 'PATH': '/opt/homebrew/bin:/usr/bin:/bin'})
        self.assertIs(app['env_file_export'], False)
        self.assertEqual(app['timeout'], 900)
        self.assertEqual(app['main_units'], ['tcp:5100', 'tmux:work:server.0'])
        self.assertEqual(self.config(self.REPORT.replace('timeout = 900\n', ''))['apps'][0]['timeout'], 120)

    def test_template_rules(self):
        for old, new, message in [
                ('template_database = "report_system_preview_base"\n', '', 'template_database'),
                ('"report_system_preview_base"', '"report_system_dev"', 'differ'),
                ('"report_system_preview_base"', '"' + 'b' * 59 + '"', 'template_database'),
                ('timeout = 900', 'timeout = 0', 'timeout'),
                ('["HTTPS_PORT"]', '["PORT"]', 'extra_ports'),
                ('["HTTPS_PORT"]', '["HTTPS_PORT", "HTTPS_PORT"]', 'extra_ports'),
                ('env_file_export = false', 'env_file_export = "no"', 'env_file_export')]:
            with self.subTest(new=new), self.assertRaisesRegex(ValueError, message):
                self.config(self.REPORT.replace(old, new))

    def test_systemd_main_units_are_skipped_with_a_warning(self):
        config = self.config(self.REPORT.replace('"tcp:5100"', '"foreman-web.service", "tcp:5100"'))
        self.assertEqual(config['apps'][0]['main_units'], ['tcp:5100', 'tmux:work:server.0'])
        self.assertEqual(len(config['warnings']), 1)
        self.assertIn('foreman-web.service', config['warnings'][0])
        self.assertIn('tcp:<port> or tmux:<target>', config['warnings'][0])
        self.assertEqual(self.config(self.REPORT)['warnings'], [])
        for bad in ('"tcp:80"', '"tmux:"', '"tmux:a b"', '"tcp:x"'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.config(self.REPORT.replace('"tcp:5100"', bad))


class OrphanTest(unittest.TestCase):
    def comment(self, unit, worktree):
        import hashlib
        return f'devserve:v1:{unit}:' + hashlib.sha256(str(Path(worktree).resolve()).encode()).hexdigest()

    def test_identity_is_rebuilt_from_name_and_comment(self):
        unit, database = d.names('stub', Path('/tmp/gone/feature'))
        found = d.orphan_identity('stub', database, self.comment(unit, '/tmp/gone/feature'))
        self.assertEqual(found, dict(unit=unit, database=database, worktree_hash=self.comment(unit, '/tmp/gone/feature')[-64:]))

    def test_forged_or_foreign_comments_are_ignored(self):
        unit, database = d.names('stub', Path('/tmp/gone/feature'))
        other_unit, other_db = d.names('stub', Path('/tmp/other/feature'))
        cases = [
            (database, self.comment(unit, '/tmp/other/feature')),       # hash does not match the name suffix
            (database, self.comment(other_unit, '/tmp/gone/feature')),  # unit does not match the database
            (other_db, self.comment(unit, '/tmp/gone/feature')),
            ('stubx_preview_feature_' + database[-12:], self.comment(unit, '/tmp/gone/feature')),
            (database, 'manual-owner'),
            (database, ''),
        ]
        for name, comment in cases:
            with self.subTest(name=name, comment=comment):
                self.assertIsNone(d.orphan_identity('stub', name, comment))
        unit2, database2 = d.names('stub2', Path('/tmp/gone/feature'))
        self.assertIsNone(d.orphan_identity('stub', database2, self.comment(unit2, '/tmp/gone/feature')))


class PrepareTest(unittest.TestCase):
    def test_create_and_comment_cannot_be_split_by_a_stop_signal(self):
        import signal
        from unittest import mock
        seen = []

        def fake_sql(statement, tools):
            if 'CREATE DATABASE' in statement or 'COMMENT ON' in statement:
                mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])
                seen.append(all(s in mask for s in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)))
            return '0' if 'count(*)' in statement else ''
        unit, database = d.names('stub', Path('/tmp/a/feature'))
        meta = dict(app='stub', unit=unit, worktree='/tmp/a/feature', database=database, port=43000,
                    config=dict(data='fresh', migrate=['true'], seed=['true'], env={}, extra_ports=[], timeout=10))
        with mock.patch.object(d, 'sql', fake_sql), mock.patch.object(d, 'run_logged', lambda *a, **k: None):
            d.prepare(meta, {}, {})
        self.assertEqual(len(seen), 2)
        self.assertTrue(all(seen), 'CREATE/COMMENT ran with stop signals deliverable')
        self.assertNotIn(signal.SIGTERM, signal.pthread_sigmask(signal.SIG_BLOCK, []))


class TomlSubsetTest(unittest.TestCase):
    DOCUMENT = r'''# comment
top = "value" # trailing
[[apps]]
name = "a"
literal = 'C:\path'
escaped = "tab\there \"q\" \\ \u00e9"
numbers = [1, +2, 3_000, -4]
nested = [["x", "y"], []]
multi = [
  "one", # inside
  "two",
]
flag = true
off = false
table = { A = "1", "B" = "2" }
empty = {}
[[apps]]
name = "b"
'''

    def test_supported_subset_parses_like_toml(self):
        expected = {
            'top': 'value',
            'apps': [
                {'name': 'a', 'literal': 'C:\\path', 'escaped': 'tab\there "q" \\ \u00e9',
                 'numbers': [1, 2, 3000, -4], 'nested': [['x', 'y'], []], 'multi': ['one', 'two'],
                 'flag': True, 'off': False, 'table': {'A': '1', 'B': '2'}, 'empty': {}},
                {'name': 'b'}]}
        self.assertEqual(d.parse_toml(self.DOCUMENT), expected)

    @unittest.skipIf(tomllib is None, 'tomllib parity needs Python 3.11+')
    def test_subset_matches_tomllib(self):
        self.assertEqual(d.parse_toml(self.DOCUMENT), tomllib.loads(self.DOCUMENT))
        self.assertEqual(d.parse_toml(ConfigTest.REPORT), tomllib.loads(ConfigTest.REPORT))

    def test_unsupported_or_invalid_toml_is_an_error_with_line(self):
        for text in ('a = 1.5', 'a = 1979-05-27', 'a.b = 1', '[table]\n', 'a = """x"""', 'a = "x',
                     'a = 1\na = 2', 'a = [1,', 'a = 01', 'a = "x" b', 'a = { b = 1,\n }', 'a =', '= 1',
                     'a = "bad \\q"', 'apps = 1\n[[apps]]'):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, 'line [0-9]+'):
                d.parse_toml(text)


class EnvFileTest(unittest.TestCase):
    def write(self, text, mode=0o600):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        path = Path(root.name) / '.env'
        path.write_text(text)
        path.chmod(mode)
        return str(path)

    def test_dotenv_subset(self):
        path = self.write('# c\n\nexport A=plain value # comment\nB="q \\"x\\" \\n"\n'
                          "C='lit $HOME'\nD=\nE=a#b\n")
        values, dynamic = d.read_env_file(path)
        self.assertEqual(values, {'A': 'plain value', 'B': 'q "x" \n', 'C': 'lit $HOME', 'D': '', 'E': 'a#b'})
        self.assertEqual(dynamic, set())

    def test_substitutions_are_marked_dynamic(self):
        values, dynamic = d.read_env_file(self.write('A=$(cat ~/.ssh/x)\nB="${HOME}/x"\nC=`id`\nD=\'$(no)\'\n'))
        self.assertEqual(dynamic, {'A', 'B', 'C'})

    def test_group_or_world_readable_file_is_refused(self):
        with self.assertRaisesRegex(ValueError, '0600'):
            d.read_env_file(self.write('A=1\n', mode=0o644))

    def test_errors_never_echo_values(self):
        for text in ('A="unterminated-canary\n', 'not an assignment canary\n', 'A="x" trailing-canary\n'):
            with self.subTest(text=text), self.assertRaises(ValueError) as caught:
                d.read_env_file(self.write(text))
            self.assertNotIn('canary', str(caught.exception))
            self.assertIn('line 1', str(caught.exception))

    def app(self, path, export=True):
        return dict(name='stub', env_file=path, env_file_export=export)

    def test_database_credentials_come_from_database_url_when_no_pg_vars(self):
        path = self.write('DATABASE_URL=ecto://root:p%40ss@db.local:5433/report_system_dev\nX=$(cat y)\n')
        tools, exported = d.secret_env(self.app(path, export=False))
        self.assertEqual(tools, {'PGUSER': 'root', 'PGPASSWORD': 'p@ss', 'PGHOST': 'db.local', 'PGPORT': '5433'})
        self.assertEqual(exported, {})

    def test_explicit_pg_vars_win_over_database_url(self):
        path = self.write('PGUSER=postgres\nPGPASSWORD=pw\nDATABASE_URL=ecto://root:x@localhost/db\n')
        tools, exported = d.secret_env(self.app(path))
        self.assertEqual(tools, {'PGUSER': 'postgres', 'PGPASSWORD': 'pw'})
        self.assertEqual(exported['PGUSER'], 'postgres')

    def test_exporting_a_dynamic_value_is_refused_by_key_name(self):
        with self.assertRaisesRegex(ValueError, 'X.*env_file_export = false'):
            d.secret_env(self.app(self.write('X=$(cat y)\n')))

    def test_reserved_keys_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'DEVSERVE_META'):
            d.secret_env(self.app(self.write('DEVSERVE_META=1\n')))

    def test_database_url_is_built_without_empty_password(self):
        meta = dict(database='db1', port=5110, config=dict(env={'MIX_ENV': 'dev'}, extra_ports=['HTTPS_PORT']))
        env = d.app_environment(meta, {'PGUSER': 'u'}, {'SECRET': 's'}, base={'DEVSERVE_X': '1', 'KEEP': 'k'})
        self.assertEqual(env['DATABASE_URL'], 'postgresql://u@localhost:5432/db1')
        self.assertEqual((env['PORT'], env['HTTPS_PORT'], env['PREVIEW']), ('5110', '5111', '1'))
        self.assertEqual((env['SECRET'], env['KEEP'], env['MIX_ENV']), ('s', 'k', 'dev'))
        self.assertNotIn('DEVSERVE_X', env)
        env = d.app_environment(meta, {'PGUSER': 'u', 'PGPASSWORD': 'p w', 'PGHOST': '::1'}, {}, base={})
        self.assertEqual(env['DATABASE_URL'], 'postgresql://u:p%20w@[::1]:5432/db1')


class RegistryTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.registry = d.Registry(Path(self.root.name) / 'state')

    def entry(self, worktree='/tmp/a/feature'):
        unit, database = d.names('stub', Path(worktree))
        return dict(app='stub', unit=unit, worktree=worktree, database=database, port=43000, state='starting')

    def test_entries_round_trip_through_a_private_file(self):
        entry = self.entry()
        self.registry.put(entry)
        self.registry.update(entry['unit'], state='running', pane_pid=12)
        self.assertEqual(self.registry.read()[entry['unit']], dict(entry, state='running', pane_pid=12))
        path = self.registry.path
        self.assertEqual(json.loads(path.read_text())['version'], 1)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
        self.registry.remove(entry['unit'])
        self.assertEqual(self.registry.read(), {})

    def test_concurrent_updates_do_not_lose_fields(self):
        import multiprocessing
        entry = self.entry()
        self.registry.put(entry)
        context = multiprocessing.get_context('fork')
        workers = [context.Process(target=_update_field, args=(str(self.registry.root), entry['unit'], f'k{i}'))
                   for i in range(8)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(10)
        stored = self.registry.read()[entry['unit']]
        self.assertEqual({k: stored[k] for k in stored if k.startswith('k')}, {f'k{i}': 20 for i in range(8)})

    def test_tampered_identity_is_refused(self):
        entry = self.entry()
        self.registry.put(dict(entry, database='postgres'))
        with self.assertRaisesRegex(ValueError, 'invalid devserve state'):
            self.registry.read()

    def test_shared_state_directory_is_refused(self):
        self.registry.root.mkdir(mode=0o755)
        self.registry.root.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'private'):
            self.registry.put(self.entry())

    def test_missing_file_is_empty(self):
        self.assertEqual(self.registry.read(), {})


def _update_field(root, unit, key):
    registry = d.Registry(Path(root))
    for value in range(1, 21):
        registry.update(unit, **{key: value})


class LivenessTest(unittest.TestCase):
    def test_observed_state(self):
        cases = [
            ('running', True, True, 'running'),
            ('running', True, False, 'failed'),
            ('running', False, True, 'stopped'),
            ('starting', True, False, 'starting'),
            ('starting', False, False, 'stopped'),
            ('failed', False, False, 'failed'),
            ('stopped', False, False, 'stopped'),
            ('stopped', True, False, 'stopped'),
        ]
        for stored, alive, listening, expected in cases:
            with self.subTest(stored=stored, alive=alive, listening=listening):
                self.assertEqual(d.observed_state(stored, alive, listening), expected)

    def test_window_identity_requires_name_server_and_pane_pid(self):
        unit = 'devserve-stub-feature-0123456789ab.service'
        entry = dict(unit=unit, window='@3', server=100, pane_pid=os.getpid())
        window = dict(name='devserve-stub-feature-0123456789ab', pane_pid=os.getpid(), dead=False, server=100)
        self.assertTrue(d.window_alive(entry, {'@3': window}))
        for change in (dict(name='other'), dict(server=101), dict(pane_pid=1), dict(dead=True)):
            with self.subTest(change=change):
                self.assertFalse(d.window_alive(entry, {'@3': dict(window, **change)}))
        self.assertFalse(d.window_alive(entry, {}))
        self.assertFalse(d.window_alive(dict(entry, window=None), {'@3': window}))


class TmuxTest(unittest.TestCase):
    def test_default_server_ignores_the_callers_tmux(self):
        from unittest import mock
        with mock.patch.dict(os.environ, {'TMUX': '/tmp/tmux-1/other,1,0', 'KEEP': '1'}):
            self.assertEqual(d.Tmux('').base, ['tmux'])
            env = d.Tmux('').environment()
        self.assertNotIn('TMUX', env)
        self.assertEqual(env['KEEP'], '1')
        self.assertEqual(d.Tmux('scratch').base, ['tmux', '-L', 'scratch'])
        self.assertEqual(d.Tmux('/tmp/s').base, ['tmux', '-S', '/tmp/s'])


class PureTest(unittest.TestCase):
    def test_lifecycle_golden_and_reachability(self):
        import random
        from render_lifecycle import render
        self.assertEqual((SCRIPT.parent.parent / 'lifecycle.md').read_text(), render())
        states = {'absent'}
        for _ in range(5):
            states |= {target for (source, _), (target, _) in d.TRANSITIONS.items() if source in states}
        self.assertEqual(states, {'absent', 'starting', 'running', 'failed', 'stopped'})
        rng = random.Random(17)
        state = 'absent'
        for _ in range(500):
            event = rng.choice(['up', 'ready', 'error', 'down', 'drop'])
            before = dict(d.TRANSITIONS)
            try:
                target, effects = d.step(state, event)
                self.assertIn(target, states)
                self.assertIsInstance(effects, tuple)
                if 'drop' in effects:
                    self.assertIn(state, ('stopped', 'failed'))
                state = target
            except ValueError:
                self.assertNotIn((state, event), d.TRANSITIONS)
            self.assertEqual(before, d.TRANSITIONS)

    def test_names_are_bounded_safe_and_distinguish_same_basename(self):
        unit, db = d.names('stub', Path('/tmp/a/feature'))
        self.assertRegex(unit, r'^devserve-stub-feature-[a-f0-9]{12}\.service$')
        self.assertRegex(db, r'^stub_preview_feature_[a-f0-9]{12}$')
        self.assertNotEqual(d.names('stub', Path('/tmp/b/feature')), (unit, db))
        self.assertLessEqual(len(d.names('a'*20, Path('/tmp/' + 'b'*200))[1]), 63)

    def free_block(self, size=6):
        import random
        for _ in range(100):
            # Below the ephemeral ranges, so unrelated client sockets cannot take a port mid-test.
            first = random.randrange(20000, 32000 - size)
            if all(d.port_free(port) for port in range(first, first + size)):
                return first
        raise AssertionError('no free port block')

    def test_port_choice_takes_first_available(self):
        port = self.free_block()
        self.assertEqual(d.choose_port([port, port + 1], set()), port)

    def test_port_choice_skips_claims_and_real_listener(self):
        with socket.socket() as listener:
            port = self.free_block()
            listener.bind(('127.0.0.1', port))
            listener.listen()
            self.assertEqual(d.choose_port([port, port + 2], {port + 1}), port + 2)
            with self.assertRaisesRegex(ValueError, 'port'):
                d.choose_port([port, port + 1], {port + 1})

    def test_port_block_needs_every_port_free_and_inside_the_range(self):
        with socket.socket() as listener:
            port = self.free_block() + 1
            listener.bind(('127.0.0.1', port))
            listener.listen()
            # port-1 is free but its block [port-1, port] is not; the first full block starts at port+1.
            self.assertEqual(d.choose_port([port - 1, port + 2], set(), width=2), port + 1)
            self.assertEqual(d.choose_port([port - 1, port + 4], {port + 2}, width=2), port + 3)
            with self.assertRaisesRegex(ValueError, 'port'):
                d.choose_port([port + 1, port + 1], set(), width=2)

    def test_lifecycle_returns_effects_and_rejects_invalid_events(self):
        self.assertEqual(d.step('absent', 'up'), ('starting', ('prepare', 'launch')))
        self.assertEqual(d.step('starting', 'ready'), ('running', ()))
        self.assertEqual(d.step('starting', 'error'), ('failed', ('rollback',)))
        self.assertEqual(d.step('running', 'down'), ('stopped', ('terminate',)))
        self.assertEqual(d.step('stopped', 'drop'), ('absent', ('drop',)))
        with self.assertRaises(ValueError):
            d.step('absent', 'ready')

    def test_listing_exposes_only_the_public_fields(self):
        row = dict(unit='u', app='a', worktree='/w', branch='b', port=1, url='http://127.0.0.1:1', database='d',
                   owner='o', state='running', missing=False, config={'env_file': '/x'}, pane_pid=3,
                   window='@1', server=9, previous='absent')
        self.assertEqual(set(d.public(row)), {'unit', 'app', 'worktree', 'branch', 'port', 'url', 'database',
                                              'owner', 'state', 'missing'})


if __name__ == '__main__':
    unittest.main()
