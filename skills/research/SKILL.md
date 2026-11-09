---
name: research
description: Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.
---

<!-- house: adapt; from: mattpocock:skills/engineering/research@49dd158 -->

Spin up a **background agent** to do the research, so you keep working while it reads.

Its job:

1. Investigate the question against **primary sources** (official docs, source code, specs, first-party APIs), not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Write the findings to a single Markdown file, citing each claim's source.
3. Save ticket findings to `$(foreman doc path report <id> --next)`, or unticketed findings to `$(foreman doc path note research <slug>)`; see the `foreman` skill's Documents section. Give the agent the resolved absolute path.
