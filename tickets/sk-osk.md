---
id: sk-osk
title: "Full pstack sync 850d7f2 -> c742dd6 (0.15.25 -> 0.15.36)"
type: task
status: open
priority: 2
parent: null
blocked_by: []
related: []
supersedes: []
discovered_from: null
labels: []
created: 2026-10-29
closed: null
close_reason: null
---

From sk-fip. statechart got its own pin (pstack-statechart). The main pstack pin stays at 850d7f2 until skills-sync decides: new create-formal-verification-skill, maintain-formal-verification-skill (TLA+ verify skills, pair with statechart), ketchup-video; diffs in merged sources (sharpen, figure-it-out, principles, verification). After the full sync, fold pstack-statechart back into the pstack source.

## Notes
- 2026-10-30 user: 2026-10-30: pstack pin is now 4dd1d05 (newer than 0.15.36) via upstream c83c9d6. Left: review the changes to merged skills listed in reports/2026-10-29.md (sharpen into tight-spec, etc.).
