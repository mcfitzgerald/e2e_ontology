# Supply Chain Ontology POC

A supply chain ontology that sits in an agent orchestration layer, providing the structural and process context agents need to navigate the domain. The ontology describes concepts, roles, events, flows, and invariants; the orchestrator binds them to actual tools and runtimes.

## State of the project

Early POC. The de-risking spike has passed — LLM reasoning over the extension pattern works cleanly on the minimal demo slice. Foundation is in place and validated; ontology is being expanded toward a full demo narrative.

**Read `initial_design_draft.md` first.** It is the authoritative design document and captures everything the current state depends on, including the spike results and forward-looking work.

## Files

| File | Purpose |
|---|---|
| `initial_design_draft.md` | Authoritative design document. Start here. |
| `core.yaml` | LinkML meta-class documentation shells (Role, Event, Flow, StateMachine). Imported by the demo. |
| `supply_chain_demo.yaml` | Concrete demo ontology exercising demand→procurement, disruption→replan, and the downstream procurement→supplier transmission. |
| `exploder.py` | Parser, object model, and cross-reference validator for the ontology. |
| `ontology_primer.md` | LLM context bootstrap — prepend to prompts that consume the ontology. |
| `CHANGELOG.md` | Session-by-session log of changes. |
| `.gitignore` | Python, IDE, OS, and `.claude/` ignores. |
| `reference/pcg.yaml` | Prior virtual-twin ontology — reference only, not POC content. |

## Quick start

### Run the exploder

```bash
uv run --with pyyaml python exploder.py supply_chain_demo.yaml
```

Prints a structured summary of the ontology's entities, roles, events, state machines, flows, and axioms. Fails with detailed errors if any cross-references are broken.

### Test LLM reasoning over the ontology

Concatenate and feed to your LLM:

1. `ontology_primer.md` — reader's guide, sets up navigation conventions
2. `core.yaml` — meta-class definitions
3. `supply_chain_demo.yaml` — the content under test

Ask questions about handoffs, axioms, and recovery routing. See `initial_design_draft.md` §10 for the three questions used in the de-risking spike and §11 for the results.

## Key design decisions at a glance

- **LinkML as the host format**, extended via `instantiates:` tags as lightweight type discriminators (not LinkML 1.6's enforced metaclass extension mechanism).
- **Class-centric structure.** Everything is a LinkML class. Plain entities have no `instantiates:`; meta-typed constructs (Role / Event / Flow / StateMachine) carry the tag and put structured semantics in `annotations:` as JSON-in-folded-string values.
- **Two-tier axiom strategy.** Tier 1: native LinkML `rules:` for simple class-level invariants. Tier 2: annotation-carried axioms with `expr:` (LinkML `equals_expression` syntax) and `nl:` (natural language) forms, attached to the flow or class they govern.
- **`llm_prompt_hint` as a load-bearing convention.** Every meta-typed element carries a per-element hint designed specifically to guide LLM navigation of that element. Adopted from `pcg.yaml` where it is proven to matter.
- **Class-centric everything.** No top-level `flows:` / `events:` / `axioms:` blocks. Composition is via LinkML's native `imports:` and `is_a` mechanisms.
- **Metrics shaped for dbt semantic layer compatibility** (MetricFlow vocabulary) without current dependency. The ontology is authoritative for metrics now; promotion to dbt is the forward path when dbt scales.

## Starting a fresh session

If you're picking this up in a new session:

1. Read `initial_design_draft.md` — especially §11 (spike results), §12 (context management), and §13 (forward-looking work) for the current state.
2. Skim `CHANGELOG.md` for session-by-session deltas.
3. Run `python exploder.py supply_chain_demo.yaml` to confirm the tooling still works in your environment.
4. If you want to verify the LLM-reasoning pattern still holds, re-run the three spike questions from §10 against the current demo file.

## Next steps (from `initial_design_draft.md` §13)

1. Expand the demo ontology further (direction 2 — in progress).
2. Harden the exploder: resolved JSON view output, richer shape validation, a test suite (direction 3).
3. Design the orchestrator-side read API (direction 4).
4. Script the full demo narrative (direction 5).
5. Meta: proposal protocol for agent-authored ontology diffs (previously tabled in §8; revisit after directions 2–4).
