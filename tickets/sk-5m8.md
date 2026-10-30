---
id: sk-5m8
title: "dispatch: steer pi builds through a file mailbox (relay) instead of tmux send-keys"
type: feature
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
`dispatch` steers build sessions with `tmux send-keys -l "<text>"` + `Enter` (dispatch SKILL.md ~72-83). The 2026-10-03 history audit found keystroke steering is where relays break: 29 multi-line messages split into separate turns, 40+ duplicate sends, and messages typed into the wrong pane. A keystroke also mixes with whatever Ryan is typing in that pane.

## What exists (proven 2026-10-03..10-06, ~10 slices)
- Pi extension `~/.pi/agent/extensions/relay.ts`: a named session gets `~/.pi/agent/relay/<name>/` with `inbox/` (delivered by `pi.sendUserMessage` only when idle), `outbox/<id>.md|.json` written on `agent_settled`, `status.json` (idle|busy|waiting_on_user|paused|parked|closed), `/relay pause|resume`.
- CLI `~/dev/work/tools/relay/bin/relay`: open (splits beside `$TMUX_PANE`), send, wait (exit 0 reply / 2 waiting on Ryan / 3 closed / 4 timeout; parked = pending), status, ls.
- Not in any repo yet (see the Pi-extensions tracking ticket).

## What to build
Make the mailbox the steering path in `dispatch`/`pi-window`: send = write inbox file; done = outbox `.json`; keep send-keys only as a fallback. Optionally emit the foreman `report` event from the outbox write. Keep `pi-wait`'s limit detection (sk-tjc).

## Check
A multi-line brief and a fix round reach a pane build with no split turns while Ryan types in the pane; `relay wait` returns the reply; board stages unchanged.
