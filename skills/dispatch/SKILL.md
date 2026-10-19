---
name: dispatch
description: "Coordinator only: launch, watch, steer, and close out pi build sessions in named tmux windows or panes, singly or from ready tickets across repos."
---

<!-- house: own -->

# Dispatch

You are the coordinator: you plan, brief, verify, and commit. Build work runs in a separate pi session, not in your context. The main coordinator uses one tmux window per build; epic coordinators use panes in their own window. Use Claude subagents (Agent tool, pi `subagent`) only when the user asks for them.

Scripts live in `~/dev/utils/skills/skills/dispatch/scripts/` (`$D` below). Run the scripts inside the caller's tmux session; they inherit `$TMUX`, including non-default servers such as `-L foreman`. Names are unique across build panes and windows in that session. Launch sequentially to avoid duplicate-check races.

Detect the tracker in each repo: `tickets/` means files; otherwise beads. Use the `foreman` skill's
direct ticket commands for content/status and its best-effort sender only for board events.
Ask/wait are direct, outcome-gated calls: read the `foreman` skill's approval-request section.
Agents never push. Pushes go through board requests.
With neither tracker directory, ask for user-approved `foreman adopt`; dispatch does not migrate repos.

## Dispatch one session

1. **Name the build** (window or pane). Short kebab-case from the content, ≤31 chars: `house-sync`, `cdo-trait-probe`. The marker is the name upper-cased plus ` DONE`: `HOUSE-SYNC DONE`.
2. **Write the brief** to `<repo>/drafts/briefs/<window>.md`, or to `/tmp/briefs/<window>.md` when the repo has no drafts dir. Fill every slot:

   ```markdown
   You are a build session in <repo> (<path>). A coordinator session dispatched you and will read your output. Work autonomously; ask only when a decision is genuinely the user's.

   ## Goal
   <one paragraph: the outcome, not the steps>

   ## Read first
   <local AGENTS.md, then the files and prior reports this work builds on>

   ## Tickets
   <ticket ids and tracker detected in this repo; start via foreman update <id> --status in_progress for files, bd update <id> --claim for beads, unless coordinator already claimed them; coordinator owns new ticket creation and closure after review and any authorized commit>

   ## Skills
   - `tdd` at these seams: <seams agreed in the spec or ticket, or "none: <reason>">
   - `verify-before-claiming` before writing the report.
   - `code-review` on your own diff against <base sha> before printing the marker: Standards and Spec axes (Spec = the tickets above), plus Risk when the diff touches persistence, wire formats, public APIs, shared config, or concurrency. Run the axes one after another in this session; spawn no subagents. Fix every Critical and Important finding, then re-run the gate.

   ## Decisions already made
   <user decisions to apply, not re-ask>

   ## Rules
   <what is off limits: commits, pushes, deploys, paths outside the repo, harness dirs>

   ## Browser checks
   <coordinator: check devserve registration before dispatch; fill this slot with the registered-app instructions below, or the existing separate-port/own-databases guidance for an unregistered app>
   For a registered app, use the `devserve` skill. In this worktree run `FOREMAN_SESSION=<window> devserve up` for browser checks and use the printed URL. Confirm `devserve ls --json` shows this worktree with owner `<window>`; report its unit, URL, database, and browser evidence. If startup or ownership verification fails, report the blocker rather than improvising a server. Leave preview cleanup to coordinator close-out.

   ## Build loop
   Use the `foreman` skill's best-effort sender for `foreman progress <id> "<milestone; next step>"` at milestones, once per affected ticket; warnings never block work.
   For a build-time question you cannot answer, run `foreman ask decision <ticket> --question "<question>" --option "<A>" --option "<B>" --recommendation "<A>"` directly, then `foreman wait <returned-request-id> --timeout 7200` in your shell, not through the sender and not as a question in this pane. Follow the `foreman` skill's approval outcomes: resume only with `state: answered`, using `outcome.answer` and `note`; exit 0 alone is not an answer. Keep the ID and re-wait after a timeout. Report an unavailable inbox as a blocker rather than guessing.

   ## Done when
   <checkable criteria: gate command and its expected result, tests, evidence>
   Work until every item above holds. Hand off early only near your context limit (above about 85%), at a clean, green point, with a precise list of what remains; a pure table without its executor is not a stopping point.

   ## Report back
   Write <report path>: what changed, evidence, review findings per axis with what you fixed and what you left open, anything else open, final gate output. Use the `foreman` skill's best-effort sender for `foreman report <id> --path <report path>` once per completed ticket; warnings never block the marker. Then print <MARKER> alone on the last line.
   ```

   `<base sha>` is `git rev-parse HEAD` in the workdir at dispatch time. For the browser-check slot, inspect `devserve ls` and the app registration using the `devserve` skill's configuration guide; an app with no running units may still be registered. Unregistered apps retain separate ports and their own databases; registering an app needs operator approval. Done when every slot is filled and the marker appears only in the last line's instruction.
3. **Launch:** `bash "$D/pi-window" <window> <workdir> <brief-file> --bead <id> [--bead <id> ...] --report <report-path> -- --model <provider/model> [pi-args...]`; use the `foreman` skill: the script records `dispatch` after launch, best-effort.
   Use the brief's ticket IDs and report path; `--bead` is the launcher's legacy flag for either tracker. Pass the chosen model explicitly. It exports `FOREMAN_ACTOR=pi` and `FOREMAN_SESSION=<window>` into pi, captures workdir/branch/base/brief, and refuses duplicate build names. Extra args go to pi (`-e <path>` loads an extension). A workdir pi has not seen (a new worktree) stops at pi's "Trust project folder?" prompt and the session waits there unseen: read the pane right after launch and answer it. Legacy calls without metadata still launch; no IDs means no board dispatch, omitted report defaults to `<workdir>/drafts/sessions/<window>.md`, omitted model records `default` (not a guessed model).
   **Pane mode (epic coordinators):** prepend `--pane`: `bash "$D/pi-window" --pane <name> <workdir> <brief-file> --bead <id> --report <report-path> -- --model <provider/model>`. It splits `$TMUX_PANE`'s window, tiles the panes while retaining coordinator focus, and sets the new pane's title and pane-local `@build` tag to `<name>`. Identity is the tag, never a pane index or a mutable title. `FOREMAN_SESSION` and preview ownership remain `<name>`; the existing board `--window` metadata field carries the stable `%pane-id` instead of a window name (board focusing support is tracked separately).
4. **Wait in the background:** run `bash "$D/pi-wait" <window> "<MARKER>" 7200` (pane build: `bash "$D/pi-wait" --pane <name> "<MARKER>" 7200`) as a background command, then keep working or return control; do not poll by hand. It matches whole lines only (whitespace-trimmed), so the marker quoted in the brief never counts. Exit codes: 0 `DONE`, 5 `LIMITED` (a provider usage or rate limit stopped the session; the error line follows: post it to the board at once: `foreman ask session_waiting <ticket> --reason usage_limit` where that kind exists, otherwise `foreman ask decision <ticket>` (wait for the reset / continue after a banked reset / switch the model), so it reaches Needs you and a notification, not only chat; act on the answer, then re-wait after the session continues), 6 `BLOCKED` (pi's trust prompt is showing: answer it or trust the parent folder), 7 `IDLE` (nothing on screen changed for `PI_WAIT_IDLE` seconds, default 600, without the marker: fallback detection; read the printed last lines and check for a pending board decision before interrupting its wait. Notify the user about the board request, or recover a question that missed the inbox, then re-wait), 3 `EXITED` (pi quit without the marker: read the pane), 4 timeout (session still running: check the pane, re-wait), 2 target gone (pane lookup also fails closed on ambiguous tags). Pane waits bind the resolved pane ID at startup, so a replacement with the same name cannot finish the old wait.
5. **Follow up** through the board for build-time decisions; its waiting shell receives the answer without pane input. Use the pane for returned review work, recovery, or a new user instruction. Send the text and the Enter as two separate commands, and keep the text to one line:

   ```bash
   tmux send-keys -t :<window> -l "<text>"
   tmux send-keys -t :<window> Enter
   ```

   Read a window build with `tmux capture-pane -p -J -S -200 -t :<window>`.
   For pane builds, resolve the tag before capture or input; stop if lookup fails:

   ```bash
   target=$(bash "$D/pi-pane" <name>) || exit
   tmux capture-pane -p -J -S -200 -t "$target"
   tmux send-keys -t "$target" -l "<text>"
   tmux send-keys -t "$target" Enter
   ```
   After sending work back to a session, start a fresh `pi-wait`: it counts only marker lines printed after it starts, so the earlier marker never ends the new wait.
6. **Close out.**
   1. Read the report file; use the `foreman` skill to send `review` for each reported ticket before running the close-out checks.
   2. Re-run the repo's gate yourself, plus its per-ticket close-out check where it has one (form-engine: `.agents/skills/verify-form-engine/verify closeout <bead-id>` for each reported ticket).
   3. Check each claim against the diff and the evidence. A claim you cannot reproduce is open, not done.
   4. Run `code-review` on the slice's diff against the brief's base sha, axes one after another in your own context; no subagents unless the user asked for them. Use the `foreman` skill to send `changes` with Critical and Important findings before sending work back (step 5); otherwise list findings as open to the user. If returning work, wait for its new report and restart close-out; do not commit or kill that build yet.
   5. Commit, one commit per slice, only when the user has asked for commits; use the `foreman` skill to send `commit --sha <actual-sha>` for the tickets in that commit, only after it succeeds.
   6. **Request publication after the authorized commit.** Use the `foreman` skill's direct ask/wait commands, not the best-effort sender. For `forge = "none"`, end at commit. Otherwise read the worktree's actual branch and full SHA (`git -C <worktree> branch --show-current`, `git -C <worktree> rev-parse HEAD`); stop on detached HEAD. Name the intended remote branch explicitly, and post `ask push` for a committed ticket covering the slice. Tell the user once in chat that close-out requests are waiting on the board; ask no terminal push/PR question.
      Wait in the background with `foreman wait <push-request-id> --timeout 7200`. Consume `state: done` before posting `ask open_pr` where the repo uses PRs: head = pushed destination, SHA = published SHA, base = repo/stack target, title/body = reviewed PR text. Allow the board's branch snapshot to refresh if creation refuses a newly pushed head. Wait for that request too. Default-branch pushes are only for one-off tickets without an epic; epic work uses a PR. If a matching PR already exists, inspect it rather than requesting a duplicate. When merging is the next step, post `ask merge` for its PR number and current expected head and wait through board confirmation and completion.
      **Human-merge repos** (`merge_policy = "human"`, see the `foreman` skill): push to a feature branch, never the base or default branch, even for a one-off ticket; `ask open_pr` with base = the repo's `merge_base` (or the parent PR's head branch for a stack). Stop there: post no `ask merge`. Report the PR URL to the user with "Waiting for a person to merge on GitHub" and keep the ticket open until forge sync shows it `merged`.
      Timeout/warning/decline/failure is not approval: follow the `foreman` outcome table. Keep tickets open and the waiting context available until required requests resolve; never substitute `git push`, `gh pr create`, or `gh pr merge` for the board worker.
   7. Close verified tickets under the repo's policy only after required requests resolve; closing earlier supersedes pending requests. In a human-merge repo that means after the board shows the ticket `merged` (a person merged its PR on GitHub). Files: direct `foreman close <id> --reason "<evidence>"`, then `foreman check`; beads: `bd close <id> --reason "<evidence>"`. Ticket-file status changes must also be included in an authorized coordinator commit; a board event doesn't save them to git. If closure changes need publication but no eligible committed ticket remains, report that policy blocker; do not fabricate stage events or push directly.
   8. **Remove session previews before killing the build.** Run `python3 "$D/preview-cleanup.py" <name>` for either mode (use the build name, not the pane ID). It selects exact `owner` matches from `devserve ls --json`, runs `devserve down <unit> --drop-db` for each (including failed/stopped previews), and re-lists to confirm none remain; other owners and main units are untouched. Run it even if the report lists no previews. A missing CLI, failed listing/drop, or remaining preview blocks teardown: keep the build and report the failure, then retry after resolving it. Quiesce browser work before cleanup; don't start new previews during close-out.
   9. Only after cleanup exits 0, tear down the build. Window mode: `tmux kill-window -t :<window>`. Pane mode: `target=$(bash "$D/pi-pane" <name>) || exit`, then `tmux kill-pane -t "$target"`. Never kill the epic coordinator's window to close a pane build.

   Done when the gate passes in your own run, every claim is confirmed or listed as open to the user, no Critical review finding is unresolved, required board requests have completed, the session's previews and their databases have been removed, and the build target is gone. If a request blocks progress, report its ID and outcome and leave close-out open.

## Dispatch from ready

1. List ready work across main checkouts under `~/dev`:

   ```bash
   python3 "$D/ready-repos.py" ~/dev
   ```

   It discovers repo-root `tickets/` or `.beads/` directories to depth 5, excluding dependency/build
   trees and checkouts whose `.git` is a file (linked worktrees). Files take precedence:
   `foreman ready --json` (uncapped); beads: `bd ready --json --limit 0` (all ready tickets).
   Output groups the
   unchanged ticket records by repo and tracker. A files-only set needs no `bd` on PATH.
   Each repo has a 30-second limit. Failed reads are reported on stderr, healthy repos still appear,
   and the script exits 1 for an incomplete scan. Report failures; do not treat them as empty frontiers,
   start Dolt servers, or fall back to beads when a files command fails.
2. Propose a table to the user: ticket, repo, window name, why it can run now. Group tickets that share files into one window. Never put two writers in the same repo working tree at once. Leave out epics, tickets that need the user live (in-game probes, logins), and tickets blocked on a decision.
3. On approval, dispatch each row as above, one brief per window.
