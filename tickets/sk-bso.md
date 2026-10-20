---
id: sk-bso
title: "devserve: tmux backend on Linux and macOS, template-cloned preview DBs, optional Caddy URLs"
type: feature
status: closed
priority: 2
parent: null
blocked_by: []
related: []
supersedes: []
discovered_from: null
labels: []
created: 2026-10-19
closed: 2026-10-20
close_reason: "770dfe2 pushed to origin/main (Ryan, card 616c02c6); review r2 clean. Open: Linux run, live ReportSystem check after #352."
---

## What to build
User decision 2026-10-19: replace devserve's systemd backend with tmux, on Linux and macOS alike. One backend, no OS split. devserve does not run on the work Mac today: it is systemd-only (one user unit per preview, EnvironmentFile for secrets, systemd as the registry, `main_units` read from systemd).

Scope on the work Mac: only ReportSystem needs previews. foreman, skills and dotfiles builds are tested directly and are not registered.

### Backend
- Each preview is a window in a `devserve` session on the user's default tmux server (configurable socket), named after the preview, running the app's `start` command with `PORT`, `DATABASE_URL`, `PREVIEW=1` and the plain `env`. The user can attach and watch the log.
- Secrets: the untracked `env_file` (0600) is read by a small launcher in the pane, never put in tmux's environment, argv or the registry.
- Registry: a JSON state file under `$XDG_STATE_HOME/devserve/` (or `~/.local/state/devserve/`), written under the existing flock. Liveness = window present + pane pid alive + TCP listener on the port. `state` keeps `starting|running|failed|stopped`; `missing` keeps its meaning.
- Main apps: `main_units` becomes a way to name the main checkout's server (port or tmux target) for `ls`; no systemd.
- Reboot: the tmux server is gone, so previews read `stopped`/`missing`; `gc` uses the state file, so it can also find pre-reboot orphan databases (better than today).

### Keep the interface
`up/down/ls --json/gc` and the `ls --json` fields stay. The foreman board (`Foreman.Previews.Devserve`) and dispatch's `preview-cleanup.py` both require `unit` to match `devserve-….service`: keep that id format, or change both consumers in the same change.

### Faster preview databases (ReportSystem's dev DB is 8.7 GB)
Add a `data = "template"` mode: `CREATE DATABASE <preview> TEMPLATE <base> STRATEGY FILE_COPY`, then migrate. `<base>` is a configured database nobody stays connected to (e.g. `report_system_preview_base`), refreshed by an explicit `devserve base refresh <app>` from the source DB. Keep `copy` for small apps.

### Optional: readable URLs
When Caddy's admin API is reachable (work Mac: Homebrew Caddy, admin `localhost:2019`), `up` adds a route `http://<sanitized-branch>.<app>.localhost` → the preview port and `down` removes it; `url` in `ls --json` reports it. Without Caddy, `url` stays `http://127.0.0.1:<port>`.

## Acceptance
- [ ] No systemd/systemctl use left; `scripts/test_devserve.py` and `test_integration.py` pass on macOS and Linux against a scratch tmux server
- [ ] `up` in a ReportSystem worktree starts its server in a tmux window on the assigned port with its own database; `ls --json` shows it running; `down --drop-db` removes window, state and database
- [ ] Secrets from `env_file` do not appear in `tmux show-environment`, pane argv, the state file or `ls --json`
- [ ] `data = "template"` creates an 8.7 GB-class preview DB much faster than `copy` (record both times) and refuses while the base has connections
- [ ] Killing the tmux server marks previews stopped/missing; `gc` finds and can drop their databases
- [ ] The foreman board's Previews and `preview-cleanup.py` work unchanged (or are changed with this ticket)
- [ ] configuration.md and lifecycle.md describe the tmux backend; `scripts/check.py` passes
