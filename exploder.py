"""
exploder.py — the ontology control plane.

Parses supply-chain ontology LinkML YAML with `instantiates:` tags and
JSON-in-folded-string annotations; validates bodies against Pydantic models
auto-generated from scont_meta.yaml (see scont_bodies.py); resolves
cross-references; surfaces warnings; answers queries; wraps linkml-lint and
gen-doc. Designed so agent authoring, inspection, and future tooling sit on a
deterministic foundation.

Architecture:
  1. `SchemaView` (from linkml_runtime) provides LinkML-level access.
  2. Annotation bodies parsed as JSON, validated against `scont_bodies.py`
     Pydantic models (auto-generated from scont_meta.yaml).
  3. Cross-reference resolution and warnings layer on top.
  4. Query API over the resolved model.
  5. CLI subcommands: validate, inspect, query, summary, doc, regen-bodies.

See initial_design_draft.md §6.5 and the plan file for design rationale.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml
from linkml_runtime.utils.schemaview import SchemaView
import pydantic

from scont_bodies import (
    RoleBody,
    EventBody,
    FlowBody,
    AxiomBody,
    StateMachineBody,
    TransitionBody,
    MetricBody,
)


# ============================================================================
# Tags
# ============================================================================

TAG_ROLE = "scont:Role"
TAG_EVENT = "scont:Event"
TAG_STATE_MACHINE = "scont:StateMachine"
TAG_FLOW = "scont:Flow"
_FLOW_KIND_BY_TAG = {
    "scont:InformationFlow": "information",
    "scont:MaterialFlow": "material",
    "scont:CashFlow": "cash",
}

ANN_ROLE = "scont:role"
ANN_EVENT = "scont:event"
ANN_STATE_MACHINE = "scont:state_machine"
ANN_FLOW = "scont:flow"
ANN_AXIOMS = "scont:axioms"
ANN_METRICS = "scont:metrics"
ANN_LLM_PROMPT_HINT = "scont:llm_prompt_hint"
ANN_DOMAIN = "scont:domain"
ANN_SUBDOMAIN = "scont:subdomain"


# ============================================================================
# Resolved object model — Pydantic bodies wrapped with their class names
# ============================================================================


@dataclass(frozen=True)
class ResolvedRole:
    name: str
    body: RoleBody
    domain: str | None = None
    subdomain: str | None = None


@dataclass(frozen=True)
class ResolvedEvent:
    name: str
    body: EventBody
    domain: str | None = None
    subdomain: str | None = None


@dataclass(frozen=True)
class ResolvedStateMachine:
    name: str
    body: StateMachineBody
    domain: str | None = None
    subdomain: str | None = None


@dataclass(frozen=True)
class ResolvedFlow:
    name: str
    kind: str  # information | material | cash
    body: FlowBody
    axioms: tuple[AxiomBody, ...]
    llm_prompt_hint: str | None
    domain: str | None = None
    subdomain: str | None = None


@dataclass(frozen=True)
class ResolvedEntity:
    name: str
    description: str | None
    attributes: dict[str, dict[str, Any]]
    rules: tuple[dict[str, Any], ...]
    metrics: tuple[MetricBody, ...]
    other_annotations: dict[str, Any]  # raw non-scont annotations + unused scont ones
    domain: str | None = None
    subdomain: str | None = None


# ============================================================================
# Error / warning model
# ============================================================================


@dataclass(frozen=True)
class ValidationIssue:
    level: str  # "error" | "warning"
    element: str
    field: str | None
    message: str

    def format(self) -> str:
        prefix = self.element
        if self.field:
            prefix += f".{self.field}"
        return f"[{self.level.upper()}] {prefix}: {self.message}"


class OntologyError(ValueError):
    """Raised when validation fails. Carries the full issue list."""

    def __init__(self, issues: list[ValidationIssue]):
        self.issues = issues
        super().__init__(self._format_summary())

    def _format_summary(self) -> str:
        errs = [i for i in self.issues if i.level == "error"]
        joined = "\n  - ".join(i.format() for i in errs)
        return f"Ontology validation failed with {len(errs)} error(s):\n  - {joined}"


# ============================================================================
# Ontology — the top-level object with the query API
# ============================================================================


@dataclass
class Ontology:
    path: Path
    schema_view: SchemaView  # underlying LinkML introspection layer
    entities: dict[str, ResolvedEntity] = field(default_factory=dict)
    roles: dict[str, ResolvedRole] = field(default_factory=dict)
    events: dict[str, ResolvedEvent] = field(default_factory=dict)
    state_machines: dict[str, ResolvedStateMachine] = field(default_factory=dict)
    flows: dict[str, ResolvedFlow] = field(default_factory=dict)
    enums: dict[str, dict[str, Any]] = field(default_factory=dict)
    warnings: list[ValidationIssue] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> str:
        return (
            f"Ontology: {len(self.entities)} entities, "
            f"{len(self.roles)} roles, "
            f"{len(self.events)} events, "
            f"{len(self.state_machines)} state machines, "
            f"{len(self.flows)} flows, "
            f"{len(self.enums)} enums"
        )

    def summary_dict(self) -> dict[str, Any]:
        """Machine-readable summary. Use with --json."""
        return {
            "path": str(self.path),
            "entities": {k: self._entity_summary(v) for k, v in self.entities.items()},
            "roles": {k: self._role_summary(v) for k, v in self.roles.items()},
            "events": {k: v.body.description for k, v in self.events.items()},
            "state_machines": {
                k: {"states": v.body.states, "transitions": len(v.body.transitions)}
                for k, v in self.state_machines.items()
            },
            "flows": {k: self._flow_summary(v) for k, v in self.flows.items()},
            "enums": list(self.enums.keys()),
            "warnings": [w.format() for w in self.warnings],
        }

    @staticmethod
    def _entity_summary(e: ResolvedEntity) -> dict[str, Any]:
        return {
            "description": e.description,
            "attributes": list(e.attributes.keys()),
            "rules": len(e.rules),
            "metrics": [m.name for m in e.metrics],
            "domain": e.domain,
        }

    @staticmethod
    def _role_summary(r: ResolvedRole) -> dict[str, Any]:
        return {
            "description": r.body.description,
            "is_boundary": bool(r.body.is_boundary),
            "human_involvement": r.body.human_involvement,
            "domain": r.domain,
        }

    @staticmethod
    def _flow_summary(f: ResolvedFlow) -> dict[str, Any]:
        return {
            "kind": f.kind,
            "source_role": f.body.source_role,
            "target_role": f.body.target_role,
            "quantum": f.body.quantum,
            "returns": f.body.returns,
            "trigger_event": f.body.trigger_event,
            "lifecycle_ref": f.body.lifecycle_ref,
            "axioms": [a.name for a in f.axioms],
            "domain": f.domain,
        }

    # ------------------------------------------------------------------
    # Query API — scont-level (LinkML-level queries go via self.schema_view)
    # ------------------------------------------------------------------

    def get_flow(self, name: str) -> ResolvedFlow | None:
        return self.flows.get(name)

    def get_role(self, name: str) -> ResolvedRole | None:
        return self.roles.get(name)

    def get_event(self, name: str) -> ResolvedEvent | None:
        return self.events.get(name)

    def get_entity(self, name: str) -> ResolvedEntity | None:
        return self.entities.get(name)

    def get_state_machine(self, name: str) -> ResolvedStateMachine | None:
        return self.state_machines.get(name)

    def list_flows_where(
        self,
        source_role: str | None = None,
        target_role: str | None = None,
        quantum: str | None = None,
        trigger_event: str | None = None,
        kind: str | None = None,
    ) -> list[ResolvedFlow]:
        """Filter flows by any combination of attributes. None means any."""
        out = []
        for f in self.flows.values():
            if source_role and f.body.source_role != source_role:
                continue
            if target_role and f.body.target_role != target_role:
                continue
            if quantum and f.body.quantum != quantum:
                continue
            if trigger_event and f.body.trigger_event != trigger_event:
                continue
            if kind and f.kind != kind:
                continue
            out.append(f)
        return out

    def list_query_flows(self) -> list[ResolvedFlow]:
        """Flows with `returns:` set — request-response query flows."""
        return [f for f in self.flows.values() if f.body.returns]

    def list_handoff_flows(self) -> list[ResolvedFlow]:
        """Flows without `returns:` — responsibility-transferring handoffs."""
        return [f for f in self.flows.values() if not f.body.returns]

    def list_boundary_roles(self) -> list[ResolvedRole]:
        return [r for r in self.roles.values() if r.body.is_boundary]

    def find_flows_triggered_by(self, event_name: str) -> list[ResolvedFlow]:
        return [f for f in self.flows.values() if f.body.trigger_event == event_name]

    def find_roles_by_domain(self, domain: str) -> list[ResolvedRole]:
        return [r for r in self.roles.values() if r.domain == domain]

    def get_axioms_for(self, name: str) -> list[AxiomBody]:
        """Axioms attached to a flow (by flow name). Class-level axioms via rules stay
        in the Entity.rules list and are not surfaced here."""
        flow = self.flows.get(name)
        return list(flow.axioms) if flow else []

    def traverse_fsm(self, name: str, from_state: str) -> list[TransitionBody]:
        sm = self.state_machines.get(name)
        if not sm:
            return []
        return [t for t in sm.body.transitions if t.from_state == from_state]


# ============================================================================
# Parsing helpers
# ============================================================================


def _load_raw(path: Path) -> dict[str, Any]:
    with path.open() as fh:
        return yaml.safe_load(fh) or {}


def _parse_json_annotation(value: Any, where: str) -> Any:
    """Annotation bodies are JSON-in-folded-string. Parse if string, passthrough
    if already structured (rare but LinkML tolerates both forms)."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise OntologyError(
                [ValidationIssue("error", where, None, f"failed to parse JSON annotation: {exc}")]
            ) from exc
    raise OntologyError(
        [ValidationIssue("error", where, None, f"unexpected annotation type {type(value).__name__}")]
    )


def _normalize_transitions(body_dict: dict[str, Any]) -> dict[str, Any]:
    """Translate wire-format `from`/`to` keys in transitions to
    `from_state`/`to_state` expected by the Pydantic model.

    Existing YAML uses `from`/`to` (LinkML's `aliases:` is metadata-only and
    doesn't emit Pydantic field aliases). This shim preserves backward
    compatibility until Phase B migrates the YAML. Accepts either form."""
    transitions = body_dict.get("transitions")
    if not isinstance(transitions, list):
        return body_dict
    for t in transitions:
        if not isinstance(t, dict):
            continue
        if "from" in t and "from_state" not in t:
            t["from_state"] = t.pop("from")
        if "to" in t and "to_state" not in t:
            t["to_state"] = t.pop("to")
    return body_dict


def _get_annotations(class_body: dict[str, Any]) -> dict[str, Any]:
    anns = class_body.get("annotations") or {}
    if isinstance(anns, list):
        return {entry["tag"]: entry.get("value") for entry in anns}
    return dict(anns)


def _collect_validation_errors(
    exc: pydantic.ValidationError, element: str, annotation: str
) -> list[ValidationIssue]:
    """Map Pydantic errors to our ValidationIssue form."""
    issues = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"])
        msg = f"{err['msg']} ({err['type']})"
        field_path = f"{annotation}.{loc}" if loc else annotation
        issues.append(ValidationIssue("error", element, field_path, msg))
    return issues


# ============================================================================
# Builders — class body → ResolvedX
# ============================================================================


def _build_role(name: str, anns: dict[str, Any], issues: list[ValidationIssue]) -> ResolvedRole | None:
    raw = _parse_json_annotation(anns.get(ANN_ROLE), f"{name}.{ANN_ROLE}")
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        issues.append(ValidationIssue("error", name, ANN_ROLE, f"expected object, got {type(raw).__name__}"))
        return None
    try:
        body = RoleBody.model_validate(raw)
    except pydantic.ValidationError as exc:
        issues.extend(_collect_validation_errors(exc, name, ANN_ROLE))
        return None
    return ResolvedRole(
        name=name,
        body=body,
        domain=anns.get(ANN_DOMAIN),
        subdomain=anns.get(ANN_SUBDOMAIN),
    )


def _build_event(name: str, anns: dict[str, Any], issues: list[ValidationIssue]) -> ResolvedEvent | None:
    raw = _parse_json_annotation(anns.get(ANN_EVENT), f"{name}.{ANN_EVENT}") or {}
    if not isinstance(raw, dict):
        issues.append(ValidationIssue("error", name, ANN_EVENT, f"expected object, got {type(raw).__name__}"))
        return None
    try:
        body = EventBody.model_validate(raw)
    except pydantic.ValidationError as exc:
        issues.extend(_collect_validation_errors(exc, name, ANN_EVENT))
        return None
    return ResolvedEvent(
        name=name,
        body=body,
        domain=anns.get(ANN_DOMAIN),
        subdomain=anns.get(ANN_SUBDOMAIN),
    )


def _build_state_machine(
    name: str, anns: dict[str, Any], issues: list[ValidationIssue]
) -> ResolvedStateMachine | None:
    raw = _parse_json_annotation(anns.get(ANN_STATE_MACHINE), f"{name}.{ANN_STATE_MACHINE}") or {}
    if not isinstance(raw, dict):
        issues.append(ValidationIssue("error", name, ANN_STATE_MACHINE, f"expected object, got {type(raw).__name__}"))
        return None
    raw = _normalize_transitions(raw)
    try:
        body = StateMachineBody.model_validate(raw)
    except pydantic.ValidationError as exc:
        issues.extend(_collect_validation_errors(exc, name, ANN_STATE_MACHINE))
        return None
    return ResolvedStateMachine(
        name=name,
        body=body,
        domain=anns.get(ANN_DOMAIN),
        subdomain=anns.get(ANN_SUBDOMAIN),
    )


def _build_axioms(owner: str, anns: dict[str, Any], issues: list[ValidationIssue]) -> tuple[AxiomBody, ...]:
    raw = _parse_json_annotation(anns.get(ANN_AXIOMS), f"{owner}.{ANN_AXIOMS}")
    if not raw:
        return ()
    if not isinstance(raw, list):
        issues.append(ValidationIssue("error", owner, ANN_AXIOMS, f"expected a list, got {type(raw).__name__}"))
        return ()
    out: list[AxiomBody] = []
    for i, entry in enumerate(raw):
        try:
            out.append(AxiomBody.model_validate(entry))
        except pydantic.ValidationError as exc:
            for err in exc.errors():
                loc = ".".join(str(p) for p in err["loc"])
                issues.append(
                    ValidationIssue(
                        "error",
                        owner,
                        f"{ANN_AXIOMS}[{i}].{loc}" if loc else f"{ANN_AXIOMS}[{i}]",
                        f"{err['msg']} ({err['type']})",
                    )
                )
    return tuple(out)


def _build_metrics(owner: str, anns: dict[str, Any], issues: list[ValidationIssue]) -> tuple[MetricBody, ...]:
    raw = _parse_json_annotation(anns.get(ANN_METRICS), f"{owner}.{ANN_METRICS}")
    if not raw:
        return ()
    if not isinstance(raw, list):
        issues.append(ValidationIssue("error", owner, ANN_METRICS, f"expected a list, got {type(raw).__name__}"))
        return ()
    out: list[MetricBody] = []
    for i, entry in enumerate(raw):
        try:
            out.append(MetricBody.model_validate(entry))
        except pydantic.ValidationError as exc:
            for err in exc.errors():
                loc = ".".join(str(p) for p in err["loc"])
                issues.append(
                    ValidationIssue(
                        "error",
                        owner,
                        f"{ANN_METRICS}[{i}].{loc}" if loc else f"{ANN_METRICS}[{i}]",
                        f"{err['msg']} ({err['type']})",
                    )
                )
    return tuple(out)


def _build_flow(
    name: str, kind: str, anns: dict[str, Any], issues: list[ValidationIssue]
) -> ResolvedFlow | None:
    raw = _parse_json_annotation(anns.get(ANN_FLOW), f"{name}.{ANN_FLOW}") or {}
    if not isinstance(raw, dict):
        issues.append(ValidationIssue("error", name, ANN_FLOW, f"expected object, got {type(raw).__name__}"))
        return None
    try:
        body = FlowBody.model_validate(raw)
    except pydantic.ValidationError as exc:
        issues.extend(_collect_validation_errors(exc, name, ANN_FLOW))
        return None
    axioms = _build_axioms(name, anns, issues)
    return ResolvedFlow(
        name=name,
        kind=kind,
        body=body,
        axioms=axioms,
        llm_prompt_hint=anns.get(ANN_LLM_PROMPT_HINT),
        domain=anns.get(ANN_DOMAIN),
        subdomain=anns.get(ANN_SUBDOMAIN),
    )


def _build_entity(
    name: str, class_body: dict[str, Any], anns: dict[str, Any], issues: list[ValidationIssue]
) -> ResolvedEntity:
    metrics = _build_metrics(name, anns, issues)
    other_anns = {
        k: v
        for k, v in anns.items()
        if k not in {ANN_METRICS, ANN_DOMAIN, ANN_SUBDOMAIN}
    }
    return ResolvedEntity(
        name=name,
        description=class_body.get("description"),
        attributes=dict(class_body.get("attributes") or {}),
        rules=tuple(class_body.get("rules") or ()),
        metrics=metrics,
        other_annotations=other_anns,
        domain=anns.get(ANN_DOMAIN),
        subdomain=anns.get(ANN_SUBDOMAIN),
    )


# ============================================================================
# Main loader
# ============================================================================


def _local_class_names(path: Path) -> set[str]:
    raw = _load_raw(path)
    return set((raw.get("classes") or {}).keys())


def load_ontology(path: str | Path, strict_warnings: bool = False) -> Ontology:
    """Parse an ontology file (following LinkML's import resolution) into the
    Ontology object model. Performs body validation (Pydantic), cross-reference
    resolution, and warnings collection. Raises OntologyError on errors;
    if strict_warnings is True, also raises on warnings.

    Only classes declared in the main file get dispatched into the model.
    Classes from imports (e.g., core.yaml meta-class shells) are loaded into
    SchemaView but not realized as ontology instances."""
    path = Path(path)
    sv = SchemaView(str(path))
    local_names = _local_class_names(path)

    ontology = Ontology(
        path=path,
        schema_view=sv,
        enums={k: {"permissible_values": list(e.permissible_values.keys())}
                for k, e in (sv.all_enums() or {}).items()
                if k in set((_load_raw(path).get("enums") or {}).keys())},
    )
    issues: list[ValidationIssue] = []

    # Walk every class in the main file
    raw = _load_raw(path)
    for name, class_body in (raw.get("classes") or {}).items():
        if name not in local_names:
            continue
        class_body = class_body or {}
        tags = class_body.get("instantiates") or []
        anns = _get_annotations(class_body)

        if not tags:
            ontology.entities[name] = _build_entity(name, class_body, anns, issues)
            continue

        handled = False
        for tag in tags:
            if tag == TAG_ROLE:
                role = _build_role(name, anns, issues)
                if role:
                    ontology.roles[name] = role
                handled = True
                break
            if tag == TAG_EVENT:
                event = _build_event(name, anns, issues)
                if event:
                    ontology.events[name] = event
                handled = True
                break
            if tag == TAG_STATE_MACHINE:
                sm = _build_state_machine(name, anns, issues)
                if sm:
                    ontology.state_machines[name] = sm
                handled = True
                break
            if tag in _FLOW_KIND_BY_TAG:
                flow = _build_flow(name, _FLOW_KIND_BY_TAG[tag], anns, issues)
                if flow:
                    ontology.flows[name] = flow
                handled = True
                break
            if tag == TAG_FLOW:
                flow = _build_flow(name, "information", anns, issues)
                if flow:
                    ontology.flows[name] = flow
                handled = True
                break

        if not handled:
            # Unknown tag — treat as a plain entity so we don't lose it
            issues.append(
                ValidationIssue("warning", name, "instantiates", f"unknown tag(s) {tags}; treating as entity")
            )
            ontology.entities[name] = _build_entity(name, class_body, anns, issues)

    # Cross-reference + convention checks
    _resolve_cross_references(ontology, issues)
    _check_conventions(ontology, issues)

    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    ontology.warnings = warnings

    if errors:
        raise OntologyError(issues)
    if strict_warnings and warnings:
        raise OntologyError(issues)

    return ontology


# ============================================================================
# Cross-reference resolution
# ============================================================================


def _all_class_names(ontology: Ontology) -> set[str]:
    return (
        set(ontology.entities)
        | set(ontology.roles)
        | set(ontology.events)
        | set(ontology.state_machines)
        | set(ontology.flows)
    )


def _resolve_cross_references(ontology: Ontology, issues: list[ValidationIssue]) -> None:
    known_classes = _all_class_names(ontology)

    # Event.observed_by → Role
    for ev in ontology.events.values():
        if ev.body.observed_by not in ontology.roles:
            issues.append(
                ValidationIssue(
                    "error",
                    ev.name,
                    "observed_by",
                    f"{ev.body.observed_by!r} is not a declared Role",
                )
            )

    # Flow body references
    for flow in ontology.flows.values():
        where = flow.name
        b = flow.body
        if b.source_role not in ontology.roles:
            issues.append(ValidationIssue("error", where, "source_role", f"{b.source_role!r} is not a declared Role"))
        if b.target_role not in ontology.roles:
            issues.append(ValidationIssue("error", where, "target_role", f"{b.target_role!r} is not a declared Role"))
        if b.quantum not in known_classes:
            issues.append(ValidationIssue("error", where, "quantum", f"{b.quantum!r} is not a declared class"))
        if b.returns and b.returns not in known_classes:
            issues.append(ValidationIssue("error", where, "returns", f"{b.returns!r} is not a declared class"))
        if b.trigger_event and b.trigger_event not in ontology.events:
            issues.append(ValidationIssue("error", where, "trigger_event", f"{b.trigger_event!r} is not a declared Event"))
        if b.lifecycle_ref and b.lifecycle_ref not in ontology.state_machines:
            issues.append(
                ValidationIssue("error", where, "lifecycle_ref", f"{b.lifecycle_ref!r} is not a declared StateMachine")
            )
        # Axiom cross-refs
        for axiom in flow.axioms:
            if axiom.on_failure_route_to and axiom.on_failure_route_to not in ontology.flows:
                issues.append(
                    ValidationIssue(
                        "error",
                        where,
                        f"axiom[{axiom.name}].on_failure_route_to",
                        f"{axiom.on_failure_route_to!r} is not a declared flow",
                    )
                )
            if axiom.references and axiom.references.classes:
                for cls in axiom.references.classes:
                    if cls not in known_classes:
                        issues.append(
                            ValidationIssue(
                                "warning",
                                where,
                                f"axiom[{axiom.name}].references.classes",
                                f"{cls!r} is not a declared class",
                            )
                        )
            if axiom.references and axiom.references.flows:
                for fl in axiom.references.flows:
                    if fl not in ontology.flows:
                        issues.append(
                            ValidationIssue(
                                "warning",
                                where,
                                f"axiom[{axiom.name}].references.flows",
                                f"{fl!r} is not a declared flow",
                            )
                        )

    # StateMachine internal consistency + FSM guard → axiom resolution
    # Collect all axiom names in scope (union across flows) for guard resolution.
    all_axiom_names = {
        axiom.name for flow in ontology.flows.values() for axiom in flow.axioms
    }

    for sm in ontology.state_machines.values():
        where = sm.name
        b = sm.body
        states = set(b.states)
        if b.initial not in states:
            issues.append(ValidationIssue("error", where, "initial", f"{b.initial!r} not in states"))
        for term in b.terminal or []:
            if term not in states:
                issues.append(ValidationIssue("error", where, "terminal", f"{term!r} not in states"))
        for i, t in enumerate(b.transitions):
            if t.from_state not in states:
                issues.append(
                    ValidationIssue("error", where, f"transitions[{i}].from_state", f"{t.from_state!r} not in states")
                )
            if t.to_state not in states:
                issues.append(
                    ValidationIssue("error", where, f"transitions[{i}].to_state", f"{t.to_state!r} not in states")
                )
            # Guard → axiom resolution (convention, §11 of design draft)
            if t.guard and t.guard not in all_axiom_names:
                issues.append(
                    ValidationIssue(
                        "error",
                        where,
                        f"transitions[{i}].guard",
                        f"{t.guard!r} does not resolve to any declared axiom name",
                    )
                )

    # Metric.entity → declared class
    for entity in ontology.entities.values():
        for i, metric in enumerate(entity.metrics):
            if metric.entity not in known_classes:
                issues.append(
                    ValidationIssue(
                        "error",
                        entity.name,
                        f"metrics[{i}].entity",
                        f"{metric.entity!r} is not a declared class",
                    )
                )


# ============================================================================
# Convention / warning checks
# ============================================================================


def _check_conventions(ontology: Ontology, issues: list[ValidationIssue]) -> None:
    # Missing llm_prompt_hint on flows (required on every meta-typed element;
    # roles and events have it in the body; flows carry it as a sibling annotation)
    for flow in ontology.flows.values():
        if not flow.llm_prompt_hint:
            issues.append(
                ValidationIssue("warning", flow.name, ANN_LLM_PROMPT_HINT, "missing; every meta-typed element should carry a hint")
            )

    # Missing domain annotations
    for name, r in list(ontology.roles.items()) + [(e.name, e) for e in ontology.events.values()]:
        pass  # evented above in a simpler form
    for label, group in (
        ("role", ontology.roles.values()),
        ("event", ontology.events.values()),
        ("state_machine", ontology.state_machines.values()),
        ("flow", ontology.flows.values()),
        ("entity", ontology.entities.values()),
    ):
        for item in group:
            if not item.domain:
                issues.append(
                    ValidationIssue("warning", item.name, ANN_DOMAIN, f"missing on {label}; every element should declare its domain")
                )

    # Unused elements (warnings only)
    referenced_roles: set[str] = set()
    referenced_events: set[str] = set()
    referenced_fsms: set[str] = set()
    referenced_classes: set[str] = set()

    for flow in ontology.flows.values():
        referenced_roles.add(flow.body.source_role)
        referenced_roles.add(flow.body.target_role)
        referenced_classes.add(flow.body.quantum)
        if flow.body.returns:
            referenced_classes.add(flow.body.returns)
        if flow.body.trigger_event:
            referenced_events.add(flow.body.trigger_event)
        if flow.body.lifecycle_ref:
            referenced_fsms.add(flow.body.lifecycle_ref)
    for event in ontology.events.values():
        referenced_roles.add(event.body.observed_by)

    for name in ontology.roles:
        if name not in referenced_roles:
            issues.append(ValidationIssue("warning", name, None, "role is declared but not referenced by any flow or event"))
    for name in ontology.events:
        if name not in referenced_events:
            issues.append(ValidationIssue("warning", name, None, "event is declared but not triggered by any flow"))
    for name in ontology.state_machines:
        if name not in referenced_fsms:
            issues.append(ValidationIssue("warning", name, None, "state machine is declared but not referenced by any flow"))


# ============================================================================
# External-tool integrations (linkml-lint, gen-doc)
# ============================================================================


def run_linkml_lint(path: Path, strict: bool = False) -> tuple[int, str]:
    """Run linkml-lint as a subprocess; return (exit_code, output).

    Uses .linkmllint.yaml from the ontology's directory if present. In
    non-strict mode, warnings don't cause a non-zero exit (via
    --ignore-warnings); strict mode surfaces everything."""
    cmd = ["linkml-lint"]
    config = path.parent / ".linkmllint.yaml"
    if config.exists():
        cmd.extend(["--config", str(config)])
    if not strict:
        cmd.append("--ignore-warnings")
    cmd.append(str(path))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode, (result.stdout or "") + (result.stderr or "")
    except FileNotFoundError:
        return 127, "linkml-lint not found on PATH (install linkml)"


def run_gen_doc(path: Path, output_dir: Path) -> tuple[int, str]:
    """Run gen-doc as a subprocess; produces markdown + Mermaid to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["gen-doc", "--directory", str(output_dir), str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, (result.stdout or "") + (result.stderr or "")
    except FileNotFoundError:
        return 127, "gen-doc not found on PATH (install linkml)"


def run_regen_bodies(meta_path: Path, out_path: Path) -> tuple[int, str]:
    """Run gen-pydantic on scont_meta.yaml to refresh scont_bodies.py."""
    try:
        result = subprocess.run(
            ["gen-pydantic", str(meta_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            out_path.write_text(result.stdout)
        return result.returncode, result.stderr or ""
    except FileNotFoundError:
        return 127, "gen-pydantic not found on PATH (install linkml)"


# ============================================================================
# CLI subcommands
# ============================================================================


def _print_summary(ontology: Ontology) -> None:
    print(ontology.summary())
    print()
    print("Entities:")
    for e in ontology.entities.values():
        extras = []
        if e.rules:
            extras.append(f"{len(e.rules)} rule(s)")
        if e.metrics:
            extras.append(f"{len(e.metrics)} metric(s)")
        suffix = f" [{', '.join(extras)}]" if extras else ""
        dom = f" ({e.domain})" if e.domain else ""
        print(f"  - {e.name}: {len(e.attributes)} attr(s){suffix}{dom}")
    print()
    print("Roles:")
    for r in ontology.roles.values():
        marks = []
        if r.body.is_boundary:
            marks.append("boundary")
        if r.body.human_involvement:
            marks.append(f"hitl={r.body.human_involvement}")
        mark = f" [{', '.join(marks)}]" if marks else ""
        print(f"  - {r.name}{mark}: {r.body.description}")
    print()
    print("Events:")
    for e in ontology.events.values():
        print(f"  - {e.name}: observed_by={e.body.observed_by}")
    print()
    print("State machines:")
    for sm in ontology.state_machines.values():
        print(f"  - {sm.name}: {len(sm.body.states)} states, {len(sm.body.transitions)} transitions")
    print()
    print("Flows:")
    for f in ontology.flows.values():
        suffix_parts = []
        if f.axioms:
            suffix_parts.append(f"{len(f.axioms)} axiom(s)")
        if f.body.returns:
            suffix_parts.append(f"returns={f.body.returns}")
        suffix = f", {', '.join(suffix_parts)}" if suffix_parts else ""
        print(f"  - {f.name} [{f.kind}]: {f.body.source_role} → {f.body.target_role}, quantum={f.body.quantum}{suffix}")


def cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.path)
    strict = bool(args.strict)
    try:
        ontology = load_ontology(path, strict_warnings=strict)
    except OntologyError as err:
        for issue in err.issues:
            print(issue.format(), file=sys.stderr)
        print(file=sys.stderr)
        print(f"FAILED: {len([i for i in err.issues if i.level == 'error'])} error(s), "
              f"{len([i for i in err.issues if i.level == 'warning'])} warning(s)", file=sys.stderr)
        return 1

    # Warnings (if any) are already collected on ontology.warnings
    for w in ontology.warnings:
        print(w.format(), file=sys.stderr)

    if args.with_linkml_lint:
        rc, out = run_linkml_lint(path, strict=strict)
        print("--- linkml-lint ---")
        print(out.strip() or "(no problems found)")
        if rc != 0:
            return rc

    print(ontology.summary())
    print(f"OK: {len(ontology.warnings)} warning(s), 0 errors")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    path = Path(args.path)
    ontology = load_ontology(path)
    if args.json:
        print(json.dumps(ontology.summary_dict(), indent=2, default=str))
    else:
        _print_summary(ontology)
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    path = Path(args.path)
    ontology = load_ontology(path)
    name = args.element

    for kind, getter in (
        ("flow", ontology.get_flow),
        ("role", ontology.get_role),
        ("event", ontology.get_event),
        ("state_machine", ontology.get_state_machine),
        ("entity", ontology.get_entity),
    ):
        item = getter(name)
        if item:
            if args.json:
                print(json.dumps({"kind": kind, **_inspect_dict(item)}, indent=2, default=str))
            else:
                print(f"{kind}: {name}")
                for k, v in _inspect_dict(item).items():
                    print(f"  {k}: {v}")
            return 0

    print(f"not found: {name}", file=sys.stderr)
    return 1


def _inspect_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, ResolvedRole):
        return {
            "description": item.body.description,
            "llm_prompt_hint": item.body.llm_prompt_hint,
            "is_boundary": bool(item.body.is_boundary),
            "human_involvement": item.body.human_involvement,
            "domain": item.domain,
        }
    if isinstance(item, ResolvedEvent):
        return {
            "description": item.body.description,
            "observed_by": item.body.observed_by,
            "llm_prompt_hint": item.body.llm_prompt_hint,
            "domain": item.domain,
        }
    if isinstance(item, ResolvedFlow):
        return {
            "kind": item.kind,
            "source_role": item.body.source_role,
            "target_role": item.body.target_role,
            "quantum": item.body.quantum,
            "returns": item.body.returns,
            "trigger_event": item.body.trigger_event,
            "lifecycle_ref": item.body.lifecycle_ref,
            "axioms": [a.name for a in item.axioms],
            "llm_prompt_hint": item.llm_prompt_hint,
            "domain": item.domain,
        }
    if isinstance(item, ResolvedStateMachine):
        return {
            "states": item.body.states,
            "transitions": [
                {"from_state": t.from_state, "to_state": t.to_state, "trigger": t.trigger, "guard": t.guard}
                for t in item.body.transitions
            ],
            "initial": item.body.initial,
            "terminal": item.body.terminal,
        }
    if isinstance(item, ResolvedEntity):
        return {
            "description": item.description,
            "attributes": list(item.attributes.keys()),
            "rules": len(item.rules),
            "metrics": [m.name for m in item.metrics],
            "domain": item.domain,
        }
    return {"raw": repr(item)}


def cmd_query(args: argparse.Namespace) -> int:
    """Minimal query: `source_role=X target_role=Y ...`. Restricted to flows for now."""
    path = Path(args.path)
    ontology = load_ontology(path)

    filters: dict[str, str] = {}
    for expr in args.expr:
        if "=" not in expr:
            print(f"malformed filter: {expr!r}; expected key=value", file=sys.stderr)
            return 2
        k, v = expr.split("=", 1)
        filters[k.strip()] = v.strip()

    flows = ontology.list_flows_where(**filters)  # type: ignore[arg-type]
    if args.json:
        print(json.dumps([Ontology._flow_summary(f) | {"name": f.name} for f in flows], indent=2, default=str))
    else:
        for f in flows:
            print(f"{f.name} [{f.kind}]: {f.body.source_role} → {f.body.target_role}, quantum={f.body.quantum}")
    return 0


def cmd_doc(args: argparse.Namespace) -> int:
    path = Path(args.path)
    output = Path(args.output)
    rc, out = run_gen_doc(path, output)
    print(out.strip() or f"(gen-doc wrote to {output})")
    return rc


def cmd_regen_bodies(args: argparse.Namespace) -> int:
    meta = Path(args.meta)
    out = Path(args.out)
    rc, err = run_regen_bodies(meta, out)
    if rc == 0:
        print(f"regenerated {out} from {meta}")
    else:
        print(err, file=sys.stderr)
    return rc


# ============================================================================
# Entry point
# ============================================================================


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="exploder",
        description="Supply chain ontology control plane — validate, inspect, and query a scont-extended LinkML ontology.",
    )
    sub = p.add_subparsers(dest="cmd")

    val = sub.add_parser("validate", help="Validate ontology; non-zero exit on errors.")
    val.add_argument("path")
    val.add_argument("--strict", action="store_true", help="Treat warnings as errors.")
    val.add_argument("--with-linkml-lint", action="store_true", help="Also run linkml-lint.")
    val.set_defaults(func=cmd_validate)

    summ = sub.add_parser("summary", help="Print an ontology summary.")
    summ.add_argument("path")
    summ.add_argument("--json", action="store_true", help="Machine-readable output.")
    summ.set_defaults(func=cmd_summary)

    insp = sub.add_parser("inspect", help="Show details for one element.")
    insp.add_argument("path")
    insp.add_argument("element")
    insp.add_argument("--json", action="store_true")
    insp.set_defaults(func=cmd_inspect)

    qry = sub.add_parser("query", help="Filter flows by key=value predicates.")
    qry.add_argument("path")
    qry.add_argument("expr", nargs="*")
    qry.add_argument("--json", action="store_true")
    qry.set_defaults(func=cmd_query)

    doc = sub.add_parser("doc", help="Generate gen-doc markdown + Mermaid diagrams.")
    doc.add_argument("path")
    doc.add_argument("--output", default="docs/")
    doc.set_defaults(func=cmd_doc)

    regen = sub.add_parser("regen-bodies", help="Regenerate scont_bodies.py from scont_meta.yaml via gen-pydantic.")
    regen.add_argument("--meta", default="scont_meta.yaml")
    regen.add_argument("--out", default="scont_bodies.py")
    regen.set_defaults(func=cmd_regen_bodies)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    # Back-compat: `python exploder.py <path>` behaves like `summary <path>`
    if argv is None:
        argv = sys.argv[1:]
    if argv and not argv[0].startswith("-") and argv[0] not in {
        "validate", "summary", "inspect", "query", "doc", "regen-bodies"
    }:
        argv = ["summary", *argv]
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
