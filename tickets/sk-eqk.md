---
id: sk-eqk
title: "analyze-sessions: run the weekly intervention report on a schedule"
type: task
status: open
priority: 2
parent: null
blocked_by: []
related: ["sk-81s.8"]
supersedes: []
discovered_from: null
labels: []
created: 2026-10-19
closed: null
close_reason: null
---

## Context
`skills/analyze-sessions` (built 2026-10-05) has a weekly intervention-report workflow: extract, `stats`, `interventions`, group by cause, propose one fix per repeated cause, write `~/dev/work/notes/interventions/<date>.md`. It ran once (2026-10-05); nothing triggers it. Its cache (`~/.cache/analyze-sessions/messages.jsonl`) only keeps messages if `extract` runs before Claude Code deletes transcripts (30 days; see the dotfiles cleanupPeriodDays ticket).

## What to do
Run `extract` plus the report weekly (report-only, like sk-81s.8), and remind Ryan when a report is ready. Never apply fixes automatically.
