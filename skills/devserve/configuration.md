# Configuration and app contract

Config lives at `~/.config/devserve/apps.toml`. `DEVSERVE_CONFIG_DIR` overrides its directory for tests.
Creating user config or changing an app's dev config requires operator approval.

```toml
tmux_socket = ""            # optional: -L name, or a path for -S; empty = the default tmux server

[[apps]]
name = "example"
path = "/absolute/path/to/main-checkout"
ports = [4700, 4799]
extra_ports = ["HTTPS_PORT"]  # optional: more ports per preview, PORT+1, PORT+2, ...
start = ["/absolute/path/to/mix", "phx.server"]
env_file = "/absolute/path/to/untracked-secrets.env"
env_file_export = true        # optional, default true
env = { APP_ROLE = "web" }
data = "copy"
source_database = "example_dev"
migrate = ["/absolute/path/to/mix", "ecto.migrate"]
timeout = 120                 # optional: seconds per preparation step and for the listener
main_units = ["tcp:4000", "tmux:work:server"]
```

`name`, `path`, `ports`, `start`, `data`, and `migrate` are required. Names are lowercase identifiers
(up to 20 characters, letters/digits/underscores). Commands are nonempty argv arrays, not shell strings;
use absolute executables or set a non-secret PATH in `env`. Paths must be absolute. App port ranges are
inclusive, 1024–65535, and must not overlap. Worktrees match by git common directory, not branch or basename.
The file is read with a TOML subset (strings, integers, booleans, arrays, one-line inline tables,
`[[apps]]`), the same on Python 3.9 and later; anything else is an error with its line number.

Data modes:
- `copy` requires `source_database`: `pg_dump --format=custom` → `pg_restore --no-owner --no-acl --exit-on-error` → migrate.
- `fresh` requires `seed`: create → migrate → seed.
- `template` requires `template_database` (up to 58 characters): `CREATE DATABASE … TEMPLATE <base> STRATEGY FILE_COPY`
  (with PostgreSQL 18's `file_copy_method = clone` where available) → migrate. `up` refuses while the base has
  connections. `devserve base refresh <app>` clones `source_database` the same way into `<base>_next`, swaps it
  in, and disallows connections to it; it refuses while the source has connections (stop the main dev server for
  the seconds it takes). `--dump` uses pg_dump/pg_restore instead, which works while the source is in use but
  fails on data pg_restore cannot load back (for example rows that violate a foreign key because they were loaded
  with triggers off). Use this mode for large databases.

Database names are PostgreSQL names, never credential-bearing URLs. A kept database is reused,
with migrations rerun but no recopy or reseed. To recopy, use `down --drop-db`, then `up`.
`env_file`, `env`, `extra_ports`, `timeout`, and `main_units` are optional. Unknown fields are errors.

`main_units` names the main checkout's server for `ls`: `tcp:<port>` is `active` while something listens on
127.0.0.1:<port>; `tmux:<target>` is `active` while that pane is alive, and `logs <app>` captures it.
Old systemd entries (`*.service`) are skipped with a warning on stderr (not for `ls --json`, which foreman parses
with stderr merged); replace them with `tcp:<port>`.

## Secret transport

All config, command arrays, branch names, owner labels, and worktree paths are public metadata.
Put secrets only in the untracked `env_file`, owned by you with mode 0600 (devserve refuses anything else).
It uses dotenv lines: `KEY=value`, optional `export`, `'literal'` or `"escaped"` values, `#` comments.
Values containing `$` or backticks (dotenv substitution such as `$(cat …)`) are not expanded.

devserve reads `env_file` itself, only in memory: the CLI for its database tools and the pane launcher
for the app. Values never go into tmux's environment, argv, the state file, `ls --json` or error messages.
Database tools authenticate with `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD` from the file; when the file has
no `PGUSER`/`PGPASSWORD`, they come from its literal `DATABASE_URL`. Defaults are localhost:5432 and the
OS username. Unix-socket DATABASE_URL generation is not supported.

With `env_file_export = true` every value is also exported to the app, migrate and seed; substitution values
are then refused. With `false` the file supplies database credentials only, for apps that load their own
env file (dotenv) from the worktree. Reserve `DEVSERVE_*`. `PORT`, `DATABASE_URL`, `PREVIEW` and `extra_ports`
names are always set by devserve and win over the file and `env`.

The preview's environment is the tmux server's global environment plus these variables. Applications and
configured commands must not print secrets or put DATABASE_URL in subprocess argv; the output of `start`,
`migrate` and `seed` goes to the pane and the log file, so `devserve logs` shows why a first start failed.
devserve's own database tools (psql, pg_dump, pg_restore) report only the executable and exit code, suppressing
potentially secret-bearing diagnostics.

## App contract

Start and migration/seed commands receive `PORT`, `DATABASE_URL`, `PREVIEW=1` and any `extra_ports` variables.
The dev server must bind on the assigned port and honor DATABASE_URL. Up waits for a 127.0.0.1 TCP listener
(up to `timeout` seconds after preparation); browser/content checks remain the caller's responsibility.
An app with external writes must refuse them under PREVIEW=1, including forge writes, pushes, merges,
and launching sessions. Check this when registering an app; copied data may contain pending actions.
The app's stdin is an open pipe that never sends EOF.

## Registry and cleanup

Unit names use `devserve-<app>-<sanitized-worktree>-<path-hash>.service` (the id format foreman and
`preview-cleanup.py` expect; there is no systemd unit); databases use `<app>_preview_<sanitized-worktree>_<path-hash>`.
The path hash distinguishes same-basename worktrees. `ls --json` previews contain `unit`, `app`, `worktree`,
`branch`, `port`, `url`, `database`, `owner`, `state`, and `missing`. Main entries contain `unit`, `app`, and
`state` (`active`/`inactive`).

Each preview is a window in the `devserve` session of the configured tmux server, named after its unit without
`.service`. The window runs `devserve _launch <state-dir> <unit>`, which prepares the database, runs `start`,
and copies the app's output to the pane and to `<state-dir>/logs/<window>.log` (0600). Windows keep a dead pane
after a failure (`remain-on-exit`) for inspection.

The registry is `$XDG_STATE_HOME/devserve/previews.json` (default `~/.local/state/devserve/`, `DEVSERVE_STATE_DIR`
overrides; directory 0700, file 0600), replaced atomically under `state.lock`. Mutation commands serialize on
`devserve.lock` in the same directory; `up` holds it only while it picks the port, records the preview and opens
the window, then waits for the listener without it, so other `up`, `down` and `gc` calls proceed meanwhile
(`down` of a `starting` preview stops its launcher, which rolls back new data). `up` on a preview that is already
`starting` waits for that same preview and prints its URL. Other programs can still race a port bind; startup
failure rolls back new data. Each preparation command times out after `timeout` seconds. Ctrl-C during the `up`
that launched the preview stops the launcher and rolls back new data.

The recorded state is checked against what exists: a preview is alive while its window (same server, name and
pane pid) exists and the pane process lives; `running` also needs the TCP listener, else it reads `failed`.
A `starting` or `running` preview whose window is gone reads `stopped`. Killing the tmux server or rebooting
therefore leaves previews `stopped` with their databases kept; a SIGHUP or SIGTERM to the launcher stops the app
first. If the launcher is killed with SIGKILL, the app (in its own process group) may keep running.
`gc` lists such previews from the state file and `gc --stopped` drops them; `gc` alone drops only previews whose
worktree is gone. `gc` also finds preview databases that carry a devserve ownership comment but have no state
entry (for example from the old systemd backend): their name and comment must match the same identity as today,
and the worktree is recognised by its path hash among the app's `git worktree list`. They are dropped when that
worktree is gone (or with `--stopped`), otherwise listed. Processes of old systemd units are not managed; stop
them once with `systemctl --user stop 'devserve-*'`. A row `gc` cannot clean is reported and skipped; `gc` then
exits 1. The launcher blocks catchable stop signals across database creation and its ownership comment.
SIGKILL, machine failure or a failed COMMENT can still leave an unmarked database; inspect it manually.
Unmarked databases are refused, never adopted or dropped.
