---
name: code-review
description: Review a diff since a fixed point on Standards and Spec axes, plus Risk when asked what it could break; and handle review feedback. Use for "review this branch/PR/since X", "what could this break", or when acting on review comments.
---

<!-- house: merge; from: mattpocock:skills/engineering/code-review@49dd158, superpowers:skills/requesting-code-review@bb92a77, superpowers:skills/receiving-code-review@bb92a77, pstack:pstack/skills/blast-radius@850d7f2, pstack:pstack/agents/comment-sicko.md@850d7f2; house edit 2026-10-16: axes run sequentially unless the user asked for subagents -->

# Code Review

Two jobs: **giving** a review of a diff, and **receiving** review feedback. Reviews report; they do not edit code.

## Giving a review

### 1. Pin the fixed point

Use the ref the user named (SHA, branch, tag, `main`, `HEAD~5`); ask if none. Then:

- `git rev-parse <ref>` resolves, and `git diff <ref>...HEAD` (three-dot, against the merge-base) is non-empty.
  Fail here, before any axis runs.
- Note `git log <ref>..HEAD --oneline`. Include uncommitted work only if the user asked to.

### 2. Gather context

- **Spec**, in order: issue/bead ids in commit messages (`bd show <id>`, or the repo's tracker), a path the user
  gave, a spec under `docs/`/`specs/` matching the branch. If none, ask; if there is none, skip the Spec axis and
  say so.
- **Standards**: every file that says how code is written here: AGENTS.md/CLAUDE.md (root and local),
  CONTRIBUTING.md, CODING_STANDARDS.md, linter/formatter config. Always add the baseline in
  `references/standards-baseline.md`; documented repo standards override it, and tooling-enforced rules are
  skipped.

### 3. Run the axes

Briefs for each axis: `references/reviewer-briefs.md`.

- **Default, and always inside a pi build window:** run the axes yourself, one after another, using each axis's
  brief as its checklist. Finish and write up one axis before starting the next so they do not blur.
- **Only when the user asked for subagents:** one fresh subagent per axis, all dispatched together, each given
  precisely crafted context (never your session history). Use the `reviewer` agent definition if installed,
  otherwise a general-purpose subagent with the brief pasted in. As the coordinator without that request, ask
  the user before spawning.

- **Standards**: does the diff follow this repo's documented standards and the baseline?
- **Spec**: does it do what the spec asked: missing, partial, wrong, or unrequested (scope creep)?
- **Risk** (only when asked "what could this break", or the diff touches persistence, wire formats, public APIs,
  shared config, or concurrency): what breaks outside the diff, and the one fact it is safe because of, proven by
  running code. Method: `references/blast-radius.md`.

### 4. Aggregate

If saving the review, use `$(foreman doc path review <id> --next)`, or `$(foreman doc path note audit <slug>)` without a ticket; see the `foreman` skill's Documents section.

Present each axis under its own heading (`## Standards`, `## Spec`, `## Risk`), lightly cleaned. Order findings
by severity **within** an axis (Critical / Important / Minor); do not merge or rerank across axes, since a change
can pass one and fail another. Include each reviewer's "declined to judge" list for the user to rule on. End with
one line: findings per axis and the worst issue in each.

Spot-check any finding you relay as Critical: open the cited `file:line` and confirm it says what the reviewer
claims.

## Receiving a review

Feedback is a set of claims to verify, not instructions to obey. Details and examples:
`references/receiving.md`.

1. **Read all of it** before changing anything. If any item is unclear, ask about it before implementing the
   others; items are often related.
2. **Verify each item** against the code: is it true here, does it break something that works, is there a reason
   for the current shape, is the suggested feature actually used (grep before "implementing it properly")?
3. **Respond with substance**: a fix with its location, or pushback with evidence (`file:line`, a test, a
   command's output). No performative agreement or thanks.
4. **Ask the user** when feedback conflicts with their earlier decisions or is architectural.
5. **Implement one item at a time**, blocking issues first, running the relevant check after each. Then
   `verify-before-claiming`.

If you pushed back and were wrong, say so in one line with what you checked, and fix it.
