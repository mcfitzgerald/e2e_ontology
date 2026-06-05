"""FastMCP wiring for the 7-O ontology knowledge-MCP + the `e2e-ontology-mcp`
entry point.

Deliberately thin: it binds `OntologyKnowledgeService` (in `core.py`) to MCP
tools (read/traverse the model) and resources (the model's source/docs/narrative).
Every handler just forwards to the core; no logic lives here. Mirrors the 7-S
split (`e2e_orchestrator/mcp/server.py`) — same house pattern, same
`mcp.server.fastmcp.FastMCP` API.

7-O is **read-only**: there are no write tools, no orchestrator, no event log.
Tools answer "what is the model and how is it connected"; resources hand back the
model's own text. Transport is stdio (there's no LLM here — it runs with no API
key).
"""
from __future__ import annotations

import argparse
import os
import sys

from mcp.server.fastmcp import FastMCP

from .core import OntologyKnowledgeService, UnknownNodeError

# ---------------------------------------------------------------------------
# Knowledge service + server. Built lazily so importing this module (entry point
# or tests) does not parse the ontology until first use.
# ---------------------------------------------------------------------------

_knowledge: OntologyKnowledgeService | None = None


def knowledge() -> OntologyKnowledgeService:
    global _knowledge
    if _knowledge is None:
        _knowledge = OntologyKnowledgeService()
    return _knowledge


def build_server(svc: OntologyKnowledgeService | None = None) -> FastMCP:
    """Construct a FastMCP server bound to `svc` (or the process knowledge
    service). Factored out so a test can bind a service and drive the server
    through an in-memory client session against the real Ontology Service."""
    if svc is not None:
        global _knowledge
        _knowledge = svc

    mcp = FastMCP("e2e-ontology-knowledge")

    # ---- tools: read + traverse the model -------------------------------

    @mcp.tool()
    def model_summary() -> dict:
        """Overview of the whole ontology: counts + the names of every role,
        flow, quantum (entity), event, playbook, and tool. The 'what's in this
        model' entry point."""
        return knowledge().model_summary()

    @mcp.tool()
    def read_role(role: str) -> dict:
        """A role's structural identity: the flows it touches (handoffs/queries,
        in/out), events emitted/observed, FSMs, playbooks anchored to it, and
        tools it may invoke. The full rendered agent prompt is `roleview://{role}`."""
        return knowledge().read_role(role)

    @mcp.tool()
    def read_flow(flow: str) -> dict:
        """A flow's definition: source/target roles, the quantum it carries, any
        return quantum, trigger event, lifecycle FSM, and constraining axioms."""
        return knowledge().read_flow(flow)

    @mcp.tool()
    def read_quantum(quantum: str) -> dict:
        """A quantum (entity class) schema: its attributes, plus the flows that
        carry/return it and the playbooks that consume it. Any entity name works."""
        return knowledge().read_quantum(quantum)

    @mcp.tool()
    def read_playbook(playbook: str) -> dict:
        """A playbook's structure: anchored role, trigger, input quantum,
        context-assembly query flows, decision criteria, the actions it may
        select, and what it always fires. (The criteria *weighting* is the agent's
        judgment — it lives nowhere in the model.)"""
        return knowledge().read_playbook(playbook)

    @mcp.tool()
    def traverse(node_id: str, relation: str | None = None) -> dict:
        """One hop along the ontology graph from any node (role/flow/quantum/
        event/playbook/tool), optionally filtered to a single `relation`. The atom
        of walking the model."""
        return knowledge().traverse(node_id, relation)

    @mcp.tool()
    def impact_analysis(start_id: str, change: str = "slip_one_week") -> dict:
        """Who/what is connected to `start_id` if it changes — the transitive
        structural closure (roles → flows → quanta → events → playbooks). Answers
        "if Megalomart's promo (a TradePromotion) slips a week, who's affected?".
        Returns an UNRANKED structural set (§2: ordering impact is the client's
        judgment, not the model's). `change` is an echoed context label only."""
        return knowledge().impact_analysis(start_id, change)

    @mcp.tool()
    def walk_flow_chain(start_flow: str) -> dict:
        """Read-only narration of the flow chain reachable from a starting flow by
        following the declared graph (quantum + target role → next handoffs).
        Purely ontological — no run, no scenario, no orchestrator."""
        return knowledge().walk_flow_chain(start_flow)

    # ---- resources: the model's own source / docs / narrative -----------

    @mcp.resource("ontology://source")
    def ontology_source() -> str:
        """The ontology YAML itself — the model."""
        return knowledge().ontology_source()

    @mcp.resource("narrative://demo")
    def narrative_demo() -> str:
        """The demo story (`demo_narrative.md`)."""
        return knowledge().narrative()

    @mcp.resource("roleview://{role}")
    def roleview(role: str) -> str:
        """`render_role_view(role).as_agent_prompt()` — the ontology-derived
        identity of any role, byte-identical to the orchestrator's LlmAgent
        instruction."""
        return knowledge().roleview(role)

    @mcp.resource("docs://{name}")
    def docs(name: str) -> str:
        """A design doc at the repo root (e.g. `agent_system_design.md`,
        `plan_of_attack.md`, `ontology_primer.md`)."""
        return knowledge().doc(name)

    return mcp


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="e2e-ontology-mcp",
        description="Read-the-model knowledge MCP over the Ontology Service (7-O).",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http", "sse"),
        default=os.environ.get("E2E_ONTOLOGY_MCP_TRANSPORT", "stdio"),
        help="MCP transport (default: stdio). There is no LLM here — runs with no API key.",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    server = build_server()
    server.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
