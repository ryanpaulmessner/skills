---
id: sk-fip
title: "Planning flow: pstack statechart (v0.15.36) + designer UX skills from upstream"
type: feature
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
close_reason: "Committed 827167e (UX skills pick) + 4684679 (statechart + planning flow), ff to main, linked. mise install waits on board card 310281d8."
---

Ryan 2026-10-29: take the statechart skill from pstack v0.15.36 (cursor/plugins c742dd6) and use it where the planning flow asks for state diagrams (tight-spec, wayfinder, design-pack); pull the UX design skills from upstream rpmessner/skills (1888d52, sk-plp: ux-critique, ux-laws, ui-patterns, information-architecture) and say when each runs in the spec skills and the foreman/dispatch workflow.

Plan:
- Cherry-pick 1888d52 only (not the other upstream commits: devserve/dispatch/foreman/orient conflict with house versions; separate sync).
- statechart: own source pin (pstack-statechart, separate clone at c742dd6, scope pstack/skills/statechart), mode adapt (test corpus left out), stays user-invoked; design-pack follows it for new or changed machines and stateful app flows.
- Edits: tight-spec (state table + rules per machine/flow; UI states), design-pack (State: statechart for proposed machines; UI: ux-critique on mockups), wayfinder (state-model prototype), to-tickets (UI states in acceptance), dispatch close-out (ux-critique on UI shots), flow map.
- Follow-up: full pstack sync 850d7f2 -> c742dd6 (create/maintain-formal-verification-skill, ketchup-video, merged-skill diffs).
