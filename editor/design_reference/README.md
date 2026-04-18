# Design reference — NOT the implementation

> **This directory is reference-only. It is NOT the implementation.**
>
> `wireframe.html` is a Claude Design mockup — the visual/UX spec for the real editor under `editor/frontend/`. It exists to anchor visual fidelity. Open it side-by-side with the real implementation when building or reviewing editor screens. Do not edit it; do not import from it at runtime.

## Contents

| File | Origin | Purpose |
|---|---|---|
| `wireframe.html` | Claude Design export (`/tmp/claude_design/test1/project/Ontology Editor Wireframes.html`) | Self-contained React + Babel-standalone mockup of the 4 editor screens. Source of all design tokens and layout rules. |
| `chat_transcript.md` | Claude Design session (`chats/chat1.md`) | Back-and-forth that produced the mockup — captures the user's intent and where they landed after iterating. |
| `mockup_readme.md` | Claude Design bundle README | Anthropic's own handoff note for coding agents. Read its "About the design files" section — it explains the recreate-pixel-perfectly-but-don't-copy-structure rule. |

## How to use this directory

- **When implementing a screen**: open `wireframe.html` in a browser, navigate to the target screen (it uses localStorage so your selection persists). Keep it in a second window next to your editor.
- **When extracting tokens**: read the source directly. Every color, font, spacing value, and SVG filter is explicit text. Match tokens into `editor/frontend/src/tokens/` — do not reinvent.
- **When running a visual parity review**: render `wireframe.html` and the real editor in adjacent browser windows, write a memo to `editor/parity_reviews/<screen>.md` listing intentional vs unintentional visual diffs, and request user sign-off.

## What NOT to do

- Do not edit `wireframe.html` to match the real implementation. If the mockup is wrong, update it in Claude Design and re-export.
- Do not copy the mockup's internal structure into the real implementation: no React-via-Babel runtime, no inline `window.ONTOLOGY`, no hand-positioned role coordinates, no hardcoded `diff`/branch values. Those were mockup conveniences, not the contract.
- Do not import anything from this directory at runtime. The real editor lives under `editor/frontend/`.
