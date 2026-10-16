---
name: analyze-sessions
description: Search and audit Ryan's past agent chats (Claude Code, Pi, Codex). Use for "audit my sessions", "where do I keep correcting agents", "weekly intervention report", or "find what we said about X in past chats".
---

<!-- house: own -->

# Analyze sessions

`scripts/sessions.py` does the extract, filter and count work. Python 3, standard library only. You do the judgment: group causes and propose fixes.

The script reads only human messages:
- Claude Code: `~/.claude/projects/*/*.jsonl`. It skips tool results, injected text, other agents and subagents.
- Pi: `~/.pi/agent/sessions/*/*.jsonl`. Messages that start with `[relay <id>]` come from the Claude planner. They are tagged `source: relay`.
- Claude Code prompt log: `~/.claude/history.jsonl`. This is a fallback for prompts that are not in any transcript, because Claude Code deletes old transcripts. These rows are tagged `source: history`. Pastes show only as `[Pasted text #N +M lines]`.
- Codex: `~/.codex/history.jsonl`. Codex rows have no `cwd`.

`extract` merges into the cache. It never drops rows, so messages from deleted transcripts stay. Use `extract --rebuild` only for an explicit fresh start.

All output is redacted (keys, tokens, passwords). The script writes only to `~/.cache/analyze-sessions/` (folder 700, files 600), or to the file given with `--out`.

## Commands

Run from this skill folder. Every command except `extract` reads `~/.cache/analyze-sessions/messages.jsonl`, so run `extract` first.

```bash
python3 scripts/sessions.py extract [--since YYYY-MM-DD] [--tool claude|pi|codex|all] [--out FILE] [--rebuild]
python3 scripts/sessions.py grep '<regex>' [--tool …] [--since …] [-C N]   # -C: N messages around each hit, same session
python3 scripts/sessions.py stats [--since …] [-n 5]          # per tool/week, long pastes, duplicates (short ones apart), split pastes, prompt-file pointers
python3 scripts/sessions.py interventions [--since …] [-n 5]  # candidate corrections by regex family
```

Families in `interventions`: `correction`, `where_were_we`, `retyped_rule` and `relay_paste`. The first three count only typed messages: 600 characters or fewer, not a paste, and not an agent report. The hits are candidates, not facts. Read them before you count a hit as an intervention. To tune a family, edit `FAMILIES` in the script.

To find what we said about a topic, run `extract`, then `grep '<topic>' -C 2`.

## Weekly intervention report

1. Run `extract --since <7 days ago>`, then `stats` and `interventions -n 20`. Use `grep -C 2` on hits that are not clear.
2. Read the hits. Group them by cause, not by wording. For example, "agent formatted the whole repo" and "drop the churn commit" have one cause.
3. For each cause that occurs 2 or more times, propose one fix. Use the first type in this list that can fix the cause:
   1. a lint rule or hook,
   2. a script,
   3. a prompt template or skill change,
   4. a rule in `AGENTS.md`.
   Give the file that would change.
4. Write the report to `notes/interventions/<YYYY-MM-DD>.md` in the current workspace (ask if it has no `notes/`): counts, causes with 2 or 3 short quotes each, and the proposed fixes. Do not apply any fix.

Do not copy secrets into the report, even if the redaction missed them.
