---
id: sk-f19
title: "Walkthrough skill: player, recorder and live mode"
type: task
status: open
priority: 2
parent: null
blocked_by: []
related: []
supersedes: []
discovered_from: null
labels: []
created: 2026-11-13
closed: null
close_reason: null
---

Part of foreman epic fm-uo5 (spec ~/dev/foreman/docs/specs/try-it.md, decisions 13 to 15).

## What to build
A `walkthrough` skill with a script on Playwright.
- File shape (decision 13): JSON with intro, seed (commands), steps of say, changed, do (goto <path>, click <selector>, fill <selector> <text>, wait <selector>), see, check (selector). Paths relative to a base url.
- `walkthrough play <file> --url <base>`: visible browser with an injected side panel (intro, then per step say / changed / see, Back and Next); Next runs the step's do; the page stays clickable.
- `walkthrough record <file> --url <base> --out <dir>`: headless run of all steps, saves a .webm video, exits non-zero naming the step whose check is missing.
- `walkthrough check <file>`: validates the shape without a browser.
- SKILL.md: how a builder writes the file (intro for someone who has not read the ticket; 3 to 8 steps; main path and the most likely failure), and the live mode for coordinators: Claude in Chrome, new tab on the preview, intro in chat, one step at a time with what changed, wait for Ryan before the next step; only when Ryan asks.

## Interfaces
Produces: the walkthrough JSON shape, which the foreman card (fm-uo5.1) stores and shows.

## Acceptance
- [ ] Spec check 6a on a scratch app (a static page is enough until fm-uo5.3 lands): record saves a video and exits 0; removing one checked element makes it exit non-zero naming that step; play shows the panel and Next runs each step.
- [ ] Tests for the shape check.
