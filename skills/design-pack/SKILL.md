---
name: design-pack
description: Draw the data, state and flow diagrams of a spec before the user approves it. Use from tight-spec or wayfinder before spec approval, or when to-tickets finds a project spec without a design pack.
---

<!-- house: own -->

# Design pack

A design pack lets the user see a feature before approving the spec: which tables change, which state
machines change, and how the main flows move through them. It is one Markdown file beside the spec,
`<spec-name>.design.md`, with Mermaid diagrams. The foreman board draws them on the draft epic page.

Every project-size spec needs a pack before approval. A part can be skipped only with a one-line reason
under its heading ("Skipped: no schema change"). A pack with every part skipped still exists, so the user
sees that the question was asked.

## Rules

- **Draw the current state from the code, never from memory or the spec.** Read the real schema (migrations,
  schema modules, or a read-only query of a local or staging database) and the real state machine
  definitions. When the repo declares machines as data, generate from that data: for example a module
  with `states/0`, `transitions/0`, `actions/0`, or a `to_mermaid/0` function. Name the source under
  each diagram ("from: `transitions/0` of <module>, at <short sha>").
- **Mark every change.** Proposed diagrams show what is new, changed or removed, with a legend. Use
  Mermaid `classDef` styles (`added`, `changed`, `removed`) on nodes and labels like `+ column`,
  `~ column`, `- column` in ER entities. A reader must see the delta without comparing two pictures.
- **Only what the feature touches**, plus one hop of context (a table it joins, a machine whose event it
  fires). A pack is not a schema dump.
- **Facts only.** A table, column, state or event that does not exist yet is marked as proposed. If you
  could not read something, say so in the pack; do not draw a guess.
- Mermaid must parse: put labels with punctuation in double quotes, and keep `;` and `{}` out of labels.
  Check each block with the Mermaid CLI if it is installed; otherwise read it once more for syntax.

## The file

```markdown
# Design pack: <feature>

Spec: <spec path> · Drawn at: <repo> <short sha> · Legend: green = added, amber = changed, red = removed

## Data
<erDiagram of the touched tables, current columns that matter plus marked changes>
<a short table: migration, what it does, reversible? backfill? rows affected (from a count if you can run one)>

## State
<per touched machine: "Now" stateDiagram-v2 from code, "Proposed" with changes marked;
 new machines from the spec's state table. Under each: events added/changed, guards, and which
 code or user action fires each new event.>

## Flows
<per main user flow: sequenceDiagram user → UI → context/service → DB/jobs.
 Annotate each step that fires a state event with the machine and event ("Ticket: start_work").
 Include the failure path that matters most (refused transition, job retry).>

## UI
<links to mockup artifacts built from the app's real CSS and markup, one line each on what it shows;
 or "Skipped: <reason>">
```

## Steps

1. Read the spec's Decisions (and its state table, if any). List the tables, machines and flows it
   touches. If the list is empty for a part, write that part's skip reason now.
2. Read the current schema and machines from the code; draw "Now". Then draw "Proposed" with the marks.
3. Draw the flows. Every state event named in the spec appears in at least one flow; every new table
   is written or read in at least one flow. A gap here is usually a gap in the spec: fix the spec too.
4. UI part: if the spec changes a page, build or link mockups (repo rules on mockups apply).
5. Save the file beside the spec. With a foreman draft epic, pass it on approval:
   `foreman epic approve draft:<slug> --project <p> --spec <spec> --design <pack>` (through the
   `foreman` skill). Tell the user the board's draft epic page shows the pack.
6. Present it with the spec: one line per part on what changes, and any spec fix the pack forced.

Done when every part has diagrams or a skip reason, each "Now" diagram names its source, and the
user has the pack in front of them before approving the spec.
