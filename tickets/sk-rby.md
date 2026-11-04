---
id: sk-rby
title: "dispatch: pi-window records session identity for the Sessions pages (foreman fm-9mm.11)"
type: task
status: open
priority: 2
parent: null
blocked_by: []
related: []
supersedes: []
discovered_from: null
labels: []
created: 2026-11-04
closed: null
close_reason: null
---

Skills-repo half of foreman ticket fm-9mm.11 (Sessions, Decision 3). pi-window (window and pane mode) generates a Pi session id, starts pi with --session-id, and dispatches with --name --pi-session --coordinator; the in-pane register adds --parent and a 5 s cap. dispatch and foreman SKILL.md document the flags. Built in ~/dev/skills-worktrees/sessions-launch (branch feat/sessions-launch, 3df1326); tests: test_pi_window 20 OK; scripts/check.py clean.
