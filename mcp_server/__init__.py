"""7-O — the ontology knowledge-MCP (read-the-model).

A read-only MCP surface over the **Ontology Service**: read and traverse the
*structure* of the supply-chain model (roles, flows, quanta, events, playbooks,
tools) and project its source/docs/narrative. The interactive form of the CSCO's
Q1 answer — *"what is the ontology, and is it legible?"*: ask it.

Distinct from 7-S (the orchestrator front door, `e2e_orchestrator/mcp/`): 7-S
*drives the system* (ingress + read a run's event log); 7-O *reads the model*.
7-O reuses none of 7-S's ingress — it wraps the Ontology Service, not the
orchestrator. See `briefings/seed-phase-B-ontology-knowledge-mcp.md`.
"""
from .core import OntologyKnowledgeService, UnknownNodeError

__all__ = ["OntologyKnowledgeService", "UnknownNodeError"]
