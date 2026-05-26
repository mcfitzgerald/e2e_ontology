# Parity review — Phase 3 · Ambient diff indicators

**Commit under review:** pending Phase 3 commit on `feat/editor-frontend`
**Implementation:**
- Backend: `editor/backend/diff.py`, `editor/backend/git_status.py`, two new endpoints in `main.py`
- Frontend: `store/diff.ts`, `components/PanelDiff.tsx`, `components/BranchBadge.tsx`, `screens/Structure/RemovedSinceHead.tsx`, gutter+underlay rendering inside `SwimlaneGraph.tsx`
**Mockup source:** `editor/design_reference/wireframe.html`
- Branch badge: line 144–153 (CSS), 2575 (JSX)
- Diff gutter on roles: 577–582 (CSS), 1717–1718 (JSX)
- Panel diff banner: 325–335 (CSS), 1268–1277 + 1349–1355 (JSX)
**Reviewer:** awaiting user sign-off

## What shipped

- `GET /api/diff?base=HEAD` — wraps `exploder._resolve_diff_inputs` + `compute_delta`. Returns `{base, base_resolved, head, head_path, kinds: {roles|flows|events|state_machines|entities|enums|warnings: {added, removed, changed: [{name, changes: [{path, before, after}]}]}}, summary: {added, changed, removed}}`. `kinds` only contains entries with non-empty deltas.
- `GET /api/git-status` — `{branch, branch_label, head_short, ahead, behind, dirty, reason}`. Each field degrades independently: detached HEAD reports `branch=null` with `branch_label="detached@<sha>"`; missing upstream reports `ahead=behind=null`; non-git checkout reports `reason="not a git repository"`.
- `store/diff.ts` — Zustand slice with `{diff, gitStatus, loading, error, base, statusIndex, changeIndex, load(base)}`. `statusIndex` and `changeIndex` are per-kind `Map<name, …>` built once per load for O(1) lookups during render.
- App-level wiring: diff loads on mount and on `window.focus`. Polling explicitly avoided.
- **Diff gutter on role nodes** — 3px-wide rect on the left edge, color per `--diff-add | --diff-change` (removed roles aren't on the canvas). Tooltip `<title>` carries the status word for hover discoverability.
- **Diff underlay on flow edges** — 7px semi-transparent stroke beneath the kind-styled edge for added/changed flows. Preserves the kind discriminator (material thick / info dashed / cash doubled) in the foreground.
- **`RemovedSinceHead` banner** — top-of-canvas pill listing every removed element across kinds with a kind-prefix label (`role / flow / event / fsm / entity / enum / warn`). Dashed border in `--diff-remove`. Renders only if anything was removed.
- **`BranchBadge` in app header** — `branch: <name> @<sha> · +N ~M -K` (segments hidden when zero) or `· clean` when no diff. Tooltip exposes the resolved base SHA + dirty flag.
- **`PanelDiff` banner in context panel** — first child above the kind body. `+ added since HEAD` / `~ N fields modified since HEAD` / `− removed since HEAD` headline; for changed elements, an inline list of `body.<path>` rows with del/ins values formatted from the dotted path that `compute_delta` emits. Axioms are not a top-level diff kind so the banner skips when an axiom is selected — its underlying changes still surface inside the parent flow's `axioms.<name>.<field>` rows.

## Intentional deviations from the mockup

- **No handwritten fonts** in any new surface. Mockup used `var(--font-hand)` for the panel-diff caret (line 333); replaced with a JetBrains Mono `+ / ~ / −`. Carries through the AGENTS.md/memory rule that the mockup's Caveat / Shadows Into Light were design-tool flourish, not intent.
- **Edge diff treatment is an extension, not a copy.** The mockup styled diff on roles only — flow edges in the demo data have `diff: "changed"` / `"added"` but no edge-specific CSS variant. We added `.flow-edge-diff-underlay` so changed/added flows are visible at canvas distance without overriding the kind color. If this reads too noisy at conference-room distance, we can dial opacity from 0.45 → 0.25 or thin the stroke.
- **Removed elements as a top banner**, not ghosted into their swimlanes. Mockup punts on this case (it hardcodes diff status into in-canvas elements, all of which exist). Our `/api/ontology` returns only working-copy state, so removed nodes have no layout coordinates. The banner keeps the loss visible without inventing layout for elements the user is on the verge of deleting. Future work could fetch the element from the base ref for read-only inspection — out of scope for Phase 3.
- **Per-status background tint on `.panel-diff`.** Mockup hardcoded `#fff6cf` (amber). We branch to `#e8f1e3` (added) and `#f4e0db` (removed) so the banner color matches the left border. Same vocabulary, just propagated.
- **Branch badge has a clean state.** Mockup never showed it. We render `· clean` in muted ink when the diff summary is all zeros. Keeps the badge from looking broken when nothing has changed.

## Backend behavior worth flagging

- **`git archive HEAD` is cwd-sensitive.** Run from `editor/backend/` it ships only that subdir and the diff fails. `compute_diff_payload` chdirs to `REPO_ROOT` for the duration of the call, then restores. If the user ever runs `exploder diff` from a subdirectory directly they'll hit the same bug — that's a real exploder.py issue but out of scope for editor work.
- **Strict-validate is enforced on both sides of the diff.** `load_ontology` rejects YAML that breaks referential integrity, so the diff endpoint returns 500 for perturbations like deleting an event that flows still trigger on. This matches CLI behavior; no special-casing for the editor.
- **`base_resolved` is best-effort.** If `git rev-parse --short <ref>` fails (timeout, missing git binary, bad ref), it's `null` rather than an error.

## Smoke-test commands (one-shot curls — user starts both servers)

```bash
# Health check
curl -s http://localhost:8787/api/health | jq

# Git status (should report current branch + dirty)
curl -s http://localhost:8787/api/git-status | jq

# Clean diff against HEAD (kinds: {} when working copy matches HEAD)
curl -s "http://localhost:8787/api/diff?base=HEAD" | jq '{base, summary, kinds_present: (.kinds | keys)}'

# Diff against an earlier commit to see meaningful deltas
curl -s "http://localhost:8787/api/diff?base=HEAD~3" | jq '.summary'
```

## Manual perturbation for visual review

The working copy matches HEAD by default, so the canvas shows no diff
indicators on first load. To exercise the visual path:

1. Edit `supply_chain_demo.yaml` — change `supply_planning`'s `description`
   text to add a "(local edit)" marker. Save.
2. Refocus the editor tab; the diff store reloads.
3. Expected:
   - `BranchBadge` shows `~1` in amber.
   - `supply_planning` role card carries an amber gutter on its left edge.
   - Selecting that role surfaces the `panel-diff` banner with `body.description` listed and inline before/after.
4. To exercise added/removed: add a new entity (must not break referential integrity), or delete one that nothing references.
5. Revert the YAML before commit.

## Points to verify during review

### Visual
- [ ] Branch badge legible at a glance; counts color-coded per status
- [ ] Role gutter is the same 3px width as the mockup (-halfW edge)
- [ ] Edge underlay reads as "this flow has diff" without obscuring its kind
- [ ] `RemovedSinceHead` banner doesn't overlap the canvas in a way that hides nodes
- [ ] `PanelDiff` banner renders above the kind panel body, not below
- [ ] Per-status background tints on the panel-diff banner read clearly

### Behavior
- [ ] On mount, both `/api/diff` and `/api/git-status` fire
- [ ] Switching tabs and refocusing reloads diff (test by editing YAML in another window)
- [ ] Type-check passes (`npm run typecheck` or `tsc --noEmit`)
- [ ] Existing tests still pass (`uv run --with linkml --with pyyaml --with pydantic --with pytest python -m pytest tests/`)

### Edge cases
- [ ] Detached HEAD: badge shows `detached@<sha>` instead of branch name
- [ ] Non-git checkout: badge shows `no git`, no diff requested (currently still requested — the diff endpoint will 400; consider gating the call on gitStatus.reason)
- [ ] Working copy clean: badge shows `· clean` in muted ink

## Open questions for sign-off

- Edge underlay opacity (0.45) — too subtle / too loud at projector distance?
- `−K` segment in BranchBadge: shown as `-K` (ASCII hyphen) for character-set safety in mono. The mockup used the same. Keep?
- Should the `BranchBadge` itself be a click target that opens a future "diff explorer" panel (out of scope for Phase 3 — just naming the future affordance)?
