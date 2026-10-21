---
id: sk-k9j
title: "pi-window: --model is ignored; builds start on Opus (API billing) until /model + /bifrost pin"
type: bug
status: open
priority: 1
parent: null
blocked_by: []
related: []
supersedes: []
discovered_from: null
labels: []
created: 2026-10-21
closed: null
close_reason: null
---

2026-10-20: two dispatch builds (foreman parked, kind-sections) launched with -- --model openai-codex/gpt-6-astra still started on anthropic/claude-opus-5-5; Bifrost routing overrides the CLI model. Workaround used: Escape, /model openai-codex/gpt-6-astra, Enter (twice if the model picker is still refreshing), /bifrost pin, then resend the task. Fix: pi-window (and relay open) should pin the requested model at start (bifrost pin flag or env) and verify the footer before handing back.

## Notes
- 2026-10-21 user: 2026-10-21 hypothesis (main coordinator): pi-window passes --model correctly and sends the brief as pi's FIRST message at launch; the Bifrost extension starts unpinned ('Bifrost · on', footer '(auto)') and routes that first turn to Opus. relay open starts pi idle, the coordinator pins (/bifrost pin), then sends, and relay builds came up on Astra every time today (3 of the pi-window launches were on Opus). Fix candidates: start pi pinned (a Bifrost env/flag if one exists), or have pi-window open idle, pin, then send the brief like relay. Unverified: where Bifrost reads its pin state.
