---
name: orient
description: "Coordinator start-of-session assessment, including when resuming a conversation or asked for /orient."
---

<!-- house: own -->

# Orient

Give a brief assessment from live reads, then recommend one next step. On **every invocation**, including a resumed conversation, re-read the sources below; earlier context and handoffs are leads, not evidence.

Read-only (except the capture-only ticket filing that step 5 allows): no dispatch, pane input, ticket edits, board events/requests, fetches, commits, pushes, service starts or repairs. Recommend actions; wait for the user's answer before switching to another workflow. REQUIRED: read the `foreman` skill for tracker precedence and read/configuration semantics; do not use its sender here.

## Gather

1. **Health and Needs you.** Record the observation time. Read each unit's actual state and the configured board's inbox:

   ```bash
   date -Is
   systemctl --user show foreman-web.service foreman-worker.service foreman-tmux.service -p Id -p LoadState -p ActiveState -p SubState
   curl --fail --silent --show-error --max-time 5 "${FOREMAN_URL:-http://127.0.0.1:4747}/needs-you"
   foreman ls --overlay --json
   ```

   `ls` without `--overlay` in a ticket checkout is local, not a board health check. Inspect output as well as exit status: CLI warnings can exit zero. The installed CLI may have no `requests`/`inbox` verb: read the rendered `/needs-you` page instead. Use the main pending-request list, not the duplicate drawer or Recent outcomes. Preserve its oldest-first order (check timestamps); report each request's ID/link, ticket, kind, age and decision/action needed. If a read fails, Needs you is **unknown**, not zero.

   On macOS there is no systemd: one launchd agent runs web and worker together (`FOREMAN_ROLE=all`), and planning sessions use the user's default tmux server. Read `launchctl print "gui/$(id -u)/com.ryanpaulmessner.foreman"` (state, pid, runs, last exit code) instead of `systemctl`, report web and worker as that one agent, and tmux as the default server's `tmux list-sessions`. For a confirmed stopped agent, give `launchctl kickstart -k "gui/$(id -u)/com.ryanpaulmessner.foreman"` as a command for the user, never execute it; its log is `~/Library/Logs/foreman/board.log`.

   Report web, worker and tmux separately from HTTP/API reachability. For a confirmed inactive unit, give `systemctl --user start <unit>` as a command for the user, never execute it. If units are active but the URL fails, report the mismatch and suggest checking the configured URL/logs, not restarting blindly. If systemd is inaccessible, unit state is unknown. Finish with a status for all four checks and a pending count or explicit gap.

2. **In flight.** Use overlay stages `dispatched`, `building`, `reported` and `in_review` to find active work and coordinator follow-through. Waiting is session state/reason, not a ticket stage; `request_changes` is an event returning work to `building`. Read each relevant `foreman show <id> --overlay --json` for history, session, workdir, report and current wait reason. Enumerate both tmux servers, even if the first is absent:

   ```bash
   tmux list-windows -a -F '#{session_name}:#{window_index} #{window_id} #{window_name}'
   tmux -L foreman list-windows -a -F '#{session_name}:#{window_index} #{window_id} #{window_name}'
   ```

   Match board sessions to windows by server/session/window, not name alone. Include pi builds and launched coordinators; unmatched windows are unclassified until inspected. Read relevant panes with `tmux [server flags] capture-pane -p -J -S -80 -t <target>` and pane cwd/command with `list-panes`. Flag explicit waiting, usage-limit, trust-prompt, exited/missing-window or reported states. Old progress alone means **possibly stalled**, not proven dead.

   Read referenced reports and `git -C <workdir> status --short` (including report paths). Distinguish unreviewed reports, reviewed but uncommitted work, and committed work; an existing old report or dirty file alone does not prove a new handoff. Reconcile board and pane discrepancies instead of silently choosing one. Finish with every observed build/coordinator window and each outstanding report accounted for, or marked unknown.

3. **Frontier.** Run the existing dispatch read (path relative to this skill directory):

   ```bash
   python3 ../dispatch/scripts/ready-repos.py ~/dev
   ```

   REQUIRED: read `dispatch`'s “Dispatch from ready” section for discovery limits and failure semantics; stop before its dispatch steps. Keep healthy repos on a partial scan and name failed repos. Group by repo and parent epic; use local `foreman show <parent> --json` / beads reads where a parent title or ancestry is needed, with “Unparented” for no parent. Inspect the candidate's full ticket before recommending it. Exclude epics from executable work. Cross-check readiness with active sessions/worktrees and pending decisions: main-checkout tickets may still be open while a build owns them elsewhere. Label these as already in flight, not new launch candidates. Finish with totals, epic groups and a concrete available pick (or explain why none is available).

4. **Unpushed.** For repos discovered above, plus repos/workdirs seen in sessions, read:

   ```bash
   git -C <repo> worktree list --porcelain
   git -C <repo> for-each-ref --format='%(refname:short) %(upstream:short) %(upstream:track)' refs/heads
   git -C <repo> rev-list --count '<upstream>..<branch>'
   ```

   Use the last command for each branch with an upstream, substituting the observed refs. Summarize ahead counts per repo **and branch**; do not sum overlapping branch histories. No upstream, gone upstream, detached HEAD or failed read means publication status unknown, not zero. Counts are against locally cached remote refs; do not fetch to refresh them. The user pushes. Finish with every scoped repo accounted for and that freshness caveat.

5. **Repo extras.** For each main checkout in scope, if `<repo>/.agents/orient.md` exists, read it and run its checks (for example an external request queue that feeds the repo's tickets). The one write an extras file may allow is filing capture-only tickets (`foreman new`) for external items with no local ticket; it never allows status changes, closes or other writes. Report what each extras file found and every ticket it filed. A failed extras read is unknown, not empty.

## If foreman is unavailable

Continue with tmux, git and `ready-repos.py`: file `foreman ls --json`, `show` and `ready` work offline from each checkout without `--overlay`. Use live report files and pane output for what they actually establish. Board stages, inbox and review status remain unknown where no current source confirms them. Do not substitute remembered board state or an empty failed read. Report the failure and recovery suggestion alongside the partial assessment.

## Answer

Use these short sections; no raw JSON or full backlog dump:

- **Health:** units and board, observation time, failures and suggested recovery.
- **Needs you (N / unknown):** oldest first, what each needs; link overflow if long.
- **In flight:** ticket → server/session/window, state; reports needing review/commit.
- **Frontier:** repo → epic groups and counts, a few candidate IDs; distinguish in-flight exclusions and incomplete scans.
- **Unpushed:** repo/branch ahead counts, unknowns, cached-ref caveat.
- **Repo extras** (only when an extras file exists): its findings and the tickets it filed.
- **Next:** one recommended action with a reason. Prefer unblocking a human decision or closing out a report before another build; otherwise pick ready work with its dependency payoff.

Done when every section has fresh evidence or an explicit unknown, and the answer ends with one recommendation rather than taking action. This is a current assessment, not `handoff`'s summary of the preceding conversation.
