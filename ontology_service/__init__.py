"""Ontology Service — role-scoped query API + format-agnostic role-view render.

Phase 1 deliverable. Sits between `exploder.Ontology` (raw resolved object
model) and downstream consumers (transactional agent prompts, knowledge-worker
onboarding, MCP responses). See `plan_of_attack.md` §1 and
`agent_system_design.md` §5 + §15.4.
"""
from .service import OntologyService, UnknownRoleError
from .views import (
    AxiomSummary,
    EventSummary,
    FlowSummary,
    FSMSummary,
    QuantumSchema,
    QuantumSlotSchema,
    RoleIdentity,
    RoleView,
    TransitionSummary,
)

__all__ = [
    "OntologyService",
    "UnknownRoleError",
    "RoleView",
    "RoleIdentity",
    "FlowSummary",
    "EventSummary",
    "FSMSummary",
    "TransitionSummary",
    "AxiomSummary",
    "QuantumSchema",
    "QuantumSlotSchema",
]
