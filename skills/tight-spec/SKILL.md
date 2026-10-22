---
name: tight-spec
description: "Interview the user into a bounded, measurable spec before building, then hand it to to-tickets. Use for /tight-spec, 'spec this out', vague or drifting-scope requests, cross-module changes, or refactors."
disable-model-invocation: true
---

<!-- house: merge; from: own:skills/tight-spec@pre-merge, mattpocock:skills/engineering/to-spec@49dd158, mattpocock:skills/productivity/grilling@49dd158, mattpocock:skills/engineering/grill-with-docs@49dd158, superpowers:skills/brainstorming@bb92a77, pstack:pstack/skills/sharpen@850d7f2, pstack:pstack/skills/figure-it-out@850d7f2; not taken (catalog drops): pstack interrogate, pstack how, mattpocock grill-me; house edit 2026-10-16: state table in Decisions -->

# Tight Spec

Use before implementing work whose scope can drift: cross-module changes, vague feature requests,
refactors, "while we are here" work. Its job is to stop over-reading scope and make completion measurable
before code starts. Output: a spec the user approves, handed to `to-tickets`.

<HARD-GATE>
Nothing gets built until the user approves the spec. Building includes product code, scaffolding,
installing dependencies, and creating tickets. Reading, exploring, and throwaway spikes the user agreed to
are fine; keeping a spike is a new request that comes back through this gate.
</HARD-GATE>

## 1. Ground yourself

- Read the local `AGENTS.md`/`CLAUDE.md`, plus `GLOSSARY.md` and ADRs in the area if they exist. Use the
  project's vocabulary in every question and in the spec; respect existing ADRs.
- If the request already holds everything that matters ("make the icon cornflower blue"), skip this skill:
  do it and say what you did.
- If the conversation already settled the decisions, size it (step 2), send the project draft's start-spec event (step 3), then synthesize (step 4); confirm only what is genuinely open.

## 2. Restate and size

Restate the concrete objective in one paragraph, including why the user wants it. Then size it in plain
words (the user can override):

- **Small change** — spec stays in chat; no tickets unless the user asks.
- **Project** — full spec, then `to-tickets`.
- **Several independent projects** — say so, agree an order, spec one at a time.
- **Too big for one session and the route is unclear** — stop and suggest `wayfinder` instead.

If it grows mid-interview, stop, say so, and step up a size.

For a project only, use the `foreman` skill to create/reuse a draft epic (slug, configured project, spec path); keep that identity for the handoff, even if the board is unavailable.

## 3. Interview

Use the `foreman` skill to send `epic spec` (`start_spec`) for the project draft as the interview starts; if skipping the interview, send it before synthesizing step 4.

**Facts are your job; decisions are the user's.** Never ask the user something you can look up (code,
config, docs, tool output). Explore yourself, or dispatch a read-only subagent for wide searches; ask
the questions that don't depend on the answer while it runs.

**One question at a time.** Each question gets a short title, the context needed to answer it, and your
recommended answer, worded so "yes" accepts it:

```
**Q: <title>** — <question; options only if the user is stuck or the fork is real>
Recommended: <your answer, one line on why>
```

Ask in dependency order: settle the decisions others hang on first. Prefer anchored questions ("walk me
through the last time this bit you", "if it could only do one of these well, which?") over abstract
ones. A guess they can correct often beats a question.

**Hunt the scope traps.** Press on each that applies:

- adjacent features that sound related but are not required
- cleanup/refactors the objective doesn't need
- hidden dependencies on live services, user state, or environment
- narrow remediation vs. broad redesign — which did they mean?
- constraints that don't serve the goal (loosen them as readily as you add ones that do)

**Design alternatives.** Where the approach has a real fork, think of several options privately, drop the
weak ones (including any that fight the stated why), and present 2–3 with tradeoffs and your pick. Don't
manufacture forks where the path is obvious.

**Play back as you go.** When one part is clear, describe it back in a few lines, marking your guesses and
defaults as yours — a default the user never heard is one they couldn't reject. Ask what's wrong or
missing.

When a term gets sharpened or a hard-to-reverse decision is made, offer to record it with the
`domain-modeling` skill (glossary/ADR) if the repo keeps them.

Stop interviewing once the next implementation step is clear and bounded. Better, not bigger.

## 4. Write the spec

```markdown
## Goal
<one sentence: the behavior or artifact that changes>

## Why
<the user's motivation, in their terms; what success looks like to them>

## Non-goals
<explicit boundaries, incl. anti-goals: what would make this a failure even if it technically works>

## Decisions
<numbered; each marked (user) or (agent call). Modules and interfaces touched, contracts, schema.
Nontrivial state mechanics: include the state table (states, events, transitions) per the principles
skill's `state-machine-skeleton`.
No file paths or code — they go stale. Exception: a prototype snippet that pins a decision better than
prose (state machine, schema, type shape), trimmed and labeled as from a prototype.>

## Acceptance checks
<observable, falsifiable evidence the work is done. Name the baseline to compare against where one
exists ("old value vs new value"). At least one check from outside the code under change.>

## Verification plan
<tests, commands, screenshots, probes, traces. Name the test seams: prefer existing seams, then the
highest one possible; fewest seams wins. Confirm the seams with the user.>

## Ask-first boundaries
<actions that exceed the spec and require another checkpoint>

## Left to the builder
<choices deliberately not decided here>
```

For a project-size spec, save the spec at the draft's spec path and run the builder check in `references/builder-check.md` before handing it over.
Then run the `design-pack` skill: data, state and flow diagrams beside the spec, drawn from the code. It
is required for a project spec; a part may be skipped only with a stated reason. Fold any gap the pack
exposes back into the spec.

## 5. Gate and hand off

Before asking for approval, you must be able to answer:

- What exact behavior or artifact will change?
- What is intentionally not changing?
- What evidence will prove the change worked?
- What action would exceed the spec and require asking first?

Present the spec with a short list of the calls you made, and for a project the design pack (one line per
part on what changes; the board's draft epic page draws it). "Sounds good" to an idea is not approval of a
spec you haven't shown. Once approved: for a project, ask the user to run `/to-tickets <spec>` (it is user-invoked, so the
Skill tool cannot start it); for a small change, proceed through the normal workflow.

On project-spec approval, use the `foreman` skill to send `epic approve` (`approve_spec`) with the saved spec path and `--design <pack path>`; pass the draft slug, project, spec and pack paths to `to-tickets`.
