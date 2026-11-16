---
name: lessons
description: "Use when the user corrects you, says something you did or claimed was wrong, or repeats an instruction you missed; turns the correction into a proposed check and a lesson ticket."
---

<!-- house: own; moved from the Lessons section of verify-before-claiming (2026-10-16); rewritten on foreman, check first (2026-11-16) -->

# Lessons

Every user correction is a lesson. Fix what the user pointed at first, then do these steps before your next task. If the user changed their mind rather than caught a mistake, it is not a lesson: save the new preference with `foreman answer` so it does not come back as a correction.

1. **Name it** in one line: what you did, what the user wanted, and what made the wrong move look right.
2. **Check for a repeat.** Search all of these for the key word:
   - lesson tickets: `grep -l '"lesson"' tickets/*.md`, then `foreman show <id>`
   - the hooks: `grep -n '<key word>' ~/.claude/hooks/*.sh`
   - prose: the repo `AGENTS.md`/`CLAUDE.md`, the skill that applied, and `~/.claude/projects/*/memory/feedback-*.md`

   A prose rule that existed and did not stop you is a repeat: prose is not enough here, so the output must be a check.
3. **Propose a check.** This is the default output. Take the first kind that can catch the mistake:
   1. **Hook**: a rule in `~/.claude/hooks/` (Bash PreToolUse; pi gets it through house-guard). Add it to `block-workflow-mistakes.sh`, or to `block-sensitive-commit.sh` for commit content. Its refusal names the right next step. Add the planted command and a normal command to `test-hooks.sh`.
   2. **Ryan-only Credo check** in `~/dev/work/tools/verify/credo/` (runs in `verify base`), for a code pattern in ReportSystem.
   3. **`foreman check`, or a relay or verify refusal**, for a ticket, card, report or review that has the wrong shape.
   4. **ReportSystem test** that fails when the behavior breaks.
   5. **Better API**: change the code, CLI or data so the mistake cannot be written.

   Write the proposal as:
   ```
   check: <kind>, <file it lives in>
   blocks: <the planted mistake, as the exact command, code or text from this incident>
   passes: <one normal input that must still pass>
   ```
   Prose (a memory, a `CLAUDE.md` line or a skill line) is allowed only with the line `check rejected: <why none of the five kinds can catch it>`. "Too much work" is not a reason: then file the check as a ticket and write no prose.
4. **Size the rule to the incident.** A correction from one incident gets a rule only as wide as that incident: the same command, the same file pattern, the same repo. Do not widen it to "all X" from one case. When a second incident shows a wider class, widen the check then.
5. **Rewrite, do not append.** If the new rule contradicts an existing rule (in a hook, a skill, `CLAUDE.md` or a memory), rewrite the old rule to the current state. Do not add a dated note below it. When the check exists, the old prose becomes one pointer line ("Enforced by <file>") or is deleted.
6. **Act.** Build the check now if it is in the current task's scope and in files you own. Show it fail on the planted mistake and pass on the normal input. Otherwise file it.
7. **Record** a lesson ticket in the repo the check lands in:
   `foreman new "<mistake> -> <check>" --type chore --labels lesson --body "<the proposal block from step 3, plus the build state: built in <file> | filed>"`, then `foreman check`.

Done when the lesson ticket exists and you have told the user, in one line, the check (or `check rejected: <reason>`) and the ticket id. Asking Ryan to approve a check, or to accept prose in place of one, goes on a `foreman ask decision` card.

For a repo-wide sweep of repeated mistakes, the user runs `correct`.
