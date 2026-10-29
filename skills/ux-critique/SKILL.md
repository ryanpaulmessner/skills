---
name: ux-critique
description: Use when critiquing a rendered screen or UI change, or running a heuristic evaluation.
---

<!-- house: merge; from: designer:visual-critique/skills/critique-*@9a6930c, designer:prototyping-testing/skills/heuristic-evaluation@9a6930c. Lenses vendored as references/; this index is own. -->

# UX critique

Critique what is actually rendered: a screenshot, a live page, or a picked frame. Never critique from source code alone; if nothing rendered is in hand, get a screenshot first.

1. **Pick lenses.** Match the question to the lines below; a general "how does this look" review runs every visual lens. Read each chosen `references/<lens>.md` in full before applying it.
   - `critique-visual-hierarchy`: where the eye lands first, eye flow, emphasis.
   - `critique-composition`: balance, whitespace, rhythm, gestalt grouping.
   - `critique-typography`: scale use, readability, consistency, token compliance.
   - `critique-color`: contrast ratios, palette coherence, semantic colour.
   - `critique-information-density`: cognitive load, prioritisation, scanning, progressive disclosure.
   - `critique-affordance`: what looks clickable, state visibility, CTA clarity.
   - `critique-brand-consistency`: only when the project has `mood.md`, `voice.md` or `tokens.md`; otherwise skip it and say so.
   - `heuristic-evaluation`: usability of a flow or product against Nielsen's heuristics, with severity ratings.
2. **Report findings.** Each finding names the element, the lens, what is wrong, a severity, and the concrete fix (value, token, or layout change). Order by severity.

Done when every chosen lens has findings or an explicit "no issues", and each finding has a fix specific enough to implement. When a fix rests on a perceptual law (proximity, Fitts, Hick), cite it from the `ux-laws` skill.
