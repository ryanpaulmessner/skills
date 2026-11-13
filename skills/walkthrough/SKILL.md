---
name: walkthrough
description: Use for walkthrough JSON, replay, recording or live Chrome demos.
---

<!-- house: own -->

# Walkthrough

A walkthrough gives someone who did not build the feature enough context to try it and replay it later. It is not a replacement for the app's tests or `verify ui`.

## Write the file

Write `builds/<ticket>/walkthrough.json` with exactly this shape:

```json
{
  "intro": "Saving a name now confirms whose name was saved. An empty name shows an error instead of saving.",
  "seed": [],
  "steps": [
    {
      "say": "Open the editor",
      "changed": "The editor now has a name field.",
      "do": ["goto /editor"],
      "see": "A name field and Save button.",
      "check": "#name"
    },
    {
      "say": "Save a name",
      "changed": "The confirmation includes the name.",
      "do": ["fill #name Ryan Messner", "click #save", "wait #saved"],
      "see": "Saved Ryan Messner.",
      "check": "#saved"
    },
    {
      "say": "Try an empty name",
      "changed": "Empty names show a validation message.",
      "do": ["fill #name \"\"", "click #save", "wait #error"],
      "see": "Name is required.",
      "check": "#error"
    }
  ]
}
```

- Write a two-to-four-sentence intro for someone who has not read the ticket: what changed and why.
- Use 3–8 steps covering the main path and the most likely failure. `say` names the step in plain words; it also identifies recording failures. `changed` is required but can be empty. `see` describes the observable result.
- Use selectors from DOM ids the code already has. Inspect the actual DOM before writing them; the example's ids are illustrative. `check` must select an element present after the actions. Use `wait` as well when visibility matters.
- `seed` contains one shell command per required starting state, or `[]` when none is needed. The coordinator reviews and runs these from the worktree with the preview's database settings before replay/record. The script never executes shell commands from the file.
- `goto <path>` resolves against `--url` (a leading `/` starts at the origin). Absolute and protocol-relative URLs are rejected. `click <selector>` and `wait <selector>` keep the entire selector. `fill <selector> <text>` uses the first word as selector and the remainder as text; JSON-quote a selector containing spaces, or quote text to fill an empty string. In JSON, escape those inner quotes as in the example.

Finish by running `check`, then `record` against the seeded preview. Hand over the JSON path and video path in the build report; a failing step goes back to the builder, not onto an approval card as passing.

## Check, play and record

Resolve `scripts/walkthrough.cjs` relative to this skill directory. No link or global installation is needed:

```sh
walkthrough() { node /absolute/path/to/skills/walkthrough/scripts/walkthrough.cjs "$@"; }
walkthrough check builds/<ticket>/walkthrough.json
walkthrough play builds/<ticket>/walkthrough.json --url http://127.0.0.1:4000
walkthrough record builds/<ticket>/walkthrough.json --url http://127.0.0.1:4000 --out builds/<ticket>/evidence
```

`check` validates without a browser. `play` opens a separate visible Chromium window with the intro first. Next runs the next step and waits for its check; Back revisits narration without undoing app state. Advancing after Back replays the actions, so use replay-safe preview data. A failed step offers Retry. Close the browser to exit. Collapse shrinks the panel to a `Step N of M` tab; click the tab to expand. Move left / Move right switches edges so preview controls stay reachable. Collapse and edge choices persist across steps, Back/Next and page navigation. The app remains interactive outside the panel.

`record` runs headless at 1440×900, including narration, and prints the saved `.webm` path. Exit 0 means all checks passed; nonzero names the failing step by number and `say`, with its selector. Failure recordings are retained too. Actions/checks time out after 5 seconds, navigation after 15 seconds. Checks mean presence, not visual correctness; inspect the recording and verify UI separately.

Only HTTP bases on `localhost` or `127.0.0.1` are accepted. Both modes use a fresh browser context, not Ryan's Chrome login: include the app's local test sign-in path when needed. Do not put production credentials into walkthrough files. Preview seed/actions may change local data; use the preview database, not production.

Requires Node and an existing Playwright package/browser. Resolution checks the local package, then existing npm exec cache; `WALKTHROUGH_PLAYWRIGHT` can name an installed package directory. Nothing is downloaded automatically. If either dependency is missing, ask for approval before installing a package or browser.

## Live in Ryan's Chrome — only when asked

When Ryan asks in chat or on a card to “walk me through it,” the coordinator uses **Claude in Chrome**, not the separate player:

1. Read this same JSON and open a **new tab** on its preview URL. Give the intro in chat before acting.
2. For one step, explain `say` and the nonempty `changed`, perform `do`, then check the selector and describe `see`. If the result differs, stop and report the mismatch.
3. Wait for Ryan before the next step. He can stop, ask questions or click himself; follow his pace rather than running all steps automatically.
4. End with what was observed, including any failures. A live demonstration does not answer the approval card for him.

If Claude in Chrome is unavailable, offer the player instead of claiming to control his Chrome. Do not start live mode merely because a preview or approval card exists. Card copy: `Ask <session> to walk you through it, or run the player.`

## Verify the scripts

From the skills repo root:

```sh
node --test skills/walkthrough/scripts/test_*.cjs
WALKTHROUGH_BROWSER_TEST=1 node --test skills/walkthrough/scripts/test_*.cjs
python3 scripts/check.py
```

The opt-in tests use installed Chromium, ephemeral localhost servers and temporary files. They check passing and missing-selector recordings, panel collapse/expand, both edges, access to an app control and persistence across navigation. They clean up afterward.
