---
id: sk-clh
title: "Retire or fold the work repo's slice-loop skill into dispatch and the foreman close-out"
type: decision
status: open
priority: 2
parent: null
blocked_by: []
related: []
supersedes: []
discovered_from: null
labels: []
created: 2026-10-19
closed: null
close_reason: null
---

## Context
`~/dev/work/.claude/skills/slice-loop` (built 2026-10-03, CLAUDE.md made it the default build path 2026-10-06) predates the foreman board and `dispatch`. It now duplicates them: launch, wait, review, fix rounds, close-out.

## Parts worth keeping (decide where each goes)
- Three user gates: approve prompt, builder question, commit.
- Per-slice loop log (`<slice>.loop.md`) that answers "where were we".
- 3-round fix cap; reopen a closed pane automatically (Ryan closes idle panes).
- Reviewer agent `.claude/agents/slice-reviewer.md` (checks the diff, not the report; flags tests that prove nothing).
- Shared builder rules (`slices/_builder-rules.md`).

## Decision needed
Retire slice-loop and move these into `dispatch` + foreman close-out (and the house `code-review` skill), or keep slice-loop as the work-repo front end that calls dispatch. Update `~/dev/work/CLAUDE.md` "Build work goes to Pi by default" to name the result.
