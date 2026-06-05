"""Transport-agnostic logic for the 7-O ontology knowledge-MCP — read-the-model.

`server.py` binds these methods to FastMCP tools/resources; the tests call them
directly against the *real* Ontology Service (not mocks), which is why the logic
lives here rather than inside decorated handlers. This mirrors the 7-S split
exactly (`e2e_orchestrator/mcp/{core,server}.py`) — the house pattern.

What this is (and is NOT):

- **7-O wraps the Ontology Service only** — `render_role_view`, the schema, the
  roles/flows/quanta/events/playbooks/tools graph. It reads/traverses the
  *structure of the model*. It is the interactive form of the CSCO's Q1 answer:
  *"what is the ontology, and is it legible?"* — ask it questions.
- It is **NOT** 7-S (the orchestrator front door). It holds **no orchestrator, no
  event log, no agent dispatch, no scenario registry** — reusing none of 7-S's
  ingress code. It never runs anything; it projects the world model.

§2 (structure, not policy). The ontology has no policy fields, so traversal
surfaces *structure* — facts, relationships, action vocabulary — never ranking,
preference, or score. `impact_analysis` returns the **structural closure** (the
reachable set), deliberately UNORDERED beyond name-sorting: "most affected first"
would be policy. The client (an LLM) reasons over the set; we don't rank it.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any

from ontology_service import (
    SUPPLY_CHAIN_DEMO_YAML,
    OntologyService,
    UnknownRoleError,
)
from ontology_service.paths import _REPO_ROOT


class UnknownNodeError(KeyError):
    """No ontology element (role/flow/quantum/event/playbook/tool) has that name."""


# The structural node kinds 7-O traverses. A "quantum" is an entity class used as
# a flow's payload; we keep the ontology's own word "entity" for the node kind and
# expose read_quantum as the consumer-facing alias.
_KINDS = ("role", "flow", "entity", "event", "playbook", "tool", "state_machine")


class OntologyKnowledgeService:
    """The Ontology Service presented as a read/traverse surface. Holds no
    domain knowledge and no per-element code: every method is generic over the
    ontology graph — no `if role == ...`, no enumerated names."""

    def __init__(self, ontology_yaml: Path | None = None):
        self._service = OntologyService.load(str(ontology_yaml or SUPPLY_CHAIN_DEMO_YAML))
        self._ont = self._service.ontology

    @property
    def service(self) -> OntologyService:
        return self._service

    # ---- model overview --------------------------------------------------

    def model_summary(self) -> dict[str, Any]:
        """The whole-model overview — counts + the names of every element, the
        'what's in this ontology' entry point. Pure projection of the resolved
        model."""
        o = self._ont
        return {
            "path": str(o.path),
            "counts": {
                "roles": len(o.roles),
                "flows": len(o.flows),
                "entities": len(o.entities),
                "events": len(o.events),
                "playbooks": len(o.playbooks),
                "tools": len(o.tools),
                "state_machines": len(o.state_machines),
                "enums": len(o.enums),
            },
            "roles": sorted(o.roles),
            "boundary_roles": sorted(r.name for r in o.list_boundary_roles()),
            "flows": sorted(o.flows),
            "entities": sorted(o.entities),
            "events": sorted(o.events),
            "playbooks": sorted(o.playbooks),
            "tools": sorted(o.tools),
        }

    # ---- read-the-element ------------------------------------------------

    def read_role(self, role: str) -> dict[str, Any]:
        """A role's structural identity: who it is, the flows it touches (in/out,
        handoffs/queries), events it emits/observes, FSMs it drives, playbooks
        anchored to it, tools it may invoke. The full *rendered* agent prompt is
        the `roleview://{role}` resource; this is the machine-readable shape."""
        r = self._ont.get_role(role)
        if r is None:
            raise UnknownNodeError(f"unknown role: {role!r}")
        svc = self._service
        return {
            "kind": "role",
            "name": r.name,
            "description": r.body.description,
            "is_boundary": bool(r.body.is_boundary),
            "human_involvement": r.body.human_involvement,
            "domain": r.domain,
            "subdomain": r.subdomain,
            "incoming_handoffs": [f.name for f in svc.incoming_handoffs(role)],
            "outgoing_handoffs": [f.name for f in svc.outgoing_handoffs(role)],
            "incoming_queries": [f.name for f in svc.incoming_queries(role)],
            "outgoing_queries": [f.name for f in svc.outgoing_queries(role)],
            "events_emitted": [e.name for e in svc.events_emitted(role)],
            "events_observed": [e.name for e in svc.events_observed(role)],
            "fsms": [m.name for m in svc.fsms_for_role(role)],
            "playbooks": [p.name for p in svc.playbooks_anchored_to(role)],
            "tools": [t.name for t in svc.tools_available_to(role)],
        }

    def read_flow(self, flow: str) -> dict[str, Any]:
        """A flow's definition: source/target roles, the quantum it carries (and
        any return quantum), trigger event, lifecycle FSM, and the axioms that
        constrain it."""
        f = self._ont.get_flow(flow)
        if f is None:
            raise UnknownNodeError(f"unknown flow: {flow!r}")
        b = f.body
        return {
            "kind": "flow",
            "name": f.name,
            "flow_kind": f.kind,
            "source_role": b.source_role,
            "target_role": b.target_role,
            "quantum": b.quantum,
            "returns": b.returns,
            "trigger_event": b.trigger_event,
            "lifecycle_ref": b.lifecycle_ref,
            "axioms": [a.name for a in f.axioms],
            "llm_prompt_hint": f.llm_prompt_hint,
            "domain": f.domain,
        }

    def read_quantum(self, quantum: str) -> dict[str, Any]:
        """A quantum (entity class) schema: its attributes + the flows that carry
        or return it and the playbooks that consume it. 'Quantum' is the
        consumer-facing word for an entity used as a flow payload; any entity
        name resolves."""
        e = self._ont.get_entity(quantum)
        if e is None:
            raise UnknownNodeError(f"unknown quantum/entity: {quantum!r}")
        carried_by = [f.name for f in self._ont.flows.values() if f.body.quantum == quantum]
        returned_by = [f.name for f in self._ont.flows.values() if f.body.returns == quantum]
        consumed_by = [p.name for p in self._ont.playbooks.values() if p.body.input_quantum == quantum]
        return {
            "kind": "entity",
            "name": e.name,
            "description": e.description,
            "attributes": {
                k: {kk: vv for kk, vv in (v or {}).items() if kk in ("range", "required", "description")}
                for k, v in e.attributes.items()
            },
            "metrics": [m.name for m in e.metrics],
            "carried_by_flows": sorted(carried_by),
            "returned_by_flows": sorted(returned_by),
            "consumed_by_playbooks": sorted(consumed_by),
        }

    def read_playbook(self, playbook: str) -> dict[str, Any]:
        """A playbook's structure: the role it's anchored to, what triggers it,
        the input quantum, its context-assembly query flows, the decision
        criteria it weighs, the actions it may select, and what it always fires.
        The decision *criteria* are surfaced; the *weighting* is the agent's
        judgment and lives nowhere in the model (§2)."""
        p = self._ont.get_playbook(playbook)
        if p is None:
            raise UnknownNodeError(f"unknown playbook: {playbook!r}")
        b = p.body
        decision = b.decision
        return {
            "kind": "playbook",
            "name": p.name,
            "role": b.role,
            "triggered_by": b.triggered_by,
            "input_quantum": b.input_quantum,
            "context_assembly": [s.flow for s in (b.context_assembly or [])],
            "criteria_refs": list(decision.criteria_refs) if decision else [],
            "selects_one_of": list(decision.selects_one_of) if decision else [],
            "always_fires": list(getattr(b, "always_fires", []) or []),
            "llm_prompt_hint": p.llm_prompt_hint,
        }

    # ---- traverse + impact ----------------------------------------------

    def classify(self, node_id: str) -> str:
        """Which kind of node is this name? Raises UnknownNodeError if it matches
        nothing. Generic — no enumerated names."""
        o = self._ont
        if node_id in o.roles:
            return "role"
        if node_id in o.flows:
            return "flow"
        if node_id in o.entities:
            return "entity"
        if node_id in o.events:
            return "event"
        if node_id in o.playbooks:
            return "playbook"
        if node_id in o.tools:
            return "tool"
        if node_id in o.state_machines:
            return "state_machine"
        raise UnknownNodeError(f"unknown ontology element: {node_id!r}")

    def neighbors(self, node_id: str) -> list[dict[str, str]]:
        """The structural neighbors of a node — one hop along the ontology graph.
        Each edge is {relation, kind, id}. Generic adjacency; the same function
        backs traverse() and impact_analysis()."""
        kind = self.classify(node_id)
        o = self._ont
        edges: list[dict[str, str]] = []

        def add(relation: str, nkind: str, nid: str | None) -> None:
            if nid:
                edges.append({"relation": relation, "kind": nkind, "id": nid})

        if kind == "role":
            for f in o.flows.values():
                if f.body.source_role == node_id:
                    add("emits_flow", "flow", f.name)
                if f.body.target_role == node_id:
                    add("receives_flow", "flow", f.name)
            for p in o.playbooks_for_role(node_id):
                add("runs_playbook", "playbook", p.name)
            for t in o.tools_for_role(node_id):
                add("uses_tool", "tool", t.name)
        elif kind == "flow":
            f = o.get_flow(node_id)
            b = f.body
            add("from_role", "role", b.source_role)
            add("to_role", "role", b.target_role)
            add("carries", "entity", b.quantum)
            add("returns", "entity", b.returns)
            add("triggered_by", "event", b.trigger_event)
        elif kind == "entity":
            for f in o.flows.values():
                if f.body.quantum == node_id:
                    add("carried_by", "flow", f.name)
                if f.body.returns == node_id:
                    add("returned_by", "flow", f.name)
            for p in o.playbooks.values():
                if p.body.input_quantum == node_id:
                    add("input_to_playbook", "playbook", p.name)
        elif kind == "event":
            for f in o.flows.values():
                if f.body.trigger_event == node_id:
                    add("triggers_flow", "flow", f.name)
        elif kind == "playbook":
            p = o.get_playbook(node_id)
            b = p.body
            add("owned_by", "role", b.role)
            add("triggered_by", "event", b.triggered_by)
            add("consumes", "entity", b.input_quantum)
            for s in (b.context_assembly or []):
                add("assembles_via", "flow", s.flow)
            if b.decision:
                for sel in b.decision.selects_one_of:
                    add("can_select", "flow", sel)
        elif kind == "tool":
            t = o.get_tool(node_id)
            b = t.body
            for r in (b.available_to or []):
                add("available_to", "role", r)
            add("reads", "entity", b.input_class)
            add("produces", "entity", b.output_class)
        elif kind == "state_machine":
            for f in o.flows.values():
                if f.body.lifecycle_ref == node_id:
                    add("governs_flow", "flow", f.name)

        # Deterministic order; de-duplicate (a flow can be both carries+returns).
        seen = set()
        out = []
        for e in sorted(edges, key=lambda e: (e["relation"], e["id"])):
            key = (e["relation"], e["kind"], e["id"])
            if key not in seen:
                seen.add(key)
                out.append(e)
        return out

    def traverse(self, node_id: str, relation: str | None = None) -> dict[str, Any]:
        """One-hop structural neighbors of `node_id`, optionally filtered to a
        single `relation`. The atom of 'walk the model'."""
        kind = self.classify(node_id)
        edges = self.neighbors(node_id)
        if relation is not None:
            edges = [e for e in edges if e["relation"] == relation]
        return {"node": node_id, "kind": kind, "neighbors": edges}

    def impact_analysis(
        self, start_id: str, change: str = "slip_one_week", max_depth: int = 4
    ) -> dict[str, Any]:
        """THE HEADLINE. The transitive structural closure reachable from
        `start_id` — *'if this changes, what's connected to it?'* Answers
        questions like *"if Megalomart's promo (a TradePromotion) slips a week,
        who's affected?"* by walking roles → flows → quanta → events → playbooks
        from the starting element.

        `change` is an echoed label for the client's context; it does NOT affect
        the result. The closure is returned as a STRUCTURAL SET grouped by kind,
        deliberately unranked — ordering impact ('most affected first') would be a
        §2 policy judgment, which is the client LLM's job, not the model's.
        """
        start_kind = self.classify(start_id)
        visited: dict[str, str] = {start_id: start_kind}
        # shortest structural path start -> node, for explainability (not ranking)
        paths: dict[str, list[dict[str, str]]] = {start_id: []}
        q: deque[tuple[str, int]] = deque([(start_id, 0)])
        edges_walked: list[dict[str, str]] = []

        while q:
            node, depth = q.popleft()
            if depth >= max_depth:
                continue
            for e in self.neighbors(node):
                nid = e["id"]
                edge = {"from": node, **e}
                if nid not in visited:
                    visited[nid] = e["kind"]
                    paths[nid] = paths[node] + [edge]
                    edges_walked.append(edge)
                    q.append((nid, depth + 1))

        affected: dict[str, list[str]] = {}
        for nid, k in visited.items():
            if nid == start_id:
                continue
            affected.setdefault(k, []).append(nid)
        for k in affected:
            affected[k].sort()

        return {
            "start": start_id,
            "start_kind": start_kind,
            "change": change,
            "max_depth": max_depth,
            "affected": affected,
            "affected_count": sum(len(v) for v in affected.values()),
            # paths give the structural reason each element is reachable — for
            # the client to explain "why", NOT a ranking.
            "paths": {nid: paths[nid] for nid in sorted(paths) if nid != start_id},
            "note": (
                "Structural closure only — unranked by design (§2). Ordering or "
                "scoring impact is the client's judgment, not the model's."
            ),
        }

    def walk_flow_chain(self, start_flow: str, max_steps: int = 12) -> dict[str, Any]:
        """Read-only narration of the flow chain reachable from a starting flow by
        following the declared graph: a flow's quantum + target role lead to the
        next flows that role emits, and any trigger-event links. Purely
        ontological — NO orchestrator, no scenario registry, no run. This is the
        '*what would happen, structurally*' walk (the seed's `walk_scenario`,
        recast as model-only since scenarios live in the orchestrator, not here)."""
        if self._ont.get_flow(start_flow) is None:
            raise UnknownNodeError(f"unknown flow: {start_flow!r}")
        steps: list[dict[str, Any]] = []
        seen: set[str] = set()
        frontier: deque[str] = deque([start_flow])
        while frontier and len(steps) < max_steps:
            flow = frontier.popleft()
            if flow in seen:
                continue
            seen.add(flow)
            f = self._ont.get_flow(flow)
            if f is None:
                continue
            b = f.body
            steps.append({
                "flow": flow,
                "from": b.source_role,
                "to": b.target_role,
                "carries": b.quantum,
                "returns": b.returns,
                "triggered_by": b.trigger_event,
            })
            # next: handoffs the target role emits (responsibility moves forward)
            for nf in self._ont.list_flows_where(source_role=b.target_role):
                if nf.name not in seen and not nf.body.returns:  # follow handoffs, not queries
                    frontier.append(nf.name)
        return {"start_flow": start_flow, "steps": steps, "truncated": len(steps) >= max_steps}

    # ---- resources (read-only projections) -------------------------------

    def ontology_source(self) -> str:
        """`ontology://source` — the ontology YAML itself (the model)."""
        return Path(self._ont.path).read_text(encoding="utf-8")

    def narrative(self) -> str:
        """`narrative://demo` — the demo story (`demo_narrative.md`)."""
        return _read_repo_doc("demo_narrative.md")

    def roleview(self, role: str) -> str:
        """`roleview://{role}` — `render_role_view(role).as_agent_prompt()`, the
        ontology-derived identity, byte-identical to what the orchestrator binds
        as an LlmAgent instruction."""
        try:
            return self._service.render_role_view(role).as_agent_prompt()
        except UnknownRoleError as exc:
            raise UnknownNodeError(f"unknown role: {role!r}") from exc

    def doc(self, name: str) -> str:
        """`docs://{name}` — a design doc at the repo root (e.g.
        `agent_system_design.md`). Path-guarded to the repo root; no traversal."""
        return _read_repo_doc(name)


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------


def _read_repo_doc(name: str) -> str:
    """Read a doc/narrative file from the ontology repo root. Guards against path
    traversal: only a bare filename under the repo root is allowed."""
    if "/" in name or "\\" in name or name.startswith("."):
        raise UnknownNodeError(f"invalid doc name: {name!r}")
    path = Path(_REPO_ROOT) / name
    if not path.is_file():
        raise UnknownNodeError(f"no such doc at repo root: {name!r}")
    return path.read_text(encoding="utf-8")
