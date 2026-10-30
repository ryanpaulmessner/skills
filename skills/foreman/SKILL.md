---
name: foreman
description: Use when managing repo tickets, build sessions, approvals inbox requests, coordinator close-out, onboarding with foreman adopt, or moving specs into tickets on foreman.
---

<!-- house: own -->

# Foreman

Ticket content belongs to the repo's tracker; the board owns session, progress, review and draft-epic
facts. Detect the tracker per repo: `tickets/` means files, even with `.beads/` present; otherwise beads.
Board events never replace ticket writes or git.

## Ticket content (direct CLI)

In a `tickets/` repo, run these commands directly from that checkout, **not** through `foreman-send`.
They read/write local files without a server. `--json` is available throughout. Invalid input fails;
handled I/O failures can warn with exit 0, so inspect the returned ticket and run `foreman check`.

| Operation | Files (`tickets/`) | Beads (`.beads/`, no `tickets/`) |
| --- | --- | --- |
| Inspect / list / frontier | `foreman show <id> --json` / `foreman ls --json` / `foreman ready --json` | `bd show <id>` / `bd list` / `bd ready` |
| Create | `foreman new "<title>" --type <type> --parent <epic> --blocked-by <ids> --body "<text>"` (omit unused flags) | `bd create` with `--parent`, `--deps`, `--body-file` |
| Start | `foreman update <id> --status in_progress` | `bd update <id> --claim` |
| Note / edit body | `foreman note <id> "<note>"` / `foreman update <id> --body "<full body>"` | `bd comments add <id> "<note>"` / `bd update <id> --body-file -` |
| Close / reopen | `foreman close <id> --reason "<reason>"` / `foreman reopen <id>` | `bd close <id> --reason "<reason>"` / `bd reopen <id>` |
| Block / unblock | `foreman dep add <blocked> <blocker>` / `foreman dep rm <blocked> <blocker>` | `bd dep add <blocked> <blocker>` / `bd dep remove <blocked> <blocker>` |
| Graph / validate | `foreman tree <id> --json` / `foreman check --json` | `bd graph <id>` |

File ready means open, all blockers closed, not an epic; `in_progress` is the claim (no assignee field).
Filter children from JSON by `.parent`; there is no `ready --parent` flag. New ticket ids are allocated
in the main checkout by the coordinator, not by parallel build worktrees. The coordinator also owns
closure after verification and any authorized commit. Build sessions report new work to be filed.

No tracker yet, or migrating beads: ask for user-approved `foreman adopt` in the main checkout.
It registers the repo, creates or converts `tickets/`, updates instructions and installs the check hook;
it stops before committing. Don't migrate incidentally or change config to make a command succeed.
Legacy beads repos keep their embedded-store/export workflow until adopted.

## Board events: send without blocking work

Replace the leading `foreman` in each command below with `bash <this-skill-dir>/scripts/foreman-send`.
It passes the same arguments to `foreman`, caps each call at five seconds (one more to kill), and
returns zero. Missing CLI, transport failure, timeout and refusal are warnings, never failed steps.
Continue the build, report, review or commit; don't install tools or repair the service mid-step.

The CLI itself exits 0 for handled failures (warning; writes spool to Postgres when possible),
and 3 for an out-of-order claim (current stage and allowed events). Keep that diagnostic; don't
retry blindly, fabricate intermediate events or call a warning a successful board update.
`foreman show <id> --overlay --json` can clarify a refusal later. Read calls never spool.

- **Identity:** build sessions inherit `FOREMAN_ACTOR=pi`, `FOREMAN_SESSION=<build-name>` from `pi-window` (also for pane builds).
  Coordinators set `FOREMAN_ACTOR` to their harness (`claude` or `pi`) and `FOREMAN_SESSION` to their
  own session name; `--actor` / `--session` override them. Without an actor the CLI says `user`.
- **Configuration:** inherit `FOREMAN_URL` (default `http://127.0.0.1:4747`) and `FOREMAN_TOKEN_FILE`
  from the user's environment. The token file has no default. Never print credentials, add secret
  paths to tracked files, create tokens, or change config to make a board call succeed.
- **Resolution:** one ticket ID per call; repeat for each affected ticket, not the parent epic.
  Ticket prefixes resolve the repo; use `--project <configured-project>` if ambiguous or not yet
  projected. Draft slugs resolve by cwd or `--project`; use explicit project and `draft:<slug>`.
  Paths are links, not uploads: use the actual brief, spec and report paths.

## Ticket stages

| When | CLI command (through `foreman-send`) |
| --- | --- |
| After launch (`pi-window` does this) | `foreman dispatch <id> --window <window> --harness pi --model <model> --workdir <path> --branch <branch> --base <sha> --brief <path> --report <path>` |
| Build milestone: reproduced, slice green, gate passed | `foreman progress <id> "<what changed; next step>"` |
| Report file written, before the done marker | `foreman report <id> --path <report>` |
| Coordinator begins close-out, before gates/review | `foreman review <id>` |
| Review sends work back to the build session | `foreman changes <id> "<finding and required check>"` |
| Actual commit exists, user authorized it | `foreman commit <id> --sha <sha>` |
| Coordinator built and committed the work itself (no dispatch) | `FOREMAN_ACTOR=claude foreman commit <id> --sha <sha>` from queued, dispatched or building; records source `coordinator`. Pi cannot skip stages. |
| User stops / resumes abandoned work | `foreman abandon <id>` / `foreman revive <id>` |

For pane builds, dispatch's existing `--window` field carries the stable tmux `%pane-id`, while
`FOREMAN_SESSION` stays the logical build name. The CLI has no separate `--pane` switch; do not invent one.

`changes` sends the machine's `request_changes` event. A correction cycle is changes → progress →
report → review → commit; send review again for the new report. Never emit commit for planned or
uncommitted work. A stage refusal prints the current `stage` and the `next_command`: run that, filled in, and never send invented intermediate events. Board success is not verification and grants no permission to commit or push.

## Approval requests: ask and wait directly

Use `foreman ask` and `foreman wait` directly, **not** `foreman-send`: its five-second cap
and swallowed exit status are for telemetry, not decisions. Inherit the identity/configuration above.
Agents never push. Pushes go through board requests; the board worker performs approved actions.

| Kind | Ask (returns a request UUID) |
| --- | --- |
| Build-time question | `foreman ask decision <ticket> --question "<question>" --text $'What: …\nPart of: …\nFrom: …\nWhy now: …' --option "<A>" --option-detail "<A>=<what happens>" --option "<B>" --option-detail "<B>=<what happens>" --recommendation "<A>"` |
| Screenshots to review | `foreman ask review_ui <ticket> --question "Does <feature> look right?" --text "<What / Part of / Why now>" --image <file-or-folder> [--image …] --look-at "<what to check>"` (or `--artifact <https-url>`) |
| Human step (sign-in, re-login, usage reset) | `foreman ask chore <ticket> --question "<what to do>" --step "<step>" [--step …] [--key "signin:<host>"]`: one Done button; the same key joins one pending chore across tickets and repos |
| Several items, one question | `foreman ask batch <ticket> --question "<q>" --text "<What / Part of / Why now>" --item "<id>=<label>" [--item-detail "<id>=<detail>"] …`: one card, a checkbox per item; `outcome.answer` = checked ids (empty is valid). Use it instead of N identical cards |
| Fix your pending card | `foreman ask update <request-id> [--question …] [--text …] [--option … --option-detail …] [--doc …]`: only the session that asked; options given replace the list; lint still applies |
| Push | `foreman ask push <ticket> --worktree <absolute-path> --branch <local-branch> --sha <full-sha> --remote-branch <destination>` (branch with an open PR: add `--expected-old-head <its current remote sha>`) |
| Open PR | `foreman ask open_pr <ticket> --head <remote-branch> --sha <full-sha> --base <base-branch> --title "<title>" --body-file <body.md>` (`--base-ok` only for an exception you explain) |
| Merge (board-merge repos only) | `foreman ask merge <ticket> --pr <number> --sha <expected-head-sha>` |

Add `--project <configured-project>` when needed for resolution. Decision options and recommendation
are optional; `--text "<context>"` adds context. PR body-file bytes are preserved. Use the `pr` skill
for the body. Merge approval opens the existing confirmation flow; only final confirmation executes it.

Save the returned UUID, then run `foreman wait <request-id> --timeout 7200` (seconds).
Build sessions wait in their own shell; coordinators wait in the background and consume the outcome
before the dependent step. Preserve the ID across timeouts; do not post duplicate asks.

Ask/wait exit 0 even on handled refusal, transport failure or timeout. Inspect output, not `$?`:
plain ask returns a UUID on acceptance, while `--json` returns the response object. A warning is not
acceptance. Use `ask ... --json` to retain offline receipts: a spooled ask's JSON includes `warning`
plus `request_id` (plain warning output omits the ID). Retain that ID and wait after service recovery
instead of re-asking. If no ID was returned, report the unresolved ask before attempting a replacement.
Wait always prints JSON:

| Wait result | Next step |
| --- | --- |
| `state: answered` | Use `outcome.answer` and any `note`; resume the build with that decision. |
| `state: done` | The action completed; inspect `outcome` before proceeding. |
| `state: pending`, `approved`, or `executing` | Unresolved, including timeout: wait again on the same ID. |
| `state: declined` or `withdrawn` | Stop the dependent work; report the state and note. No automatic re-ask. |
| `state: wrong_question` | Ryan says the premise or options are wrong; `note` says why. Fix them and ask one corrected card. Not a "no". |
| `state: failed` or `superseded` | Inspect reason and live facts; any replacement needs a new request. For unknown/partial outcomes, observe what happened before proposing another write. |
| `warning`, missing state or unreadable output | Unresolved, not permission. Retain diagnostics/ID, report the blocker, and resume waiting when available. |

Push/open_pr require board stage `committed`. Do not close the ticket before these requests resolve:
completion supersedes pending requests. `forge = "none"` ends at commit, without action asks.
Default-branch pushes are only for one-off tickets without an epic (never in human-merge repos);
epic work reaches default through PRs. Push binds worktree, local branch, SHA and destination; open_pr binds the remote head SHA and
base. After push `done`, allow the board's branch snapshot to refresh before asking open_pr; a
snapshot refusal is not permission to open it directly. Never weaken guards or fabricate stage events.
To update a branch that has an open PR, pass `--expected-old-head`; the push must be a fast-forward.
`--force-with-lease` replaces history and the card warns Ryan; use it only when a rebase was asked for.
Open PR bases must be the repo's `merge_base` (else the forge default) or the head branch of an open
PR for a recorded blocker of this ticket (`foreman dep add`); otherwise `base_unexpected` names the
allowed bases. A board merge also retargets the child PR to that base; the merge card names it.

**Human-merge repos** (`merge_policy = "human"` on the repo or at the top of `foreman.toml`; the
work repos): every change reaches a shared branch through a GitHub PR that a person merges.
Close-out ends at `push` (to a feature branch) then `open_pr` with `--base` = the repo's
`merge_base` (or, for a stack, the parent PR's head branch). The board refuses `ask merge`
(`human_merge_policy`) and any push to the base or default branch (`human_merge_base_branch`),
one-off tickets included. Report the PR URL and keep the ticket open: forge sync moves it to
`merged` when GitHub reports the PR merged (merge commit, squash or rebase). Children of a merged
parent are not retargeted; leave that to the person on GitHub. Never fall back to `git merge`,
`gh pr merge` or a direct push.

**Writing a card.** One question per card. Put What / Part of (one-off, or the epic) / From (Asana,
Support Board T-###, Ryan's note, or "found while doing X") / Why now in `--text`, and give every
option an `--option-detail "<option>=<what happens>"`. The board refuses a decision without What,
Part of, Why now or an option detail (`card_unclear` names what is missing). Screenshots go on a
`review_ui` card, never as local paths in text: `--image` takes PNG/JPEG/GIF/WebP files or a folder
(a `verify ui` run folder gives width and theme from its result.json; otherwise `<path>@1440x900:dark`).
Images must be under the repo, `~/.cache/verify/runs` or a folder you pass with `--scratchpad`; no
symlinks. Options are fixed (Looks right / Change it); per-image comments come back in `note`. A card must make sense to
someone who has not read your session. To fix a pending card, use `ask update`; never withdraw and
repost. Use a `chore` card, not a decision, for a step only Ryan can do. **Standing answers:** Ryan
can mark an answer "Always". `ask decision` then refuses the same question and options
(`already_answered`, with `standing_answer`): use that answer. A close match is accepted but the
response carries `standing_answer` (plain output prints JSON then): if it already answers you,
withdraw the new card. Withdraw your own stale card with
`foreman withdraw <request-id> --reason "<why>"`; never leave Ryan a question that no longer applies.

**Note to every coordinator** (coordinators only): `FOREMAN_ACTOR=claude FOREMAN_SESSION=<you> foreman note --all-coordinators "<text>" --json`. Read `delivered` and `skipped` (busy, ended or gone panes are skipped, never queued).

**Card questions.** Ryan can ask about a pending card from the board. The question arrives in your
session as `[card question <request-id>] <text>`. Answer it on the card, not only in chat:
`foreman card-reply <request-id> --text "<answer>"` (or `--body-file <md>` for a longer answer).
The card stays pending; asking is not answering. A card question never changes your task.

## Project-size specs only

Keep one slug, configured project and spec path through `tight-spec` → `to-tickets`; carry them in
the handoff. Reuse an existing draft, not a new slug per session. A board draft is not a tracker ticket.

| When | CLI command (through `foreman-send`) |
| --- | --- |
| Sized as a project; choose the spec file | `foreman epic create draft:<slug> --project <project> --title "<title>" --spec <path>` |
| Interview starts (or settled decisions are synthesized) | `foreman epic spec draft:<slug> --project <project>` |
| User approves the written spec | `foreman epic approve draft:<slug> --project <project> --spec <path>` |
| Approved tickets published under a tracker epic | `foreman epic ticket draft:<slug> --project <project> --beads-epic-id <epic-id>` |
| User stops / resumes a draft | `foreman epic abandon draft:<slug> --project <project>` / `foreman epic revive draft:<slug> --project <project>` |

`epic spec` sends `start_spec`; `epic approve` sends `approve_spec`. The ticket flag is
`--beads-epic-id`, not `--bead`: this legacy flag accepts epic ids from either tracker. Small chat-only
specs create no draft. Without a draft or a published tracker epic, skip ticketing the board.

## Links and inspection

Use `foreman attach <ticket> --epic <epic>` / `foreman detach <ticket> --epic <epic>` for board-side
cross-repo membership; `--epic-project <project>` disambiguates the target. Ticket content stays untouched.
Use `foreman show <id> --overlay --json` for stage, allowed events and history;
`foreman ls --project <project> --stage building --json` for a filtered list.
