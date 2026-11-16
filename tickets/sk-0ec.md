---
id: sk-0ec
title: "Move foreman rules into the foreman skill"
type: task
status: open
priority: 2
parent: null
blocked_by: []
related: []
supersedes: []
discovered_from: null
labels: []
created: 2026-11-16
closed: null
close_reason: null
---

Retro finding 11 (foreman notes/2026-11-13-retro-coordinator-workflows.md). Rules about foreman live in coordinator memory and the foreman-board handoff where build agents never read them. Move each one into the foreman (or dispatch) skill once, and delete the other copies.

- [ ] Each moved rule exists in one place
- [ ] check.py passes within the token budget
