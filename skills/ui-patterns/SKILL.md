---
name: ui-patterns
description: Use when writing interface copy (errors, empty states, CTAs) or designing loading, error or feedback states.
---

<!-- house: merge; from: designer:designer-toolkit/skills/ux-writing@9a6930c, designer:interaction-design/skills/{loading-states,error-handling-ux,feedback-patterns}@9a6930c. Patterns vendored as references/; this index is own. -->

# UI patterns

Pick the matching reference and read it in full before designing or writing:

- `ux-writing`: the words are the deliverable: microcopy, button labels, error messages, empty states.
- `loading-states`: content is not ready yet: spinners, skeletons, optimistic updates, progressive reveal.
- `error-handling-ux`: something can go wrong: prevention, detection, message placement, recovery path.
- `feedback-patterns`: an action needs acknowledging: confirmations, status updates, notifications.

A state design usually touches more than one: an error state needs `error-handling-ux` for the behaviour and `ux-writing` for the message.

Done when every state the screen can enter (empty, loading, partial, error, success) has its copy and behaviour specified, or is named as not applicable.
