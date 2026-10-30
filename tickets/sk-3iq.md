---
id: sk-3iq
title: "Track the Pi extensions and prompt templates that live only in ~/.pi/agent"
type: task
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

## Problem
These files are in use but in no repo (created 2026-10-03..10-06), so a machine rebuild or a bad edit loses them:
- `~/.pi/agent/extensions/relay.ts` (mailbox; see the dispatch relay ticket)
- `~/.pi/agent/extensions/initiative.ts` (session bar: `/s`, Alt+1..9, parked sessions, owner lock) and launcher `~/dev/work/tools/initiative/bin/initiative`
- `~/.pi/agent/prompts/`: `commit.md`, `pr.md`, `plain.md`, `implement.md`, `where.md`, `review.md`

## What to do
Move them into the house repo (`pi/` packages next to `house-guard` and `foreman-wait`, linked by `link.py`), or retire each one that foreman now covers. `initiative.ts` overlaps foreman session parking and relaunch (fm-3c3.4) and pane-mode builds (sk-fkb): decide keep, merge or drop. Prompt templates may overlap house skills (`pr`, `finishing-a-development-branch`).

## Check
`link.py` recreates every kept file; Pi loads them after a fresh link (`/reload`); nothing remains only in `~/.pi/agent`.
