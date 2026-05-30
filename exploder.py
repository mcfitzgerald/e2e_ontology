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
import contextlib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator

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
    PlaybookBody,
    ToolBody,
)


# ============================================================================
# Tags
# ============================================================================

TAG_ROLE = "scont:Role"
TAG_EVENT = "scont:Event"
TAG_STATE_MACHINE = "scont:StateMachine"
TAG_FLOW = "scont:Flow"
TAG_PLAYBOOK = "scont:Playbook"
TAG_TOOL = "scont:Tool"
_FLOW_KIND_BY_TAG = {
    "scont:InformationFlow": "information",
    "scont:MaterialFlow": "material",
    "scont:CashFlow": "cash",
}

ANN_ROLE = "scont:role"
ANN_EVENT = "scont:event"
ANN_STATE_MACHINE = "scont:state_machine"
ANN_FLOW = "scont:flow"
ANN_PLAYBOOK = "scont:playbook"
ANN_TOOL = "scont:tool"
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
class ResolvedPlaybook:
    name: str
    body: PlaybookBody
    llm_prompt_hint: str | None
    domain: str | None = None
    subdomain: str | None = None


@dataclass(frozen=True)
class ResolvedTool:
    name: str
    body: ToolBody
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
    playbooks: dict[str, ResolvedPlaybook] = field(default_factory=dict)
    tools: dict[str, ResolvedTool] = field(default_factory=dict)
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
            f"{len(self.playbooks)} playbooks, "
            f"{len(self.tools)} tools, "
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
            "playbooks": {k: self._playbook_summary(v) for k, v in self.playbooks.items()},
            "tools": {k: self._tool_summary(v) for k, v in self.tools.items()},
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

    @staticmethod
    def _playbook_summary(p: ResolvedPlaybook) -> dict[str, Any]:
        b = p.body
        return {
            "role": b.role,
            "triggered_by": b.triggered_by,
            "input_quantum": b.input_quantum,
            "context_assembly": [s.flow for s in (b.context_assembly or [])],
            "criteria_refs": list(b.decision.criteria_refs) if b.decision else [],
            "selects_one_of": list(b.decision.selects_one_of) if b.decision else [],
            "domain": p.domain,
        }

    @staticmethod
    def _tool_summary(t: ResolvedTool) -> dict[str, Any]:
        b = t.body
        return {
            "category": b.category,
            "input_class": b.input_class,
            "output_class": b.output_class,
            "implementation": b.implementation,
            "available_to": list(b.available_to),
            "domain": t.domain,
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

    def get_playbook(self, name: str) -> ResolvedPlaybook | None:
        return self.playbooks.get(name)

    def get_tool(self, name: str) -> ResolvedTool | None:
        return self.tools.get(name)

    def playbooks_for_role(self, role: str) -> list[ResolvedPlaybook]:
        """Playbooks anchored to this role (body.role == role). Sorted by name."""
        out = [p for p in self.playbooks.values() if p.body.role == role]
        return sorted(out, key=lambda p: p.name)

    def tools_for_role(self, role: str) -> list[ResolvedTool]:
        """Tools this role may invoke (role in body.available_to). Sorted by name."""
        out = [t for t in self.tools.values() if role in (t.body.available_to or [])]
        return sorted(out, key=lambda t: t.name)

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
# Structural diff — compare two Ontology instances
# ============================================================================


DIFF_KINDS = ("entities", "roles", "events", "state_machines", "flows", "enums", "warnings")


@dataclass(frozen=True)
class ElementChange:
    """A single element (by name) that exists in both ontologies but differs.
    `changes` is a list of (field_path, before, after) tuples. Field paths use
    dotted form (`body.source_role`, `axioms.line_capacity_not_exceeded.severity`)."""
    name: str
    changes: tuple[tuple[str, Any, Any], ...]


@dataclass(frozen=True)
class TypedDelta:
    """Per-element-kind delta. Any or all of added/removed/changed may be empty;
    a TypedDelta appears in `compute_delta` output only if at least one is non-empty."""
    kind: str  # one of DIFF_KINDS
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    changed: tuple[ElementChange, ...] = ()


def _element_to_comparable(kind: str, elem: Any) -> Any:
    """Normalize an element to a plain dict for comparison. Each kind has its
    own extraction because Ontology element types are heterogeneous."""
    if kind == "entities":
        return {
            "description": elem.description,
            "attributes": elem.attributes,
            "rules": list(elem.rules),
            "metrics": {m.name: m.model_dump(mode="json") for m in elem.metrics},
            "domain": elem.domain,
            "subdomain": elem.subdomain,
        }
    if kind in ("roles", "events", "state_machines"):
        return {
            "body": elem.body.model_dump(mode="json"),
            "domain": elem.domain,
            "subdomain": elem.subdomain,
        }
    if kind == "flows":
        return {
            "flow_kind": elem.kind,
            "body": elem.body.model_dump(mode="json"),
            "axioms": {a.name: a.model_dump(mode="json") for a in elem.axioms},
            "llm_prompt_hint": elem.llm_prompt_hint,
            "domain": elem.domain,
            "subdomain": elem.subdomain,
        }
    if kind == "enums":
        return elem  # raw dict from YAML
    raise ValueError(f"unknown diff kind {kind!r}")


def _diff_values(before: Any, after: Any, path: str = "") -> list[tuple[str, Any, Any]]:
    """Recursive leaf-level diff. Walks dicts; compares lists and scalars as
    atomic values. Returns (dotted_path, before, after) tuples."""
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        out: list[tuple[str, Any, Any]] = []
        for k in sorted(set(before) | set(after)):
            b = before.get(k)
            a = after.get(k)
            if b == a:
                continue
            subpath = f"{path}.{k}" if path else k
            if isinstance(b, dict) and isinstance(a, dict):
                out.extend(_diff_values(b, a, subpath))
            else:
                out.append((subpath, b, a))
        return out
    return [(path, before, after)]


def compute_delta(
    old: "Ontology",
    new: "Ontology",
    kinds: Iterable[str] | None = None,
) -> list[TypedDelta]:
    """Compare two Ontology instances element-by-element. Returns one TypedDelta
    per element kind that has any change; empty list means ontologies match on
    the selected kinds."""
    selected = set(kinds) if kinds is not None else set(DIFF_KINDS)
    result: list[TypedDelta] = []

    sources = {
        "entities": (old.entities, new.entities),
        "roles": (old.roles, new.roles),
        "events": (old.events, new.events),
        "state_machines": (old.state_machines, new.state_machines),
        "flows": (old.flows, new.flows),
        "enums": (old.enums, new.enums),
    }

    for kind, (old_map, new_map) in sources.items():
        if kind not in selected:
            continue
        added = tuple(sorted(k for k in new_map if k not in old_map))
        removed = tuple(sorted(k for k in old_map if k not in new_map))
        changed: list[ElementChange] = []
        for name in sorted(set(old_map) & set(new_map)):
            before = _element_to_comparable(kind, old_map[name])
            after = _element_to_comparable(kind, new_map[name])
            diffs = _diff_values(before, after)
            if diffs:
                changed.append(ElementChange(name=name, changes=tuple(diffs)))
        if added or removed or changed:
            result.append(TypedDelta(kind=kind, added=added, removed=removed, changed=tuple(changed)))

    if "warnings" in selected:
        old_warns = sorted(w.format() for w in old.warnings)
        new_warns = sorted(w.format() for w in new.warnings)
        if old_warns != new_warns:
            added_w = tuple(sorted(set(new_warns) - set(old_warns)))
            removed_w = tuple(sorted(set(old_warns) - set(new_warns)))
            if added_w or removed_w:
                result.append(TypedDelta(kind="warnings", added=added_w, removed=removed_w))

    return result


# ============================================================================
# Delta rendering
# ============================================================================


_ANSI = {
    "reset": "\033[0m",
    "added": "\033[32m",    # green
    "removed": "\033[31m",  # red
    "changed": "\033[33m",  # yellow
    "kind": "\033[1;36m",   # bold cyan
    "dim": "\033[2m",
}


def _color(code: str, text: str, use_color: bool) -> str:
    if not use_color:
        return text
    return f"{_ANSI[code]}{text}{_ANSI['reset']}"


def _fmt_value(v: Any) -> str:
    """Compact single-line render for diff values. None → ∅."""
    if v is None:
        return "∅"
    if isinstance(v, str):
        return repr(v)
    if isinstance(v, (dict, list)):
        return json.dumps(v, default=str, sort_keys=True)
    return repr(v)


def render_delta_human(deltas: list[TypedDelta], use_color: bool = False) -> str:
    """Human-readable rendering. Groups by kind; within kind, added / removed /
    changed sections. Each changed element's field diffs are indented."""
    if not deltas:
        return "(no differences)"
    lines: list[str] = []
    for d in deltas:
        lines.append(_color("kind", f"── {d.kind} ──", use_color))
        if d.added:
            for n in d.added:
                lines.append(_color("added", f"  + {n}", use_color))
        if d.removed:
            for n in d.removed:
                lines.append(_color("removed", f"  - {n}", use_color))
        for change in d.changed:
            lines.append(_color("changed", f"  ~ {change.name}", use_color))
            for fpath, before, after in change.changes:
                lines.append(
                    "      "
                    + _color("dim", fpath, use_color)
                    + ": "
                    + _color("removed", _fmt_value(before), use_color)
                    + " → "
                    + _color("added", _fmt_value(after), use_color)
                )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_delta_json(deltas: list[TypedDelta]) -> str:
    """Machine-readable rendering. Each delta becomes a JSON object with
    kind/added/removed/changed; each change has name and a list of
    [field_path, before, after] triples."""
    payload = []
    for d in deltas:
        payload.append({
            "kind": d.kind,
            "added": list(d.added),
            "removed": list(d.removed),
            "changed": [
                {
                    "name": c.name,
                    "changes": [list(t) for t in c.changes],
                }
                for c in d.changed
            ],
        })
    return json.dumps(payload, indent=2, default=str)


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


def _build_playbook(
    name: str, anns: dict[str, Any], issues: list[ValidationIssue]
) -> ResolvedPlaybook | None:
    raw = _parse_json_annotation(anns.get(ANN_PLAYBOOK), f"{name}.{ANN_PLAYBOOK}") or {}
    if not isinstance(raw, dict):
        issues.append(ValidationIssue("error", name, ANN_PLAYBOOK, f"expected object, got {type(raw).__name__}"))
        return None
    try:
        body = PlaybookBody.model_validate(raw)
    except pydantic.ValidationError as exc:
        issues.extend(_collect_validation_errors(exc, name, ANN_PLAYBOOK))
        return None
    return ResolvedPlaybook(
        name=name,
        body=body,
        llm_prompt_hint=anns.get(ANN_LLM_PROMPT_HINT),
        domain=anns.get(ANN_DOMAIN),
        subdomain=anns.get(ANN_SUBDOMAIN),
    )


def _build_tool(
    name: str, anns: dict[str, Any], issues: list[ValidationIssue]
) -> ResolvedTool | None:
    raw = _parse_json_annotation(anns.get(ANN_TOOL), f"{name}.{ANN_TOOL}") or {}
    if not isinstance(raw, dict):
        issues.append(ValidationIssue("error", name, ANN_TOOL, f"expected object, got {type(raw).__name__}"))
        return None
    try:
        body = ToolBody.model_validate(raw)
    except pydantic.ValidationError as exc:
        issues.extend(_collect_validation_errors(exc, name, ANN_TOOL))
        return None
    return ResolvedTool(
        name=name,
        body=body,
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
            if tag == TAG_PLAYBOOK:
                playbook = _build_playbook(name, anns, issues)
                if playbook:
                    ontology.playbooks[name] = playbook
                handled = True
                break
            if tag == TAG_TOOL:
                tool = _build_tool(name, anns, issues)
                if tool:
                    ontology.tools[name] = tool
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
        | set(ontology.playbooks)
        | set(ontology.tools)
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

    # Playbook + Tool cross-refs (Phase 1.8)
    _resolve_playbook_references(ontology, issues, known_classes)
    _resolve_tool_references(ontology, issues, known_classes)


def _axiom_severity_index(ontology: Ontology) -> dict[str, str | None]:
    """Map every flow-declared axiom name to its severity string. Used to
    validate Playbook decision.criteria_refs resolve to *advisory* axioms.
    Severity is already a string under use_enum_values; normalize defensively."""
    index: dict[str, str | None] = {}
    for flow in ontology.flows.values():
        for ax in flow.axioms:
            sev = ax.severity
            index[ax.name] = sev.value if hasattr(sev, "value") else sev
    return index


def _resolve_playbook_references(
    ontology: Ontology, issues: list[ValidationIssue], known_classes: set[str]
) -> None:
    severities = _axiom_severity_index(ontology)
    seen_anchors: dict[tuple[str, str], str] = {}

    for pb in ontology.playbooks.values():
        where = pb.name
        b = pb.body
        if b.role not in ontology.roles:
            issues.append(ValidationIssue("error", where, "role", f"{b.role!r} is not a declared Role"))
        if b.triggered_by not in ontology.events:
            issues.append(ValidationIssue("error", where, "triggered_by", f"{b.triggered_by!r} is not a declared Event"))
        if b.input_quantum not in known_classes:
            issues.append(ValidationIssue("error", where, "input_quantum", f"{b.input_quantum!r} is not a declared class"))

        # context_assembly[].flow must resolve to a query flow (returns: set)
        for i, step in enumerate(b.context_assembly or []):
            target = ontology.flows.get(step.flow)
            if target is None:
                issues.append(
                    ValidationIssue("error", where, f"context_assembly[{i}].flow", f"{step.flow!r} is not a declared flow")
                )
            elif not target.body.returns:
                issues.append(
                    ValidationIssue(
                        "error",
                        where,
                        f"context_assembly[{i}].flow",
                        f"{step.flow!r} is not a query flow (no `returns:` — context assembly needs request-response flows)",
                    )
                )

        if b.decision is not None:
            for i, crit in enumerate(b.decision.criteria_refs or []):
                if crit not in severities:
                    issues.append(
                        ValidationIssue("error", where, f"decision.criteria_refs[{i}]", f"{crit!r} does not resolve to any declared axiom")
                    )
                elif severities[crit] != "advisory":
                    issues.append(
                        ValidationIssue(
                            "error",
                            where,
                            f"decision.criteria_refs[{i}]",
                            f"{crit!r} is severity {severities[crit]!r}; criteria_refs must reference advisory axioms",
                        )
                    )
            for i, res in enumerate(b.decision.selects_one_of or []):
                if res not in ontology.flows:
                    issues.append(
                        ValidationIssue("error", where, f"decision.selects_one_of[{i}]", f"{res!r} is not a declared flow")
                    )

        # always_fires[] — exactly one of event/flow, and it must resolve
        for i, eff in enumerate(b.always_fires or []):
            if bool(eff.event) == bool(eff.flow):
                issues.append(
                    ValidationIssue("error", where, f"always_fires[{i}]", "exactly one of `event` / `flow` must be set")
                )
            if eff.event and eff.event not in ontology.events:
                issues.append(
                    ValidationIssue("error", where, f"always_fires[{i}].event", f"{eff.event!r} is not a declared Event")
                )
            if eff.flow and eff.flow not in ontology.flows:
                issues.append(
                    ValidationIssue("error", where, f"always_fires[{i}].flow", f"{eff.flow!r} is not a declared flow")
                )

        # Single-playbook-per-(role, triggered_by) — §12.4 defaulted answer.
        anchor = (b.role, b.triggered_by)
        if anchor in seen_anchors:
            issues.append(
                ValidationIssue(
                    "error",
                    where,
                    "role/triggered_by",
                    f"duplicate playbook anchor ({b.role}, {b.triggered_by}); already claimed by "
                    f"{seen_anchors[anchor]!r}. Single-playbook-per-(role, event) is enforced.",
                )
            )
        else:
            seen_anchors[anchor] = pb.name


def _resolve_tool_references(
    ontology: Ontology, issues: list[ValidationIssue], known_classes: set[str]
) -> None:
    for tool in ontology.tools.values():
        where = tool.name
        b = tool.body
        if b.input_class not in known_classes:
            issues.append(ValidationIssue("error", where, "input_class", f"{b.input_class!r} is not a declared class"))
        if b.output_class not in known_classes:
            issues.append(ValidationIssue("error", where, "output_class", f"{b.output_class!r} is not a declared class"))
        for i, role in enumerate(b.available_to or []):
            if role not in ontology.roles:
                issues.append(
                    ValidationIssue("error", where, f"available_to[{i}]", f"{role!r} is not a declared Role")
                )
        # `implementation` is a contract name bound by the orchestrator at boot;
        # it intentionally does not resolve to anything in the ontology.


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
        ("playbook", ontology.playbooks.values()),
        ("tool", ontology.tools.values()),
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
    # Playbooks and tools also reference roles/events/classes — count them so a
    # role/event used only by a playbook or tool isn't flagged unused.
    for pb in ontology.playbooks.values():
        referenced_roles.add(pb.body.role)
        referenced_events.add(pb.body.triggered_by)
        referenced_classes.add(pb.body.input_quantum)
        for eff in pb.body.always_fires or []:
            if eff.event:
                referenced_events.add(eff.event)
    for tool in ontology.tools.values():
        for role in tool.body.available_to or []:
            referenced_roles.add(role)
        referenced_classes.add(tool.body.input_class)
        referenced_classes.add(tool.body.output_class)

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
    if ontology.playbooks:
        print()
        print("Playbooks:")
        for p in ontology.playbooks.values():
            print(f"  - {p.name}: anchored to ({p.body.role}, {p.body.triggered_by})")
    if ontology.tools:
        print()
        print("Tools:")
        for t in ontology.tools.values():
            print(f"  - {t.name} [{t.body.category}]: {t.body.input_class} → {t.body.output_class}, available_to={', '.join(t.body.available_to)}")


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
        ("playbook", ontology.get_playbook),
        ("tool", ontology.get_tool),
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
    if isinstance(item, ResolvedPlaybook):
        b = item.body
        return {
            "role": b.role,
            "triggered_by": b.triggered_by,
            "input_quantum": b.input_quantum,
            "context_assembly": [s.flow for s in (b.context_assembly or [])],
            "synchronization": b.synchronization,
            "criteria_refs": list(b.decision.criteria_refs) if b.decision else [],
            "selects_one_of": list(b.decision.selects_one_of) if b.decision else [],
            "always_fires": [e.event or e.flow for e in (b.always_fires or [])],
            "llm_prompt_hint": item.llm_prompt_hint,
            "domain": item.domain,
        }
    if isinstance(item, ResolvedTool):
        b = item.body
        return {
            "category": b.category,
            "description": b.description,
            "input_class": b.input_class,
            "output_class": b.output_class,
            "implementation": b.implementation,
            "available_to": list(b.available_to),
            "llm_prompt_hint": item.llm_prompt_hint,
            "domain": item.domain,
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


class DiffInputError(ValueError):
    """Raised when a diff argument can't be resolved to a file or git ref."""


def _is_existing_path(arg: str) -> bool:
    # Anything with a path separator or an existing filesystem entry is a path,
    # not a git ref. Plain names like 'HEAD' or a bare branch never pass this.
    if "/" in arg or "\\" in arg:
        return True
    return Path(arg).exists()


def _git_archive_to(ref: str, dest: Path) -> None:
    """Extract the repo's tracked contents at `ref` into `dest` via
    `git archive | tar -x`. Raises DiffInputError if the ref doesn't resolve."""
    try:
        archive = subprocess.run(
            ["git", "archive", "--format=tar", ref],
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise DiffInputError("git not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or b"").decode(errors="replace").strip()
        raise DiffInputError(f"could not resolve git ref {ref!r}: {stderr}") from exc
    try:
        subprocess.run(
            ["tar", "-x", "-C", str(dest)],
            input=archive.stdout,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or b"").decode(errors="replace").strip()
        raise DiffInputError(f"tar extraction failed for ref {ref!r}: {stderr}") from exc


@contextlib.contextmanager
def _resolve_diff_inputs(
    arg1: str, arg2: str, file_override: str | None
) -> Iterator[tuple[Path, Path]]:
    """Map a pair of CLI args (each either a disk path or a git ref, optionally
    `<ref>:<file>`) to a pair of filesystem paths pointing at loadable ontology
    YAML. Materializes git refs via `git archive` into tempdirs so that LinkML
    imports resolve. Cleans up tempdirs on exit.

    Filename inference for a bare ref: use `--file` if given, else borrow the
    basename of the other arg when it's a disk path. Raises DiffInputError if
    neither is available."""
    tempdirs: list[Path] = []

    def _resolve(primary: str, fallback_name: str | None) -> Path:
        if ":" not in primary and _is_existing_path(primary):
            return Path(primary)
        if ":" in primary:
            ref, _, file = primary.partition(":")
        else:
            ref = primary
            file = file_override or fallback_name
        if not file:
            raise DiffInputError(
                f"{primary!r} is a bare git ref — pass --file <path> or use "
                f"'{primary}:<path>' to name the file within the ref"
            )
        tmp = Path(tempfile.mkdtemp(prefix="exploder-diff-"))
        tempdirs.append(tmp)
        _git_archive_to(ref, tmp)
        resolved = tmp / file
        if not resolved.exists():
            raise DiffInputError(
                f"{file!r} does not exist at ref {ref!r} (looked in {tmp})"
            )
        return resolved

    # First pass: if exactly one arg is a disk path, use its basename as the
    # default for the other arg. Lets `exploder diff HEAD~1 path/to/file.yaml`
    # work without --file.
    path1_is_disk = ":" not in arg1 and _is_existing_path(arg1)
    path2_is_disk = ":" not in arg2 and _is_existing_path(arg2)
    fallback1 = Path(arg2).name if path2_is_disk and not path1_is_disk else None
    fallback2 = Path(arg1).name if path1_is_disk and not path2_is_disk else None

    try:
        p1 = _resolve(arg1, fallback1)
        p2 = _resolve(arg2, fallback2)
        yield p1, p2
    finally:
        for t in tempdirs:
            shutil.rmtree(t, ignore_errors=True)


def cmd_diff(args: argparse.Namespace) -> int:
    kinds: set[str] | None = None
    if args.only:
        kinds = {k.strip() for k in args.only.split(",") if k.strip()}
        invalid = kinds - set(DIFF_KINDS)
        if invalid:
            print(
                f"unknown kind(s) in --only: {sorted(invalid)}. "
                f"Valid kinds: {list(DIFF_KINDS)}",
                file=sys.stderr,
            )
            return 2

    try:
        with _resolve_diff_inputs(args.path1, args.path2, args.file) as (p1, p2):
            old = load_ontology(p1)
            new = load_ontology(p2)
            deltas = compute_delta(old, new, kinds=kinds)
    except DiffInputError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(render_delta_json(deltas))
    else:
        use_color = sys.stdout.isatty() and not args.no_color
        print(render_delta_human(deltas, use_color=use_color), end="")
    return 0


# ============================================================================
# Scaffolding — emit YAML fragments for new elements
# ============================================================================


SCAFFOLD_KINDS = ("role", "event", "flow", "query-flow", "state-machine", "axiom", "entity")

_TAG_BY_KIND = {
    "role": "scont:Role",
    "event": "scont:Event",
    "flow": "scont:InformationFlow",
    "query-flow": "scont:InformationFlow",
    "state-machine": "scont:StateMachine",
}

_BODY_ANNOTATION_BY_KIND: dict[str, tuple[str, type[pydantic.BaseModel]]] = {
    "role": (ANN_ROLE, RoleBody),
    "event": (ANN_EVENT, EventBody),
    "flow": (ANN_FLOW, FlowBody),
    "query-flow": (ANN_FLOW, FlowBody),
    "state-machine": (ANN_STATE_MACHINE, StateMachineBody),
}

# State-machine body needs structured placeholders (list[str] and
# list[TransitionBody]) that `<STATES>` can't satisfy. Use these when the user
# doesn't supply values.
_STATE_MACHINE_DEFAULTS: dict[str, Any] = {
    "states": ["<STATE_1>", "<STATE_2>"],
    "transitions": [
        {"from_state": "<STATE_1>", "to_state": "<STATE_2>", "trigger": "<TRIGGER>"}
    ],
    "initial": "<STATE_1>",
}


class ScaffoldError(ValueError):
    """Raised when scaffolding inputs are malformed."""


def _unwrap_type(annotation: Any) -> Any:
    import typing
    origin = getattr(annotation, "__origin__", None)
    if origin is typing.Union:
        non_none = [a for a in annotation.__args__ if a is not type(None)]
        if non_none:
            return _unwrap_type(non_none[0])
    return annotation


def _field_descriptor(cls: type[pydantic.BaseModel], name: str) -> str:
    """Short human-readable type description for the optional-fields comment."""
    import enum
    info = cls.model_fields[name]
    annotation = _unwrap_type(info.annotation)
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        return " | ".join(repr(v.value) for v in annotation)
    origin = getattr(annotation, "__origin__", None)
    if origin is list:
        inner = _unwrap_type(annotation.__args__[0]) if annotation.__args__ else str
        if isinstance(inner, type) and issubclass(inner, enum.Enum):
            return "list[" + " | ".join(repr(v.value) for v in inner) + "]"
        inner_name = getattr(inner, "__name__", "any")
        return f"list[{inner_name}]"
    if isinstance(annotation, type):
        return annotation.__name__
    return repr(annotation)


def _required_field_names(cls: type[pydantic.BaseModel]) -> list[str]:
    return [n for n, info in cls.model_fields.items() if info.is_required()]


def _optional_field_names(cls: type[pydantic.BaseModel]) -> list[str]:
    return [n for n, info in cls.model_fields.items() if not info.is_required()]


def _body_class_for_kind(kind: str) -> type[pydantic.BaseModel] | None:
    """Return the Pydantic body class for a kind, or None if the kind has no
    annotation body (entity is plain LinkML; axiom is a list entry, not a class)."""
    entry = _BODY_ANNOTATION_BY_KIND.get(kind)
    if entry:
        return entry[1]
    if kind == "axiom":
        return AxiomBody
    return None


def _coerce_value(cls: type[pydantic.BaseModel], field_name: str, raw: Any) -> Any:
    """Normalize a CLI-string value for JSON emission. Strings pass through;
    list[str] fields split on commas; bool fields parse true/false."""
    if field_name not in cls.model_fields:
        return raw
    annotation = _unwrap_type(cls.model_fields[field_name].annotation)
    if isinstance(raw, str):
        if annotation is bool:
            return raw.strip().lower() in ("1", "true", "yes", "y")
        origin = getattr(annotation, "__origin__", None)
        if origin is list:
            return [s.strip() for s in raw.split(",") if s.strip()]
    return raw


def _indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line if line else line for line in text.splitlines())


def _build_body_dict(
    cls: type[pydantic.BaseModel],
    values: dict[str, Any],
    required: list[str],
    defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct the body dict in declaration order: required first (filled or
    placeholder), then any optional fields the caller has explicitly supplied."""
    body: dict[str, Any] = {}
    for f in required:
        if f in values:
            body[f] = _coerce_value(cls, f, values[f])
        elif defaults and f in defaults:
            body[f] = defaults[f]
        else:
            body[f] = f"<{f.upper()}>"
    for f, v in values.items():
        if f in cls.model_fields and f not in body:
            body[f] = _coerce_value(cls, f, v)
    return body


def _optional_comment_lines(
    cls: type[pydantic.BaseModel], exclude: set[str], indent: str
) -> list[str]:
    optionals = [n for n in _optional_field_names(cls) if n not in exclude]
    if not optionals:
        return []
    lines = [f"{indent}# Optional body fields (add inside the JSON below as needed):"]
    for n in optionals:
        lines.append(f"{indent}#   {n}: {_field_descriptor(cls, n)}")
    return lines


def _render_class_fragment(
    kind: str, name: str, values: dict[str, Any], domain: str | None
) -> str:
    tag = _TAG_BY_KIND[kind]
    ann_name, cls = _BODY_ANNOTATION_BY_KIND[kind]
    required = list(_required_field_names(cls))
    if kind == "query-flow" and "returns" not in required:
        required.append("returns")

    defaults = _STATE_MACHINE_DEFAULTS if kind == "state-machine" else None
    body = _build_body_dict(cls, values, required, defaults=defaults)

    lines = [f"  {name}:", f"    instantiates: [{tag}]", "    annotations:"]
    lines.append(f"      scont:domain: {domain or '<DOMAIN>'}")
    lines.extend(_optional_comment_lines(cls, set(body.keys()), "      "))
    lines.append(f"      {ann_name}: >-")
    lines.append(_indent(json.dumps(body, indent=2), "        "))

    # Flows carry llm_prompt_hint as a sibling annotation (not in FlowBody).
    if kind in ("flow", "query-flow"):
        hint = values.get("llm_prompt_hint", "<LLM_PROMPT_HINT>")
        lines.append(f"      scont:llm_prompt_hint: {json.dumps(hint)}")
    return "\n".join(lines) + "\n"


def _render_entity_fragment(name: str, values: dict[str, Any], domain: str | None) -> str:
    description = values.get("description", "<DESCRIPTION>")
    lines = [
        f"  {name}:",
        f"    description: {json.dumps(description)}",
        "    annotations:",
        f"      scont:domain: {domain or '<DOMAIN>'}",
        "    attributes:",
        "      # Replace with real attributes. Range can be a primitive",
        "      # (string|integer|decimal|boolean|date) or another declared class/enum.",
        "      <attr_name>:",
        "        range: string",
        "        required: true",
    ]
    return "\n".join(lines) + "\n"


def _render_axiom_fragment(values: dict[str, Any]) -> str:
    required = list(_required_field_names(AxiomBody))
    body = _build_body_dict(AxiomBody, values, required)
    json_text = json.dumps(body, indent=2)
    optional_lines = [
        f"#   {n}: {_field_descriptor(AxiomBody, n)}"
        for n in _optional_field_names(AxiomBody)
        if n not in body
    ]
    out = [
        "# Axiom list-entry. Paste into a flow's scont:axioms annotation:",
        "#   scont:axioms: >-",
        "#     [ <entry>, <entry>, ... ]",
        json_text,
    ]
    if optional_lines:
        out.append("# Optional axiom fields:")
        out.extend(optional_lines)
    return "\n".join(out) + "\n"


def _template_for_kind(
    kind: str, name: str, values: dict[str, Any], domain: str | None
) -> str:
    if kind not in SCAFFOLD_KINDS:
        raise ScaffoldError(f"unknown kind: {kind!r}. Valid: {list(SCAFFOLD_KINDS)}")
    if kind == "entity":
        return _render_entity_fragment(name, values, domain)
    if kind == "axiom":
        return _render_axiom_fragment(values)
    return _render_class_fragment(kind, name, values, domain)


def _parse_extra_flags(tokens: list[str]) -> dict[str, str]:
    """Parse leftover `--kebab-field VALUE` / `--kebab-field=VALUE` tokens into
    a snake_case dict. Unknown tokens to `new` are treated as dynamic body
    fields; argparse's parse_known_args routes them here."""
    out: dict[str, str] = {}
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if not tok.startswith("--"):
            raise ScaffoldError(f"unexpected argument: {tok!r}")
        key_part = tok[2:]
        if "=" in key_part:
            key, _, val = key_part.partition("=")
            out[key.replace("-", "_")] = val
            i += 1
            continue
        if i + 1 >= len(tokens) or tokens[i + 1].startswith("--"):
            raise ScaffoldError(f"missing value for --{key_part}")
        out[key_part.replace("-", "_")] = tokens[i + 1]
        i += 2
    return out


def _interactive_prompt(kind: str, current: dict[str, Any]) -> dict[str, Any]:
    """Prompt stdin for each required body field not already supplied."""
    cls = _body_class_for_kind(kind)
    if cls is None:
        return current
    required = list(_required_field_names(cls))
    if kind == "query-flow" and "returns" not in required:
        required.append("returns")
    # Flow's llm_prompt_hint is a sibling annotation; still prompt for it
    # because strict validation warns when missing.
    if kind in ("flow", "query-flow") and "llm_prompt_hint" not in required:
        required.append("llm_prompt_hint")
    out = dict(current)
    for f in required:
        if f in out:
            continue
        if f in cls.model_fields:
            desc = _field_descriptor(cls, f)
        else:
            desc = "string"
        resp = input(f"{f} [{desc}]: ").strip()
        if resp:
            out[f] = resp
    return out


def cmd_new(args: argparse.Namespace) -> int:
    kind = args.kind
    try:
        extra = _parse_extra_flags(list(getattr(args, "_unknown", []) or []))
    except ScaffoldError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if getattr(args, "llm_prompt_hint", None) is not None:
        extra.setdefault("llm_prompt_hint", args.llm_prompt_hint)
    if kind == "axiom" and args.name:
        extra.setdefault("name", args.name)

    if args.interactive:
        try:
            extra = _interactive_prompt(kind, extra)
        except EOFError:
            pass

    try:
        fragment = _template_for_kind(kind, args.name, extra, args.domain)
    except ScaffoldError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(fragment, end="")
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

    df = sub.add_parser("diff", help="Compare two ontology YAMLs (files or git refs) and emit a structural delta.")
    df.add_argument(
        "path1",
        help="Earlier / base side. Either a disk path, a git ref (HEAD~1, main, SHA), or <ref>:<path>.",
    )
    df.add_argument(
        "path2",
        help="Later / compared side. Same accepted forms as path1.",
    )
    df.add_argument(
        "--file",
        help="File path within a git ref when the ref form is bare (e.g. --file supply_chain_demo.yaml). "
             "Ignored for disk-path args. Defaults to the other arg's basename if that arg is a disk path.",
    )
    df.add_argument(
        "--only",
        help=f"Comma-separated kinds to include. Valid: {','.join(DIFF_KINDS)}.",
    )
    df.add_argument("--json", action="store_true", help="Machine-readable output.")
    df.add_argument("--no-color", action="store_true", help="Disable ANSI colors in human output.")
    df.set_defaults(func=cmd_diff)

    new = sub.add_parser(
        "new",
        help="Scaffold a YAML fragment for a new ontology element (stdout only).",
    )
    new.add_argument("kind", choices=SCAFFOLD_KINDS, help="Element kind to scaffold.")
    new.add_argument("--name", required=True, help="Element name (axiom: name field within the body).")
    new.add_argument("--domain", help="scont:domain annotation value.")
    new.add_argument("--llm-prompt-hint", dest="llm_prompt_hint", help="llm_prompt_hint value.")
    new.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt stdin for each required body field not supplied via flags.",
    )
    new.set_defaults(func=cmd_new)

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
        "validate", "summary", "inspect", "query", "doc", "regen-bodies", "diff", "new"
    }:
        argv = ["summary", *argv]
    # `new` accepts dynamic --<field> VALUE pairs for body fields; route them
    # through parse_known_args. Every other subcommand rejects extras.
    args, unknown = parser.parse_known_args(argv)
    if unknown and getattr(args, "cmd", None) != "new":
        parser.error(f"unrecognized arguments: {' '.join(unknown)}")
    args._unknown = unknown
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
