---
id: sk-a1b
title: "Try-it step in coordinator close-out"
type: task
status: closed
priority: 2
parent: null
blocked_by: ["sk-f19"]
related: []
supersedes: []
discovered_from: null
labels: []
created: 2026-11-13
closed: 2026-11-13
close_reason: "skills PR merged (25637f8)"
---

Part of foreman epic fm-uo5 (spec ~/dev/foreman/docs/specs/try-it.md, decisions 7, 9, 10, 11). Also blocked by foreman fm-uo5.1, fm-uo5.2 and fm-uo5.3 (cross-repo; not expressible as a file edge).

## What to build
- dispatch close-out: after the commit and before ask push, for a user-facing change: check the worktree is clean at T, start the preview with FOREMAN_SESSION=try-it-<ticket>, run the walkthrough seed, run walkthrough record, post review_ui with --url, --walkthrough, --video, --sha and screenshots, wait. Found a problem -> foreman changes, back to the build, new card on the new sha.
- Brief template: ask the builder for builds/<ticket>/walkthrough.json and to name it in the report.
- foreman skill: review_ui row with the new flags; push row with --no-try-it.
- preview-cleanup.py: removal by try-it-<ticket> owner, and --list-stale (try-it previews whose ticket is closed, abandoned or pushed); orient runs the listing.

## Acceptance
- [ ] Spec check 8: a scratch foreman build is closed out and its window killed; the try-it preview still answers and devserve ls shows owner try-it-<ticket>; after the push, cleanup removes it.
- [ ] preview-cleanup tests cover --list-stale.
