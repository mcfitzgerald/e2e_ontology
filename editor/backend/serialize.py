"""
Serialize the resolved Ontology into a lean JSON shape for the frontend.

The frontend never needs the SchemaView or raw Pydantic bodies — it just
needs flat records it can feed into React Flow and panels. This module
owns that flattening.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from exploder import (  # type: ignore[import-not-found]
    Ontology,
    ResolvedEntity,
    ResolvedEvent,
    ResolvedFlow,
    ResolvedRole,
    ResolvedStateMachine,
    ValidationIssue,
)
from scont_bodies import AxiomBody  # type: ignore[import-not-found]


def serialize_ontology(ontology: Ontology) -> dict[str, Any]:
    return {
        "path": str(ontology.path),
        "roles": [_role(r) for r in ontology.roles.values()],
        "events": [_event(e) for e in ontology.events.values()],
        "flows": [_flow(f) for f in ontology.flows.values()],
        "state_machines": [_state_machine(s) for s in ontology.state_machines.values()],
        "entities": [_entity(e) for e in ontology.entities.values()],
        "warnings": [_warning(w) for w in ontology.warnings],
        "summary": {
            "roles": len(ontology.roles),
            "events": len(ontology.events),
            "flows": len(ontology.flows),
            "state_machines": len(ontology.state_machines),
            "entities": len(ontology.entities),
            "warnings": len(ontology.warnings),
        },
    }


def _role(r: ResolvedRole) -> dict[str, Any]:
    b = r.body
    return {
        "name": r.name,
        "domain": r.domain,
        "subdomain": r.subdomain,
        "description": b.description,
        "llm_prompt_hint": b.llm_prompt_hint,
        "is_boundary": bool(b.is_boundary),
        "human_involvement": _enum(b.human_involvement),
        "can_be_played_by": b.can_be_played_by,
    }


def _event(e: ResolvedEvent) -> dict[str, Any]:
    b = e.body
    return {
        "name": e.name,
        "domain": e.domain,
        "subdomain": e.subdomain,
        "description": b.description,
        "observed_by": b.observed_by,
        "llm_prompt_hint": b.llm_prompt_hint,
    }


def _flow(f: ResolvedFlow) -> dict[str, Any]:
    b = f.body
    return {
        "name": f.name,
        "kind": f.kind,
        "domain": f.domain,
        "subdomain": f.subdomain,
        "source_role": b.source_role,
        "target_role": b.target_role,
        "quantum": b.quantum,
        "trigger_event": b.trigger_event,
        "lifecycle_ref": b.lifecycle_ref,
        "returns": b.returns,
        "llm_prompt_hint": f.llm_prompt_hint,
        "axioms": [_axiom(a) for a in f.axioms],
    }


def _state_machine(s: ResolvedStateMachine) -> dict[str, Any]:
    b = s.body
    return {
        "name": s.name,
        "domain": s.domain,
        "subdomain": s.subdomain,
        "states": list(b.states),
        "initial": b.initial,
        "terminal": list(b.terminal or []),
        "transitions": [
            {
                "from_state": t.from_state,
                "to_state": t.to_state,
                "trigger": t.trigger,
                "guard": t.guard,
            }
            for t in b.transitions
        ],
    }


def _entity(e: ResolvedEntity) -> dict[str, Any]:
    return {
        "name": e.name,
        "domain": e.domain,
        "subdomain": e.subdomain,
        "description": e.description,
        "attributes": sorted(e.attributes.keys()),
        "rule_count": len(e.rules),
        "metrics": [m.name for m in e.metrics],
    }


def _axiom(a: AxiomBody) -> dict[str, Any]:
    return {
        "name": a.name,
        "scope": _enum(a.scope),
        "severity": _enum(a.severity),
        "nl": a.nl,
        "expr": a.expr,
        "message": a.message,
        "on_failure_route_to": a.on_failure_route_to,
        "references": {
            "metrics": list(a.references.metrics or []) if a.references else [],
            "classes": list(a.references.classes or []) if a.references else [],
            "flows": list(a.references.flows or []) if a.references else [],
            "events": list(a.references.events or []) if a.references else [],
        }
        if a.references
        else None,
    }


def _warning(w: ValidationIssue) -> dict[str, Any]:
    return {
        "level": w.level,
        "element": w.element,
        "field": w.field,
        "message": w.message,
    }


def _enum(value: Any) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)
