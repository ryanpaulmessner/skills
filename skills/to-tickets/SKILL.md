---
name: to-tickets
description: "Break an approved spec, plan, or conversation into tracer-bullet tickets with blocking edges and acceptance criteria, published under an epic in the repo's tracker. Use for /to-tickets or after tight-spec approval."
disable-model-invocation: true
---

<!-- house: adapt; from: mattpocock:skills/engineering/to-tickets@49dd158, superpowers:skills/writing-plans@bb92a77, pstack:pstack/skills/figure-it-out@850d7f2 -->

# To Tickets

Break a spec, plan, or conversation into **tickets**: tracer-bullet vertical slices, each declaring the
tickets that **block** it, published to the repo's tracker. Then give a short rundown and stop for pushback.
This skill plans; it never starts implementing.

## 0. Start gate

Run this skill only when one of these is true:

- The user typed `/to-tickets` in this session.
- The user answered **Break into tickets** on a board card for this spec (`state: answered`). The
  Skill tool cannot start this skill, so read this file (`to-tickets/SKILL.md` in the skills directory)
  and follow it.

Otherwise, with an approved spec in hand, post the card and wait. Do not start on your own
judgement, and do not ask only in chat:

```bash
foreman ask decision <epic-or-draft-ticket> --question "Break <spec name> into tickets?" \
  --text $'What: break the approved spec into tickets with blocking edges\nPart of: <epic>\nFrom: <session>\nWhy now: the spec was approved; no build can start without tickets' \
  --doc <spec path> --doc <design pack path> \
  --option "Break into tickets" --option-detail "Break into tickets=I draft the tickets and send the list back on a card before I publish" \
  --option "Not yet" --option-detail "Not yet=no tickets; say what to change in the note" \
  --recommendation "Break into tickets"
foreman wait <request-id> --timeout 7200   # background
```

## 1. Gather context

Detect the tracker in this repo: `tickets/` means ticket files (even if `.beads/` also exists);
otherwise use beads. With neither directory, ask the user to onboard with `foreman adopt`; don't
initialize or migrate a repo as part of publishing. Use the `foreman` skill for tracker commands.

Work from the conversation. If the user passes a reference (a ticket id, a spec path), read its full
body, notes/comments, and children: files use `foreman show <id> --json` and `foreman tree <id> --json`;
beads use `bd show <id>` and `bd list --parent <id>`.

For a project spec, read its design pack at the path defined in the `foreman` skill's Documents section. If it is missing, stop and
run the `design-pack` skill, then show the pack to the user before drafting tickets: the user approves
a spec with its pack, never without. A pack part skipped with a reason is fine.

## 2. Explore the codebase

If you haven't already, explore enough to know the current state. Use the project's glossary vocabulary
in titles and descriptions, and respect ADRs in the area. Look for prefactoring that makes the work
easier: "make the change easy, then make the easy change."

## 3. Draft vertical slices

<vertical-slice-rules>

- Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests): vertical, NOT
  a horizontal slice of one layer.
- A completed slice is demoable or verifiable on its own.
- Each slice fits in a single fresh context window.
- A ticket is the smallest unit that carries its own test cycle and is worth a reviewer's gate. Fold
  setup, config, scaffolding, and docs into the ticket whose deliverable needs them; split only where a
  reviewer could reject one ticket while approving its neighbor.
- Prefactoring goes first. Among independent slices, put the riskiest unknown first.

</vertical-slice-rules>

Give each ticket its **blocking edges**: the tickets that must complete before it can start. Only real
gates — a ticket with no blockers can start immediately, and parallel work stays parallel.

When one ticket hands a named contract to another (a function, message, schema, event), note it under
**Interfaces** in both: what it produces, what it consumes. Names and shapes, not file paths.

**Wide refactors are the exception.** One mechanical change whose blast radius fans across the codebase
(rename a column, retype a shared symbol) can't land green as a vertical slice. Sequence it
expand–contract: expand (add the new form beside the old) → migrate call sites in batches sized by blast
radius, each blocked by the expand → contract (delete the old form), blocked by every batch. If batches
can't stay green alone, they share an integration branch and all block a final integrate-and-verify
ticket; green is promised only there.

**Self-check before showing the user:**

- **Coverage** — every spec acceptance check and decision maps to a ticket. Add tickets for gaps.
- **Failure modes** — inputs or conditions the spec implies but no ticket exercises get an acceptance
  criterion on the ticket that owns that code.
- **States** — each UI ticket's acceptance names every state its screen can enter (empty, loading,
  partial, error, success) with its copy, per the `ui-patterns` skill; each ticket that adds or changes
  a state machine names the rules it must keep, from the spec's state table. A pack line "Formal check:
  recommended" becomes its own ticket, blocked by the build ticket: run `create-formal-verification-skill`*
  on the built code for that property (the user starts it; it leaves a repo-local verify skill).
- **No empty lines** — "handle edge cases", "add validation", "TBD" decide nothing. Replace or delete.
- **Proportion** — tickets carry decisions, not transcripts of the code.

## 4. Rundown and pushback

Present the breakdown as a numbered list. For each ticket:

- **Title** — short, descriptive
- **Blocked by** — which tickets (if any)
- **What it delivers** — the end-to-end behavior it makes work

Ask:

- Does the granularity feel right (too coarse / too fine)?
- Is each blocking edge a genuine gate?
- Should any tickets merge or split?

When the run started from a board card, or the user is not answering in this session, put the rundown
on the board instead of only in chat: write the numbered list and three questions to
`$(foreman doc path plan <epic-id>)`, or `$(foreman doc path note decision <slug>)` before an epic
exists; see the `foreman` skill's Documents section. Then post `foreman ask decision` with `--doc` on that file, options
**Publish** and **Change** (the note says what to change), and wait in the background. On **Change**,
revise the file and the same card with `foreman ask update <request-id> --doc …`, then wait again.

Iterate until the user approves (**Publish** on the card, or "publish" in chat). Do not publish before approval.

## 5. Publish

Publish from the main checkout in dependency order (blockers first), so each blocker names a real id.
Build sessions hand ticket proposals to the coordinator rather than allocating ids in worktrees.

- **Epic.** If the source is an existing ticket, it is the parent: don't close it or rewrite its body,
  but set its type to `epic` if it is not one already (`foreman update <id> --type epic`); the board
  links a draft only to an epic. Otherwise
  create an epic whose body is the approved spec (Goal, Non-goals, Acceptance checks, Ask-first
  boundaries) so every ticket inherits it from one place.
- **Files (`tickets/`).** Follow `references/files.md`: one `foreman new` per ticket with `--parent`
  and `--blocked-by`, and a body with What to build, Interfaces if any, and Acceptance checkboxes.
  Run `foreman check`; verify the created ids and edges before handing the files to the coordinator
  for an authorized commit. Ticket commands run directly, never through the best-effort board sender.
- **Beads (`.beads/`, no `tickets/`).** Follow `references/beads.md`: one `bd create` per ticket with
  `--parent`, `--deps`, description and acceptance checklist.

Avoid file paths and code snippets in tickets — they go stale. Exception: a prototype snippet that pins a
decision better than prose (state machine, schema, type shape), trimmed and labeled.
Give each ticket the slice of the design pack it builds: the ER fragment for its tables, the proposed
transitions it adds, the flow it makes work. Copy the Mermaid block (trimmed to that ticket) and link
the pack; the builder builds to that shape.

### Link the board draft (required)

The board moves the initiative from "spec approved" to planned and shows its tickets only after this
step. Run it directly, not through the best-effort sender, so a refusal is seen:

1. Find the draft: the slug `tight-spec` passed, or the board draft whose spec path is this spec. No
   draft exists only for a small chat-only spec; say so in the hand-back.
2. `foreman epic ticket draft:<slug> --project <project> --beads-epic-id <epic-id>` (the legacy flag
   takes file-ticket epic ids too).
3. On a refusal, fix the cause and run it again:
   - `file ticket must have type epic` / `beads_epic_required`: set the epic's type to `epic`, run
     `foreman check`, and send it again. The board syncs the ticket on the next send.
   - `invalid` from a state other than `spec_approved`: the spec approval event never reached the
     board. Send `foreman epic approve draft:<slug> --project <project> --spec <spec> --design <pack>`,
     then send `epic ticket` again.
4. Still refused: post a `chore` card with the exact command and the error, and say it in chat. A
   refusal written only in a handoff note is not done.

Done when the board shows the draft as planned (`ticketed`) under the epic id, with its tickets.

## 6. Hand back

Report the epic and ticket ids with titles, the draft's board state (`ticketed`, or the open card),
and the frontier: files use
`foreman ready --json | jq --arg epic "$EPIC" '[.[] | select(.parent == $epic)]'`;
beads use `bd ready --parent <epic>`. Say what can start now and what could run in parallel.
Then stop. Implementation starts only when the user says so.
