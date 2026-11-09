---
id: sk-qgs
title: "Skills write documents through foreman doc path"
type: task
status: closed
priority: 2
parent: null
blocked_by: []
related: []
supersedes: []
discovered_from: null
labels: []
created: 2026-11-06
closed: 2026-11-09
close_reason: "skills PR #3 merged (cde86c3)"
---

Skills half of foreman fm-qpm.3 (doc layout, docs/specs/doc-layout.md in ~/dev/foreman). The foreman skill gets a Documents section; dispatch, pr, research, tight-spec, design-pack, to-tickets, wayfinder, handoff and code-review point to it; pi-window defaults the report path from foreman doc path report <first ticket>.

## Acceptance
- [ ] No listed skill tells an agent to write under drafts/, docs/briefs, docs/sessions or /tmp/briefs.
- [ ] test_pi_window.py covers the default report path and the fallback.
