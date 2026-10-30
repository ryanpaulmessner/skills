---
name: tdd
description: "Red-green-refactor in vertical slices at agreed seams, testing behaviour through public interfaces. Use when building a feature or fixing a bug test-first, when the user mentions TDD, red-green, or a regression test, or when implement reaches a ticket."
---

<!-- house: merge; from: mattpocock:skills/engineering/tdd/SKILL.md@49dd158, mattpocock:skills/engineering/tdd/tests.md@49dd158, mattpocock:skills/engineering/tdd/mocking.md@49dd158, superpowers:skills/test-driven-development/SKILL.md@bb92a77, superpowers:skills/test-driven-development/writing-good-tests.md@bb92a77, pstack:pstack/skills/tdd/SKILL.md@850d7f2, pstack:pstack/skills/principle-test-behavior-not-implementation/SKILL.md@850d7f2 (references/test-behavior-not-implementation.md) -->

# TDD

Write the test first, watch it fail for the right reason, write the least code that passes. A test you never saw fail proves nothing.

Read `GLOSSARY.md` and ADRs in the area if they exist, so test names use the domain's words.

## 1. Agree the seams

A **seam** is the public boundary where behaviour is observed without reaching inside. Tests live only at seams.

- Use seams already recorded on the ticket. Otherwise propose them: "public interface X; seams A, B", each with one line on what it catches and what it misses. Confirm with the user before the first test.
- Spend tests on critical paths and complex logic, not every edge case.
- If the interface itself is in question (depth, where the seam goes), consult `codebase-design`.

## 2. Does TDD fit?

Default: yes, for new behaviour and bug fixes. It does not fit when the only test path needs broad harness setup, production-only state, a live client you cannot drive, or mocks of everything. Then say so, and use the closest faithful executable check instead (script, probe, replay, screenshot) via `verify-before-claiming`. **No new test beats a bad test.** Throwaway prototypes, generated code, and config are exempt. Any other skip is the user's call, not yours.

## 3. The loop: one vertical slice at a time

Never write all the tests first (horizontal slicing tests imagined behaviour). Each slice is a tracer bullet: one seam, one test, one minimal change, and the next test responds to what this one taught you.

**RED.** Before writing the body, name the production break this test catches. Can't name one → it is a change detector or tautology; pick a behaviour instead. Write one test for one behaviour, with expected values derived independently (literal, worked example, spec), never recomputed the way the code does. Run it.
- It must fail on its assertion, for the reason you named. A compile/link error, missing symbol, or crash is not RED yet: add the minimal stub (empty function, `{:error, :todo}`, `return 0`) and re-run.
- Stub header-first: declare the signature, write the test, then add the stub body as its own edit of under 10 lines (one constant return per function). pi's write guard rejects 10+ line diffs that look like placeholders; if it still refuses, report the refusal and keep the link error as the RED evidence.
- It passes? You are testing existing behaviour or the test is wrong. Fix the test.

**GREEN.** Write the simplest code that passes. No speculative options, no anticipating the next test. Run the test; then the module's tests. Fails → fix the code, not the test.

**TIDY (optional).** Only while green, only code this slice touched, no new behaviour. Wider restructuring is a finding for `code-review` or a new bead, not part of the loop.

Repeat until the seam's behaviour is covered. Then run the project's full test command once. Failures you did not cause still go in the report by name. Output must be pristine (no warnings or noise).

**Wrote production code before its test?** Stash or revert it, write the test, watch it fail, then restore or rewrite. Keeping it unseen-red is testing after.

## Bug fixes

Reproduce the bug as the smallest failing test at the nearest existing seam first; confirm it fails for the bug's reason, not an unrelated one. Then fix minimally and keep nearby contracts. Hard or unclear bugs: `diagnosing-bugs` first. Flaky bug: make the test deterministic and say what signal it locks down. Never weaken an existing assertion to get green unless the intended behaviour genuinely changed.

## Good tests (details: [references/good-tests.md](references/good-tests.md))

- Behaviour through the public interface; survives a refactor that keeps behaviour.
- Assert the literal result a user sees. A test that would pass if every import returned `undefined` gets rewritten or deleted; weak assertion shapes and fixes: [references/test-behavior-not-implementation.md](references/test-behavior-not-implementation.md).
- Reads like a spec: the name says what, not how. "and" in the name → split it.
- Mock only at system boundaries (network, clock, randomness, hardware, sometimes fs/db), never your own modules. Never assert on the mock itself.
- No test-only methods in production code; put them in test helpers.
- Mutation check before finishing: wrong constant, wrong branch, missing side effect, default return, missing validation. Each realistic mutation should fail some test.

## Red flags

"Too simple to test." "I'll test after." "I already tried it manually." "Keep it as reference." "Just this once." Each means: go back to RED.

## Report

Feed this to `verify-before-claiming`:
- **RED**: command, the failing output, why that failure was expected.
- **GREEN**: command and passing output; full-suite command and result.
- If no failing-first evidence was possible: why, and the executable check used instead.
