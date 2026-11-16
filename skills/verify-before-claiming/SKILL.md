---
name: verify-before-claiming
description: Use before saying work is done, fixed, passing, or deployed, and before committing, closing a bead, or trusting a subagent's report; forces fresh empirical evidence against the real artifact.
---

<!-- house: merge; from: own:skills/verify-before-claiming, superpowers:skills/verification-before-completion@bb92a77, pstack:pstack/skills/principle-prove-it-works@850d7f2, pstack:pstack/skills/show-me-your-work@850d7f2 -->

# Verify Before Claiming

Verifier-layer discipline: stop "looks right" or "I changed it" from becoming a completion claim.

## Rule

**No completion claim without fresh evidence from this turn.** Run the narrowest faithful verifier, read its
output, and report it. If verification is impossible, say exactly why and what risk remains, and ask the user on a `foreman ask decision` card to accept that risk. Until the user accepts it, the work is not done.

This covers paraphrases too: "should work now", "looks correct", "Done!", "fixed", moving to the next task,
committing, closing a bead or ticket, and reporting a delegated agent's work.

## Gate

1. **Identify** the command, probe, or observation that would prove the claim.
2. **Run** it in full, fresh. A previous run, a partial run, or "it compiled" does not count.
3. **Read** the whole output: exit code, failure count, warnings.
4. **Compare** to the claim. If it does not confirm it, report the actual state with the evidence.

## Check the real thing, not a proxy

- Exercise the behaviour the user will see: run the feature, read the actual value, inspect the real diff. Not
  file mtimes, cached screenshots, log freshness, or derived state. Check a process is alive by asking the
  process (pid, health endpoint), not by inferring from its output.
- A subagent's "success" is a claim, not evidence. Check the VCS diff and re-run its verifier yourself.
- If a check fails in a way that makes no sense, suspect the observation method before the system.
- Prefer a script that re-runs the comparison over a one-time eyeball, and keep its output where the user can
  re-run it.

## Pick the lowest faithful verifier

Cheapest verifier that actually exercises the claim:

1. Pure logic: unit test or focused script.
2. Integration behaviour: integration test, fixture replay, CLI command, API request, or domain harness.
3. UI behaviour: browser automation, screenshot, DOM assertion, console check, or live-client capture. Look at
   the screenshot critically; anything visibly off is a finding.
4. Unknown client/API behaviour: probe or structured trace read back from saved output.
5. Tooling/hooks: a planted violation must be blocked and a clean action must pass.
6. Docs-only work: link or diff the changed section and check it resolves the stated contradiction or gap.

What each claim needs: `references/claims.md`.

For hard bugs or performance regressions, use `diagnosing-bugs`. For new behaviour with a good test seam, use
`tdd`. A bug fix is verified only when the **original symptom** is gone, and a regression test counts only after
you have seen it fail without the fix.

## Requirements, not just tests

Green tests do not mean the job is done. Re-read the request, spec, or bead; check each requirement line by line;
report gaps instead of rounding them up to "complete".

## Lessons

A user correction runs the `lessons` skill before you move on.

## Report format

Finish with:

- **Changed**: the concrete files or behaviour changed.
- **Verified**: the exact command/test/probe/screenshot/artifact and its result.
- **Not verified**: anything important that could not be checked, with the reason.

Do not bury failed checks. A failed verifier is a blocker unless the user explicitly accepts the residual risk.

For long, multi-phase, or unattended runs that the user will review after stepping away, keep a decision trail
as you go: `references/decision-trail.md`.
