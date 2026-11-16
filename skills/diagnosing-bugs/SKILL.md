---
name: diagnosing-bugs
description: Root-cause diagnosis loop for bugs, failing tests, wrong behaviour, and performance regressions. Use when the user says "debug"/"diagnose", or reports something broken, throwing, failing, flaky, slow, or behaving wrong.
---

<!-- house: merge; from: mattpocock:skills/engineering/diagnosing-bugs@49dd158, superpowers:skills/systematic-debugging@bb92a77, pstack:pstack/skills/principle-fix-root-causes@850d7f2 -->

# Diagnosing Bugs

**No fix without a root cause, and no root cause without a loop that goes red on this bug.** Every phase runs.
If a phase cannot run, stop and ask the user on a `foreman ask decision` card.

Read the local AGENTS.md/CLAUDE.md, and any GLOSSARY.md or ADRs for the area, before touching code.

**Redact.** Replace secrets in anything you show with `<REDACTED>`; keep credentials in env vars; quote only the
lines of a captured artifact that carry the signal.

## Phase 0: Classify the report

- **It throws / has a stack trace.** Read the whole message and trace: file, line, error code. That is direct
  evidence; start from it.
- **It behaves wrong (no error).** Wrong behaviour is not an error. Do not go hunting logs for a stack trace that
  is not there. Reason about the behaviour, and **first reproduce it end-to-end, as close to how the user
  experienced it as you can** (same entry point, same UI or CLI path, same data). Only then narrow down.
- **It used to work.** Check what changed first (`git log`/`git diff`, deps, config, env). Inspect or revert that
  change before debugging forward. Bisect if the window is wide.
- **It fails after a restart.** Suspect stale persistent state (config, cache, lock, serialized state) before code.
  If clearing that state restores the behaviour, the fix is validating the state on load.

## Phase 1: Build a feedback loop

This is the skill. With a tight pass/fail signal that goes red on *this* bug, bisection and hypothesis testing
are mechanical. Without one, reading code will not save you. Be aggressive and creative here.

Start from the end-to-end repro and move toward the cheapest loop that still shows the user's exact symptom:
failing test at the right seam, HTTP/CLI script, browser automation, trace replay, throwaway harness, fuzz,
bisect harness, differential run, and last a human-driven script (`scripts/hitl-loop.template.sh`). Details,
tightening, and flaky-bug tactics: `references/feedback-loops.md`.

**Done when** you can name one command you have already run (show it and its redacted output) that is:

- [ ] **Red-capable**: drives the real code path and asserts the user's exact symptom, not "didn't crash".
- [ ] **Deterministic**: same verdict each run (flaky bugs: a pinned, high reproduction rate).
- [ ] **Fast**: seconds, not minutes.
- [ ] **Agent-runnable**: unattended, or human-in-the-loop only via the HITL script.

If you cannot build one, stop and say so: list what you tried, and ask for environment access, a captured
artifact, or permission to add temporary instrumentation. Do not hypothesise without a loop.

## Phase 2: Reproduce and minimise

Run the loop and watch it go red. Confirm it is the failure the **user** described, not a nearby one (wrong bug,
wrong fix), and capture the exact symptom. Then cut inputs, callers, config, and steps one at a time, re-running
after each cut, until every remaining element is load-bearing.

## Phase 3: Hypothesise

- Find a working analogue (similar code, an older version, the reference implementation read in full) and list
  every difference from the broken case, however small.
- Write **3–5 ranked, falsifiable hypotheses**: "If X is the cause, changing Y makes it disappear." A hypothesis
  with no prediction is a vibe; drop or sharpen it.
- Show the ranked list to the user before testing; they often re-rank instantly. Do not block if they are away.
- For errors deep in a call chain, trace the bad value backward to where it originates
  (`references/root-cause-tracing.md`).

## Phase 4: Instrument and test

One probe per prediction; change one variable at a time; never stack fixes. Prefer a debugger or REPL, then
targeted logs at the boundaries that separate hypotheses. Never "log everything and grep". Tag every temporary log
with a unique prefix such as `[DEBUG-a4f2]` so cleanup is one grep. In multi-component systems, log what enters
and leaves each boundary once to find which layer breaks.

Performance: measure a baseline (timer, profiler, query plan) and bisect. Measure first, fix second.

If you say "I don't understand X", say it to the user rather than guessing.

## Phase 5: Fix at the root, with a regression test

- Fix where the bad state originates, not where it surfaces. No guards that silence the symptom (a nil check over
  a crash is a symptom fix). A workaround that needs a paragraph of comment to justify it means the code is wrong.
- Grep for the same pattern and fix every instance, not just the reported one.
- Regression test **before** the fix, only at a seam that exercises the real bug pattern. If no such seam exists,
  that is a finding: report it rather than writing a shallow test that gives false confidence.
- Watch it fail, apply one fix, watch it pass, then re-run the original un-minimised Phase 1 loop.
- **Three failed fixes means stop.** If each fix reveals a new problem elsewhere, the design is wrong, not the
  hypothesis. Discuss the architecture with the user before fix #4.
- If the deciding fact took a deep dig, propose the cheap always-on signal (log line, assertion, metric) that
  would have shown it at first look.

## Phase 6: Clean up and report

- [ ] Original repro no longer reproduces (Phase 1 loop re-run).
- [ ] Regression test passes, or the missing seam is documented.
- [ ] `[DEBUG-` instrumentation removed (grep the prefix); throwaway harnesses deleted.
- [ ] The confirmed hypothesis is stated in the report and any commit message.

Then run `verify-before-claiming` before saying it is fixed. If investigation shows the cause is genuinely
external (environment, timing, third party), document what you checked and add handling plus a signal. Most "no
root cause" verdicts are an incomplete investigation.

## Stop signals

Go back to Phase 1 if you catch yourself thinking "quick fix for now", "just try X", "it's probably X", proposing
fixes before tracing data flow, or if the user says "stop guessing", "is that not happening?", or "we're stuck?".
