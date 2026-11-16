---
name: implement
description: "Build the work described by approved beads tickets or a spec: claim, TDD at agreed seams, verify, review, close. Use when the user says implement/build/execute these tickets, names a bead id, or hands over a spec whose tickets passed rundown and pushback."
disable-model-invocation: true
---

<!-- house: merge; from: mattpocock:skills/engineering/implement/SKILL.md@49dd158, mattpocock:skills/engineering/implement-spec/SKILL.md@49dd158, superpowers:skills/executing-plans/SKILL.md@bb92a77, superpowers:skills/subagent-driven-development/SKILL.md@bb92a77, superpowers:skills/subagent-driven-development/implementer-prompt.md@bb92a77, superpowers:skills/dispatching-parallel-agents/SKILL.md@bb92a77, pstack:pstack/skills/swarm/SKILL.md@850d7f2 -->

# Implement

Turn approved tickets into verified code, one ticket at a time. The tickets already did the thinking; this skill executes them and leaves evidence.

## Before starting

1. **Approval gate.** The tickets must have been through plan → tickets → rundown → user pushback. If not, stop and give the rundown first. Never build the maximal reading of a vague ticket; use `tight-spec` if scope can still drift.
2. **Load the work.** For each ticket: `bd show <id>`, state its title. Ambiguous reference → ask. With a spec, read it once; it is the authority the tickets argue from.
3. **Frontier.** Tickets form a graph, not a list. `bd ready` gives the frontier; work in dependency order.
4. **Pick a mode.** Inline is the default. Use subagent mode only when the user asked for delegation (see below).
5. **Commits.** Commit only if the user asked in this request or standing instructions. If they did: granular, one or more per ticket, never on main/master without consent.

## Per-ticket loop

1. **Claim.** `bd update <id> --claim`. Record BASE (`git rev-parse HEAD`) if commits are in play.
2. **Seams.** Use the seams recorded on the ticket. If none, propose them and confirm before the first test (`tdd` owns this).
3. **Build.** Run the `tdd` skill at those seams. Compile/typecheck and the focused test often; the full suite once at the end of the ticket.
4. **Rulings, not stalls.** Ticket is wrong or ambiguous in a small way → decide the smallest change that satisfies the spec, record it: `bd update <id> --append-notes "Ruling: <what> — <why> — <cost if wrong>"`, continue. Unrecorded deviation is a decision made in secret.
5. **Scope.** Anything the ticket did not ask for is a new bead (`bd create ... --deps discovered-from:<id>`), not a "while I'm here" edit.
6. **Verify.** Run `verify-before-claiming`. A failing verifier is a blocker, not a footnote.
7. **Review.** Run `code-review` on this ticket's change (since BASE, or the working-tree diff). Critical/Important findings: fix each with a failing test first, rerun the suite. Minor findings: new bead or ruling note, not silent fixes.
8. **Close.** `bd close <id> --reason "<evidence: command → result>"`. Close only with evidence; known gaps stay open or become beads.

Stop and ask only for: an irreversible or destructive operation; a security-sensitive action; an outward side effect (push, merge to a shared branch, publish, deploy to a live client); a ticket so wrong that every path is a guess.

**Compaction.** Beads plus `git log` are the ledger. After losing context, trust `bd list --status in_progress`, closed tickets, and ruling notes over memory; never redo a closed ticket.

## Subagent mode

Use when the user asked to delegate, or for long ticket sets where later tickets would run on a compacted context. Dispatch with the harness's subagent tool (Claude Code: Agent/Task; pi: `subagent`). If none exists, run inline; never fabricate a dispatch.

- **You are the controller.** You claim, review, rule, and close. You do not write ticket code yourself, so review stays independent and your context stays clean.
- **One fresh implementer per ticket**, built from pointers (bead id, spec path, seams, constraints, report path), not pasted history. It runs `tdd`, never dispatches subagents itself, and returns a short status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT. Brief template: [references/subagent-mode.md](references/subagent-mode.md).
- **Review between tickets.** After DONE, run `code-review` on BASE..HEAD yourself. Findings go back to the same implementer (resume, or a fresh one carrying the report file). For Pi builds, apply the `dispatch` skill's [Billing and fallback](../dispatch/SKILL.md#billing-and-fallback) policy to stuck reviews; for other harnesses, after 3 fix rounds rule on each open finding in the bead notes, or escalate.
- **BLOCKED / NEEDS_CONTEXT** means something must change: more context, a stronger model, a smaller ticket, or a ruling. Never re-dispatch the identical brief.
- **Model tier.** For Pi builds, use the `dispatch` skill's [Billing and fallback](../dispatch/SKILL.md#billing-and-fallback) policy. For other harnesses, name the tier explicitly (an omitted model inherits the session's): cheap for transcription of a complete spec, standard for multi-file work, strongest for design judgment and the final review.
- **Batch small same-shape tickets** (the same one-line change across files) into one dispatch and one review.

### Parallel tickets

Only for tickets with no blocking relation and disjoint files. Requires commit permission (work merges through branches).

- One worktree and branch per implementer, cut from an integration branch; one writer per worktree.
- Every brief stands alone. Results report PASS / ISSUES / BLOCKED with evidence; a missing or unevidenced result is a gap, not a pass. Re-dispatch once, then report the gap.
- You merge finished branches into the integration branch one at a time, rerunning the full suite after each merge. Newly unblocked tickets go out as the frontier moves.
- Clean up worktrees when done. Merging the integration branch anywhere shared is an outward side effect: ask.

## Finish

When more than one ticket landed, run `code-review` once over the whole change (merge-base..HEAD). Fix Critical/Important findings in one pass, each with a failing test first.

Report:
- **Closed**: tickets with their evidence.
- **Rulings I made**: every ruling note, with its cost if wrong. Exhaustive.
- **Deferred**: minors and discovered work, as bead ids.
- **Not verified**: anything unchecked, and why.
- Commits made, or the suggested commit plan if commits were not authorized.
