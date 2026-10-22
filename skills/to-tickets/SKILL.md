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

## 1. Gather context

Detect the tracker in this repo: `tickets/` means ticket files (even if `.beads/` also exists);
otherwise use beads. With neither directory, ask the user to onboard with `foreman adopt`; don't
initialize or migrate a repo as part of publishing. Use the `foreman` skill for tracker commands.

Work from the conversation. If the user passes a reference (a ticket id, a spec path), read its full
body, notes/comments, and children: files use `foreman show <id> --json` and `foreman tree <id> --json`;
beads use `bd show <id>` and `bd list --parent <id>`.

For a project spec, read its design pack (`<spec-name>.design.md` beside it). If it is missing, stop and
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

Iterate until the user approves. Do not publish before approval.

## 5. Publish

Publish from the main checkout in dependency order (blockers first), so each blocker names a real id.
Build sessions hand ticket proposals to the coordinator rather than allocating ids in worktrees.

- **Epic.** If the source is an existing ticket, it is the parent: don't close or rewrite it. Otherwise
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

After publishing in either tracker, use the `foreman` skill to send `epic ticket <draft-slug> --project <project> --beads-epic-id <epic-id>` for the draft from `tight-spec`; skip when there is no draft. The legacy flag also accepts file-ticket epic ids.

## 6. Hand back

Report the epic and ticket ids with titles, and the frontier: files use
`foreman ready --json | jq --arg epic "$EPIC" '[.[] | select(.parent == $epic)]'`;
beads use `bd ready --parent <epic>`. Say what can start now and what could run in parallel.
Then stop. Implementation starts only when the user says so.
