---
name: flow
description: Map of the house skills and the order they run in. Use at the start of nontrivial work, or when unsure which skill applies.
---

<!-- house: own; router replacing mattpocock:skills/engineering/ask-matt@49dd158, superpowers:skills/using-superpowers@bb92a77, pstack:pstack/skills/poteto-mode@850d7f2 -->

# Flow

Match the work to a line below, then read that skill's SKILL.md before acting on it or describing it to the user: these lines orient, the skill decides. If a line plausibly applies, open the skill. Process skills (spec, debug) run before implementation skills.

Skills marked * are user-invoked. When one is due, name it to the user (`/tight-spec`); once they have asked for that step, read `../<name>/SKILL.md` and follow it.

## New nontrivial work

1. `tight-spec`*: goal, non-goals, acceptance checks. Stop for user approval.
2. `to-tickets`*: approved spec → tracker epic and vertical-slice tickets with blocking edges.
3. Rundown: your understanding in a few lines. Stop for user pushback.
4. `implement`*: work the repo's ticket frontier ticket by ticket. `tdd` at seams, `verify-before-claiming` before any done-claim, `code-review` per ticket.

Too big or too foggy for one session: `wayfinder`* first; when its map clears, enter at step 1.

## By situation

- Broken, failing, flaky, slow, or behaving wrong → `diagnosing-bugs`.
- Module or interface shape, where a seam goes → `codebase-design`. Survey for deepening opportunities → `improve-codebase-architecture`*.
- Domain terms, glossary, ADRs → `domain-modeling`.
- A design or implementation decision → `principles`.
- Stress-test a plan or idea → `grilling`.
- A question only running code can settle (state model, UI) → `prototype`.
- Facts from docs, APIs, primary sources → `research`.
- Raw incoming requests in beads → `triage`*.
- Reporting a perf number → `benchmark-checklist`*.
- No scripted way to drive the app → `create-verification-skill`*; audit it later → `maintain-verification-skill`*.
- User corrected you → `lessons`. Periodic repo-wide sweep → `correct`*. Retrospective on a session's environment → `retro`*.
- Prose for people (docs, PR bodies, commits) → `writing-for-people`. Docs agents read (skills, AGENTS.md) → `writing-for-agents`. An article from scratch: `writing-fragments`* (explore), then `writing-shape`* or `writing-beats`* (exploit).
- Isolated branch → `using-git-worktrees`. Integrating finished work → `finishing-a-development-branch`. PR body → `pr`.
- Comment cleanup before review → `no-comments`*.
- Context hand-off to a new session, harness, or person → `handoff`*.
- Learning a concept over several sessions → `teach`*.
- UI polish and design critique → `emil-design-eng`. Worst-case data in a screen → `break-ui`. Build motion → `animate`; where motion is missing → `find-animation-opportunities`; dropped frames → `animation-performance`; audit or review existing motion → `improve-animations`, `review-animations`*. Name an effect → `animation-vocabulary`. Gesture and spring UI → `apple-design`. Choosing a frontend library → `pick-ui-library`*. Sonner toasts → `ask-sonner`.
- Patterns in past agent sessions, repeated corrections → `analyze-sessions`.

Setup and one-off skills (`setup-pre-commit`, `git-guardrails-claude-code`, `migrate-to-shoehorn`, `scaffold-exercises`, `wizard`) fire on their own descriptions. `wait-what`* is the user's re-pitch request. Upstream back-import for this skill set → `skills-sync`*.

## Operating model

- Coordinator starting or resuming a session → `orient`: fresh, read-only assessment before choosing work.
- A coordinator Claude Code session plans and dispatches build sessions as pi agents in named tmux windows → `dispatch` (coordinator only). Each build session reports where its brief says.
- Detect the tracker per repo: `tickets/` → direct `foreman` ticket commands; otherwise `.beads/` → `bd` until user-approved `foreman adopt`. With neither, ask to onboard. The `foreman` skill separates ticket content from best-effort board events.
- Build-time questions go through `foreman ask decision` and `foreman wait`, not pane prompts. Spec interviews and grilling stay conversational.
- At coordinator close-out, use `foreman` through `dispatch`: `review` before checking, `changes` (`request_changes`) when returning findings, `commit` after an authorized commit, then push/open_pr requests (merge when next) and waits. Telemetry warnings never block work; unresolved approval requests block their dependent steps. Agents never push; pushes go through board requests.
- A repo or workspace skill that runs its own build loop wins over `dispatch` there.
- Claude subagents (Agent tool; pi `subagent`) only when the user asks for them. This overrides any skill that says to dispatch or fan out subagents: run that work sequentially in context instead, or ask first.
