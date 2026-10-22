---
id: sk-n4p
title: "Design pack before ticketing: data, state and flow diagrams"
type: feature
status: closed
priority: 2
parent: null
blocked_by: []
related: []
supersedes: []
discovered_from: null
labels: []
created: 2026-10-22
closed: 2026-10-22
close_reason: "700aeec design-pack skill + tight-spec/wayfinder/to-tickets/flow; board side fm-44e live"
---

From: Ryan, 2026-10-21: before /to-tickets, show database diagrams of the feature and its changes, state diagrams and flow diagrams (especially flows that touch existing state machines), plus design artifacts, so the feature can be reviewed visually before approval and ticketing.

Plan (pending Ryan's cards):
- New shared skill design-pack, run by tight-spec before spec approval and by wayfinder when the map destination is a spec; to-tickets checks for it.
- Data: Mermaid erDiagram of the tables touched, read from the real schema, with new/changed/removed tables and columns marked; list of migrations.
- State: each touched state machine drawn from code (ReportSystem.StateMachine transitions/0 and actions/0; foreman Fsm to_mermaid), current vs proposed with changes marked; new machines from the spec state table.
- Flows: sequence diagrams of the main user flows, each step naming the state transition it fires.
- UI: mockups from the real app CSS (existing rule), as artifacts linked from the pack.
- Output: <spec>.design.md beside the spec (Mermaid source); to-tickets copies the relevant diagram into each ticket.
- Foreman side: fm ticket (render Mermaid, design link on the draft epic).

## Notes
- 2026-10-22 user: Ryan 2026-10-22: card c79d5b53 = Board page (diagrams drawn on the draft epic page, fm-44e); card 41a9e686 = Required, with skip reason. Skill design-pack added; tight-spec, wayfinder, to-tickets and flow updated.
