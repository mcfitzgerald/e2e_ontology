"""
exploder.py — parses supply-chain ontology LinkML YAML with `instantiates:`
tags and JSON-in-folded-string annotations, produces structured Python
objects, and validates cross-references.

See initial_design_draft.md §6.5 for the design rationale. First-cut scope:
  1. Parse core.yaml + supply_chain_demo.yaml (with imports)
  2. Dispatch on `instantiates:` tags to build Role / Event / Flow /
     StateMachine / Axiom objects
  3. Validate cross-references (source_role, target_role, trigger_event,
     lifecycle_ref, quantum all resolve)

Not in first-cut scope (easy additions later):
  - Resolved JSON view generator
  - Richer shape checks (optional fields, enums of severity levels, etc.)
  - Expression-language evaluation (LinkML's equals_expression handles that)
  - CLI niceties
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ============================================================================
# Object model — the structured view the exploder produces
# ============================================================================


@dataclass
class Entity:
    """A plain structural entity (no `instantiates:`). Slots preserved raw."""

    name: str
    description: str | None = None
    attributes: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class Role:
    name: str
    description: str | None = None
    llm_prompt_hint: str | None = None


@dataclass
class Event:
    name: str
    description: str | None = None
    observed_by: str | None = None  # role name
    llm_prompt_hint: str | None = None


@dataclass
class Transition:
    from_state: str
    to_state: str
    trigger: str | None = None
    guard: str | None = None  # axiom name or None


@dataclass
class StateMachine:
    name: str
    states: list[str] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)
    initial: str | None = None
    terminal: list[str] = field(default_factory=list)


@dataclass
class Axiom:
    name: str
    scope: str  # "class" | "flow"
    nl: str  # natural-language form is always required
    expr: str | None = None
    severity: str = "blocking"  # blocking | warning | advisory
    message: str | None = None
    references: dict[str, list[str]] = field(default_factory=dict)
    on_failure_route_to: str | None = None  # name of a recovery flow


@dataclass
class Flow:
    name: str
    kind: str  # "information" | "material" | "cash"
    source_role: str
    target_role: str
    quantum: str
    trigger_event: str | None = None
    lifecycle_ref: str | None = None  # StateMachine name
    axioms: list[Axiom] = field(default_factory=list)
    llm_prompt_hint: str | None = None


@dataclass
class Ontology:
    entities: dict[str, Entity] = field(default_factory=dict)
    roles: dict[str, Role] = field(default_factory=dict)
    events: dict[str, Event] = field(default_factory=dict)
    state_machines: dict[str, StateMachine] = field(default_factory=dict)
    flows: dict[str, Flow] = field(default_factory=dict)
    enums: dict[str, dict[str, Any]] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"Ontology: {len(self.entities)} entities, "
            f"{len(self.roles)} roles, "
            f"{len(self.events)} events, "
            f"{len(self.state_machines)} state machines, "
            f"{len(self.flows)} flows, "
            f"{len(self.enums)} enums"
        )


class ExploderError(ValueError):
    """Raised when parsing or validation fails."""


# ============================================================================
# Parse — YAML + imports → raw class dicts
# ============================================================================


def _load_raw(path: Path) -> dict[str, Any]:
    """Load a single LinkML YAML file (no import resolution)."""
    with path.open() as fh:
        return yaml.safe_load(fh) or {}


def _resolve_imports(path: Path, loaded: set[Path]) -> dict[str, Any]:
    """Load a schema and recursively merge any local imports.

    Merging strategy: classes from imports are added to the result's `classes`
    dict; later files override earlier ones on name collision (the main file
    wins, which matches LinkML's import semantics closely enough for POC).
    Only local imports are resolved — `linkml:types` and similar external
    imports are ignored here.
    """
    path = path.resolve()
    if path in loaded:
        return {}
    loaded.add(path)

    raw = _load_raw(path)
    merged_classes: dict[str, Any] = {}
    merged_enums: dict[str, Any] = {}

    for imp in raw.get("imports") or []:
        if not isinstance(imp, str) or ":" in imp:
            # Skip URI-form external imports (e.g. linkml:types)
            continue
        imp_path = path.parent / f"{imp}.yaml"
        if not imp_path.exists():
            continue
        sub = _resolve_imports(imp_path, loaded)
        merged_classes.update(sub.get("classes") or {})
        merged_enums.update(sub.get("enums") or {})

    # Main file's own classes override anything from imports
    merged_classes.update(raw.get("classes") or {})
    merged_enums.update(raw.get("enums") or {})

    return {**raw, "classes": merged_classes, "enums": merged_enums}


# ============================================================================
# Annotation body parsing
# ============================================================================


def _parse_json_annotation(value: Any, where: str) -> Any:
    """Annotation bodies are JSON-in-folded-string. Parse them; pass through
    if already structured (YAML parsers may occasionally hand back dicts)."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise ExploderError(f"{where}: failed to parse JSON annotation: {exc}") from exc
    raise ExploderError(f"{where}: unexpected annotation type {type(value).__name__}")


def _get_annotations(class_body: dict[str, Any]) -> dict[str, Any]:
    anns = class_body.get("annotations") or {}
    # LinkML accepts annotations either as a flat tag→value dict or as a list
    # of {tag: ..., value: ...} objects. The POC schemas use the flat form.
    if isinstance(anns, list):
        return {entry["tag"]: entry.get("value") for entry in anns}
    return dict(anns)


# ============================================================================
# Dispatch — build objects from tagged classes
# ============================================================================


_FLOW_KIND_BY_TAG = {
    "scont:InformationFlow": "information",
    "scont:MaterialFlow": "material",
    "scont:CashFlow": "cash",
}


def _build_role(name: str, anns: dict[str, Any]) -> Role:
    body = _parse_json_annotation(anns.get("scont:role"), f"{name}.scont:role") or {}
    return Role(
        name=name,
        description=body.get("description"),
        llm_prompt_hint=body.get("llm_prompt_hint"),
    )


def _build_event(name: str, anns: dict[str, Any]) -> Event:
    body = _parse_json_annotation(anns.get("scont:event"), f"{name}.scont:event") or {}
    return Event(
        name=name,
        description=body.get("description"),
        observed_by=body.get("observed_by"),
        llm_prompt_hint=body.get("llm_prompt_hint"),
    )


def _build_state_machine(name: str, anns: dict[str, Any]) -> StateMachine:
    body = _parse_json_annotation(anns.get("scont:state_machine"), f"{name}.scont:state_machine") or {}
    transitions = [
        Transition(
            from_state=t["from"],
            to_state=t["to"],
            trigger=t.get("trigger"),
            guard=t.get("guard"),
        )
        for t in body.get("transitions") or []
    ]
    return StateMachine(
        name=name,
        states=body.get("states") or [],
        transitions=transitions,
        initial=body.get("initial"),
        terminal=body.get("terminal") or [],
    )


def _build_axioms(owner: str, anns: dict[str, Any]) -> list[Axiom]:
    raw = _parse_json_annotation(anns.get("scont:axioms"), f"{owner}.scont:axioms")
    if not raw:
        return []
    if not isinstance(raw, list):
        raise ExploderError(f"{owner}.scont:axioms: expected a list, got {type(raw).__name__}")
    return [
        Axiom(
            name=a["name"],
            scope=a.get("scope", "class"),
            nl=a["nl"],
            expr=a.get("expr"),
            severity=a.get("severity", "blocking"),
            message=a.get("message"),
            references=a.get("references") or {},
            on_failure_route_to=a.get("on_failure_route_to"),
        )
        for a in raw
    ]


def _build_flow(name: str, kind: str, anns: dict[str, Any]) -> Flow:
    body = _parse_json_annotation(anns.get("scont:flow"), f"{name}.scont:flow") or {}
    required = ("source_role", "target_role", "quantum")
    missing = [k for k in required if not body.get(k)]
    if missing:
        raise ExploderError(f"{name}: flow body missing required fields: {missing}")
    return Flow(
        name=name,
        kind=kind,
        source_role=body["source_role"],
        target_role=body["target_role"],
        quantum=body["quantum"],
        trigger_event=body.get("trigger_event"),
        lifecycle_ref=body.get("lifecycle_ref"),
        axioms=_build_axioms(name, anns),
        llm_prompt_hint=anns.get("scont:llm_prompt_hint"),
    )


def _build_entity(name: str, class_body: dict[str, Any]) -> Entity:
    return Entity(
        name=name,
        description=class_body.get("description"),
        attributes=dict(class_body.get("attributes") or {}),
    )


# ============================================================================
# Main entry point
# ============================================================================


def load_ontology(path: str | Path) -> Ontology:
    """Parse an ontology file (following local imports) into structured objects.

    Only classes declared in the main file get dispatched into the object model.
    Imported files (e.g. core.yaml) provide documentation shells and type
    references but their class definitions are not themselves realized as
    ontology instances — they'd otherwise pollute the entity count.
    """
    path = Path(path)
    main_only = _load_raw(path)
    local_class_names = set((main_only.get("classes") or {}).keys())

    raw = _resolve_imports(path, loaded=set())
    ontology = Ontology(enums=dict(raw.get("enums") or {}))

    for name, body in (raw.get("classes") or {}).items():
        if name not in local_class_names:
            continue  # skip imported meta-class shells
        body = body or {}
        tags = body.get("instantiates") or []

        if not tags:
            ontology.entities[name] = _build_entity(name, body)
            continue

        anns = _get_annotations(body)

        # Dispatch on the first recognized tag. If a class has multiple tags
        # (rare), the first wins; the others can still carry annotations.
        handled = False
        for tag in tags:
            if tag == "scont:Role":
                ontology.roles[name] = _build_role(name, anns)
                handled = True
                break
            if tag == "scont:Event":
                ontology.events[name] = _build_event(name, anns)
                handled = True
                break
            if tag == "scont:StateMachine":
                ontology.state_machines[name] = _build_state_machine(name, anns)
                handled = True
                break
            if tag in _FLOW_KIND_BY_TAG:
                ontology.flows[name] = _build_flow(name, _FLOW_KIND_BY_TAG[tag], anns)
                handled = True
                break
            if tag == "scont:Flow":
                # Abstract — concrete classes shouldn't tag this directly, but
                # if they do we treat it as an unspecified information flow.
                ontology.flows[name] = _build_flow(name, "information", anns)
                handled = True
                break

        if not handled:
            # Unknown tag — treat as a plain entity so we don't lose it, but
            # flag it for visibility.
            ontology.entities[name] = _build_entity(name, body)

    _validate(ontology)
    return ontology


# ============================================================================
# Cross-reference validation
# ============================================================================


def _validate(ontology: Ontology) -> None:
    """Check that flow bodies reference declared roles, events, FSMs, and
    quantum classes. Collect all errors before raising so authors see the
    full picture per run."""
    errors: list[str] = []

    known_classes = set(ontology.entities) | set(ontology.roles) | set(ontology.events) | set(ontology.state_machines) | set(ontology.flows)

    for flow in ontology.flows.values():
        where = f"flow {flow.name!r}"
        if flow.source_role not in ontology.roles:
            errors.append(f"{where}: source_role {flow.source_role!r} is not a declared Role")
        if flow.target_role not in ontology.roles:
            errors.append(f"{where}: target_role {flow.target_role!r} is not a declared Role")
        if flow.quantum not in known_classes:
            errors.append(f"{where}: quantum {flow.quantum!r} is not a declared class")
        if flow.trigger_event and flow.trigger_event not in ontology.events:
            errors.append(f"{where}: trigger_event {flow.trigger_event!r} is not a declared Event")
        if flow.lifecycle_ref and flow.lifecycle_ref not in ontology.state_machines:
            errors.append(f"{where}: lifecycle_ref {flow.lifecycle_ref!r} is not a declared StateMachine")
        for axiom in flow.axioms:
            route = axiom.on_failure_route_to
            if route and route not in ontology.flows:
                errors.append(
                    f"{where}: axiom {axiom.name!r} routes to {route!r}, which is not a declared flow"
                )

    # StateMachine internal consistency
    for sm in ontology.state_machines.values():
        where = f"state_machine {sm.name!r}"
        states = set(sm.states)
        if sm.initial and sm.initial not in states:
            errors.append(f"{where}: initial state {sm.initial!r} not in states")
        for t in sm.transitions:
            if t.from_state not in states:
                errors.append(f"{where}: transition from {t.from_state!r} not in states")
            if t.to_state not in states:
                errors.append(f"{where}: transition to {t.to_state!r} not in states")
        for term in sm.terminal:
            if term not in states:
                errors.append(f"{where}: terminal state {term!r} not in states")

    if errors:
        joined = "\n  - ".join(errors)
        raise ExploderError(f"Ontology validation failed with {len(errors)} error(s):\n  - {joined}")


# ============================================================================
# CLI — load and summarize
# ============================================================================


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("usage: python exploder.py <path-to-yaml>")
        sys.exit(1)

    ontology = load_ontology(sys.argv[1])
    print(ontology.summary())
    print()
    print("Roles:")
    for r in ontology.roles.values():
        print(f"  - {r.name}: {r.description}")
    print()
    print("Events:")
    for e in ontology.events.values():
        print(f"  - {e.name}: observed_by={e.observed_by}")
    print()
    print("State machines:")
    for sm in ontology.state_machines.values():
        print(f"  - {sm.name}: {len(sm.states)} states, {len(sm.transitions)} transitions")
    print()
    print("Flows:")
    for f in ontology.flows.values():
        axioms = f", {len(f.axioms)} axiom(s)" if f.axioms else ""
        print(f"  - {f.name} [{f.kind}]: {f.source_role} → {f.target_role}, quantum={f.quantum}{axioms}")
