---
id: sk-jy8
title: "dispatch and foreman skills write ticket summaries (for foreman This week)"
type: task
status: open
priority: 2
parent: null
blocked_by: []
related: []
supersedes: []
discovered_from: null
labels: []
created: 2026-10-21
closed: null
close_reason: null
kind: internal
---

## What to build
House skills write a plain-English `## Summary` in the ticket file at three points, so the foreman This week page (fm-49x, spec ~/dev/foreman/docs/specs/this-week.md decisions 12 and 14) has text without Ryan asking:
- `dispatch`: at launch (what it is and why), after the PR opens (what changed, what users will see), at close-out (final state, what is left open).
- `foreman`: the close instructions include writing or updating `## Summary`.
Format, under `## Summary`: `Title:` (optional), `What users see:`, `How it works:`, `Open or risky:`, `Report line:`. Plain English (ASD-STE100), no jargon.

## Acceptance
- [ ] Both skills name the three points and the exact format; the `writing-for-agents` check passes.
- [ ] A dry run on one real work ticket produces a Summary the foreman projection parses (after fm-49x.3 lands).
