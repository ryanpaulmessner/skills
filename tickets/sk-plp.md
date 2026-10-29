---
id: sk-plp
title: "Reconcile designer-skills into the house set (curated core)"
type: task
status: closed
priority: 2
parent: null
blocked_by: []
related: []
supersedes: []
discovered_from: null
labels: []
created: 2026-10-29
closed: 2026-10-29
close_reason: "Source designer pinned 9a6930c; ux-critique, ux-laws, ui-patterns, information-architecture added; 50 drops; check.py 62 skills ~2468/2500, 0 errors; MIT notice added."
---

Add Owl-Listener/designer-skills (MIT, pinned 9a6930c) as source `designer` at ~/dev/utils/skill-sources/designer-skills. Curated core: ux-critique (merge visual-critique/* + heuristic-evaluation), ux-laws (merge 17 law skills), ui-patterns (merge ux-writing, loading-states, error-handling-ux, feedback-patterns), information-architecture (adapt, user-invoked). Every other upstream skill gets a [[drop]] with a reason. Done when scripts/check.py passes with 0 errors under the always-on budget, link.py links the new skills, and THIRD_PARTY_NOTICES carries the MIT notice. ai-design-skills collection is out of scope (user decision).

## Notes
- 2026-10-29 user: Implemented: source designer pinned 9a6930c; 4 house skills (ux-critique, ux-laws, ui-patterns, information-architecture[user-invoked]); 50 drops; check.py 62 skills ~2468/2500, 0 errors; linked into ~/.claude/skills and ~/.agents/skills. Uncommitted pending user.
