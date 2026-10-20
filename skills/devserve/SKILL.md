---
name: devserve
description: Use when starting, inspecting, or cleaning up a worktree app preview, or configuring an app for isolated browser checks.
---

<!-- house: own -->

# devserve

Run `python3 scripts/devserve up [worktree]` and open the printed URL for browser checks.
The preview runs in its own tmux window, on its own port, against its own database.
The app must already be registered in `~/.config/devserve/apps.toml`; configuration and the app contract are in [configuration.md](configuration.md).

- `ls --json` returns `previews` and `main_units`; select your preview by `worktree` or `owner`.
- `logs <unit> [-f]` prints or follows the preview's log; `logs <app>` captures that app's `tmux:` main targets.
- `down <unit>` stops the app, closes its window and keeps its database for the next `up`.
- At session close-out, run `down <unit> --drop-db` and confirm the unit disappeared from `ls --json`.
- `gc` removes previews whose worktree directory is gone and lists stopped ones; `gc --stopped` also drops those (after a reboot or a killed tmux server). It also finds owned databases with no state entry (old systemd previews).
- `base refresh <app> [--dump]` rebuilds a `data = "template"` app's base database from its source database.

Owner comes from `FOREMAN_SESSION`, otherwise the OS username. Main servers are read-only here.
A failed start rolls back a newly created database and keeps its window for inspection until `down --drop-db`.
Only databases with the matching devserve ownership comment can be reused or dropped.
To watch a preview live, attach to the `devserve` tmux session; each window is named after its unit.

## Install (operator-approved)

Requires tmux 3.0+, Python 3.9+, git 2.31+, and PostgreSQL client tools matching the server (15+ for `template`).
After approval, link the script's absolute path into `~/.local/bin/devserve` with `ln -s`.
No installation is required to use the Python invocation above.

## Verify

```sh
python3 -m unittest discover -s skills/devserve/scripts
DEVSERVE_INTEGRATION=1 python3 -m unittest discover -s skills/devserve/scripts
python3 scripts/check.py   # needs Python 3.11+ (tomllib)
```

Run these from the skills repo root. Integration tests need tmux and the local throwaway-test PostgreSQL login
`postgres/postgres` on localhost. Each test runs a scratch tmux server (`tmux -L devserve-test-<pid>`), creates
only `devserve_test_<pid>*` databases, and removes both in cleanup. `DEVSERVE_BENCH_SOURCE=<db>` additionally
times copy against template on a large database, reading the source only through `pg_dump`.
The [lifecycle diagram and matrix](lifecycle.md) are generated from the declared table and checked by tests.
