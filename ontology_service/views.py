"""Typed role-scoped views over the ontology, with format adapters at the edge.

`RoleView` is the resolved snapshot a single role's agent (or knowledge-worker
reading the same view) needs to know about itself: identity, the flows it sends
and receives, the events on its surface, the lifecycles its quanta live in.
Built once by `service.render_role_view`; consumed by the format adapters
(`as_agent_prompt`, `as_markdown`, `as_json`) without re-querying the ontology.

Pydantic everywhere so the typed object is also the wire format. Sub-models are
deliberately flat: agents reason over field names, not nested envelopes.

Order discipline: within each list, entries are sorted by `name` (or by a stable
key). The ontology declares no priority over flows, events, or FSMs; the render
must not invent one (§2 design rule — no policy in the world model).
"""
from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from .orientation import ORIENTATION


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AxiomSummary(_Base):
    """An axiom as presented to the agent. `nl` is authoritative for reasoning;
    `expr` is for the deterministic backbone, not for the LLM."""
    name: str
    scope: str            # "class" | "flow"
    severity: Optional[str]  # "blocking" | "warning" | "advisory" | None
    nl: str
    expr: Optional[str] = None
    message: Optional[str] = None
    on_failure_route_to: Optional[str] = None


class QuantumSlotSchema(_Base):
    """One slot on a quantum class — what fields the payload must carry.
    `range_kind` discriminates primitive (`string`/`integer`/...) vs. `class`
    (entity reference; pass as string id at the wire) vs. `enum` (bounded;
    permissible values are emitted inline so the LLM doesn't guess)."""
    name: str
    range: str
    range_kind: str       # "primitive" | "class" | "enum"
    required: bool
    multivalued: bool = False
    description: Optional[str] = None
    permissible_values: tuple[str, ...] = ()  # populated only when range_kind == "enum"


class QuantumSchema(_Base):
    """Slot schema for a quantum class, rendered into the agent prompt so the
    LLM knows the payload shape without guessing.

    Sourced from `SchemaView.class_induced_slots()`. Phase 1.5 add — Phase 2
    revealed that "the LLM guessed the field names and got lucky" is not a
    verified contract. The slot structure of a quantum is world model (§2):
    structural fact about what the action vocabulary carries, the same kind
    of declaration as `target_role` on a flow."""
    name: str
    description: Optional[str] = None
    slots: tuple[QuantumSlotSchema, ...]


class FlowSummary(_Base):
    """A flow as seen from a role's perspective. `returns` discriminates shape:
    present → query (request-response, source retains responsibility); absent →
    handoff (responsibility transfers).

    `quantum_schema` and `returns_schema` carry the slot schemas for the
    payload classes the flow names; they are how the LLM learns the payload
    shape without guessing."""
    name: str
    kind: str             # "information" | "material" | "cash"
    source_role: str
    target_role: str
    quantum: str
    trigger_event: Optional[str] = None
    lifecycle_ref: Optional[str] = None
    returns: Optional[str] = None
    domain: Optional[str] = None
    llm_prompt_hint: Optional[str] = None
    axioms: tuple[AxiomSummary, ...] = ()
    quantum_schema: Optional[QuantumSchema] = None
    returns_schema: Optional[QuantumSchema] = None


class EventSummary(_Base):
    """An event on the role's surface. `observed_by` names the producer role
    declared in the ontology; for `events_observed` from a target's vantage,
    `observed_by` will name the upstream producer."""
    name: str
    description: str
    observed_by: str
    llm_prompt_hint: str
    domain: Optional[str] = None


class TransitionSummary(_Base):
    from_state: str
    to_state: str
    trigger: Optional[str] = None
    guard: Optional[str] = None     # axiom name


class FSMSummary(_Base):
    """A state machine governing one of the role's quanta. `governs_flows`
    lists every flow the role touches that shares this lifecycle — multiple
    flows can share an FSM (e.g. `request_production` + `re_request_production`
    both run `ProductionRequestLifecycle`)."""
    name: str
    states: tuple[str, ...]
    initial: str
    terminal: tuple[str, ...]
    transitions: tuple[TransitionSummary, ...]
    governs_flows: tuple[str, ...]


class RoleIdentity(_Base):
    name: str
    domain: Optional[str]
    description: str
    llm_prompt_hint: str
    is_boundary: bool
    human_involvement: Optional[str]   # "required" | "conditional" | "autonomous" | None


class RoleView(BaseModel):
    """Format-agnostic snapshot of everything a role's agent needs to know
    about itself, resolved from the ontology. The same view feeds the
    transactional agent's system prompt, the knowledge-worker onboarding doc
    (via MCP), and the JSON envelope a tool chain consumes — only the adapter
    at the edge differs (`as_agent_prompt`, `as_markdown`, `as_json`)."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: RoleIdentity
    incoming_handoffs: tuple[FlowSummary, ...]
    outgoing_handoffs: tuple[FlowSummary, ...]
    incoming_queries: tuple[FlowSummary, ...]
    outgoing_queries: tuple[FlowSummary, ...]
    events_observed: tuple[EventSummary, ...]   # events that fire flows arriving here
    events_emitted: tuple[EventSummary, ...]    # events the role produces (observed_by == role)
    fsms_governing_my_quanta: tuple[FSMSummary, ...]

    # Phase 5 stubs — Playbook + Tool meta-constructs are not yet in scont_meta.yaml.
    # Rendered as empty sections so the prompt shape is stable across the upgrade.
    playbooks_anchored_to: tuple[Any, ...] = ()
    tools_available_to: tuple[Any, ...] = ()
    advisory_criteria: tuple[AxiomSummary, ...] = ()

    # ---- format adapters ---------------------------------------------------

    def as_json(self) -> dict[str, Any]:
        """Wire form. Pydantic JSON dump with enum values as strings."""
        return json.loads(self.model_dump_json())

    def as_markdown(self) -> str:
        """Human-readable role onboarding doc. Same content as the agent
        prompt, formatted with markdown headers + tables for human reading."""
        return _render_markdown(self)

    def as_agent_prompt(self) -> str:
        """LLM system prompt. Same content as the markdown view, formatted as
        plain text sections an instruction-tuned model parses well."""
        return _render_agent_prompt(self)


# ============================================================================
# Format adapters — pure functions over RoleView; no ontology access.
# ============================================================================


def _fmt_axioms(axioms: tuple[AxiomSummary, ...], indent: str = "    ") -> list[str]:
    if not axioms:
        return [f"{indent}(no axioms)"]
    lines = []
    for a in axioms:
        sev = a.severity or "unspecified"
        head = f"{indent}- {a.name} [{a.scope}, {sev}]"
        if a.on_failure_route_to:
            head += f" → on failure: {a.on_failure_route_to}"
        lines.append(head)
        lines.append(f"{indent}    {a.nl}")
    return lines


def _fmt_flow_line(f: FlowSummary, perspective: str) -> str:
    """`perspective` is 'incoming' or 'outgoing'; controls which side of the
    arrow is the counterparty."""
    if perspective == "incoming":
        arrow = f"from {f.source_role}"
    else:
        arrow = f"to {f.target_role}"
    parts = [f"- {f.name} ({f.kind}, {arrow}): quantum={f.quantum}"]
    if f.returns:
        parts.append(f"returns={f.returns}")
    if f.trigger_event:
        parts.append(f"trigger={f.trigger_event}")
    if f.lifecycle_ref:
        parts.append(f"lifecycle={f.lifecycle_ref}")
    return ", ".join(parts)


def _fmt_quantum_schema(qs: QuantumSchema, label: str, indent: str = "    ") -> list[str]:
    """Render a quantum or returns slot schema beneath a flow block. Format:

        {indent}{label} {ClassName} slots:
        {indent}  {slot}: {range}[{[]}] ({required|optional}) — {description}.{ class/enum hint}

    Class-typed slot ranges carry an inline "Pass the entity id as a string."
    note so the LLM does not embed nested objects unless the schema requires
    one. Enum slots emit their permissible values inline. Both nudges keep the
    LLM from guessing payload shape, which Phase 2 showed to be the dominant
    failure mode without this block."""
    lines = [f"{indent}{label} {qs.name} slots:"]
    sub_indent = indent + "  "
    for s in qs.slots:
        type_str = s.range + ("[]" if s.multivalued else "")
        req_str = "required" if s.required else "optional"
        line = f"{sub_indent}{s.name}: {type_str} ({req_str})"
        suffix: list[str] = []
        if s.description:
            # Descriptions are sometimes multi-line (folded scalars); normalize
            # whitespace so the rendered line stays single-line.
            desc = " ".join(s.description.split())
            suffix.append(desc.rstrip("."))
        if s.range_kind == "class":
            suffix.append("Pass the entity id as a string")
        elif s.range_kind == "enum" and s.permissible_values:
            suffix.append(f"Values: {', '.join(s.permissible_values)}")
        if suffix:
            line += " — " + ". ".join(suffix) + "."
        lines.append(line)
    return lines


def _render_section_flows(
    title: str, flows: tuple[FlowSummary, ...], perspective: str, empty: str
) -> list[str]:
    out = [f"## {title}", ""]
    if not flows:
        out.append(empty)
        out.append("")
        return out
    for f in flows:
        out.append(_fmt_flow_line(f, perspective))
        if f.llm_prompt_hint:
            out.append(f"    hint: {f.llm_prompt_hint.strip()}")
        if f.quantum_schema:
            out.extend(_fmt_quantum_schema(f.quantum_schema, "quantum"))
        if f.returns_schema:
            out.extend(_fmt_quantum_schema(f.returns_schema, "returns"))
        if f.axioms:
            out.append("    axioms:")
            out.extend(_fmt_axioms(f.axioms, indent="      "))
    out.append("")
    return out


def _render_section_events(title: str, events: tuple[EventSummary, ...], empty: str) -> list[str]:
    out = [f"## {title}", ""]
    if not events:
        out.append(empty)
        out.append("")
        return out
    for e in events:
        out.append(f"- {e.name} (observed_by={e.observed_by}): {e.description}")
    out.append("")
    return out


def _render_section_fsms(fsms: tuple[FSMSummary, ...]) -> list[str]:
    out = ["## Lifecycles governing my quanta", ""]
    if not fsms:
        out.append("(none — none of the flows I touch carry a lifecycle_ref)")
        out.append("")
        return out
    for sm in fsms:
        out.append(f"- {sm.name}")
        out.append(f"    states: {', '.join(sm.states)}")
        out.append(f"    initial: {sm.initial}")
        if sm.terminal:
            out.append(f"    terminal: {', '.join(sm.terminal)}")
        out.append(f"    governs flows I touch: {', '.join(sm.governs_flows)}")
        if sm.transitions:
            out.append("    transitions:")
            for t in sm.transitions:
                line = f"      {t.from_state} → {t.to_state}"
                if t.trigger:
                    line += f"  on={t.trigger}"
                if t.guard:
                    line += f"  guard={t.guard}"
                out.append(line)
    out.append("")
    return out


def _render_tool_kit(view: RoleView) -> list[str]:
    """The fixed seven-tool kit (§7), wired to this role's surface. Phase 1
    stubs out `call_tool` because the Tool meta-construct lands in Phase 5."""
    out = ["## Your tool kit", ""]
    out.append("You have a fixed set of tools regardless of role. The mapping to your surface:")
    out.append("")
    out.append("- read_ontology(query): introspect the ontology at any time.")
    out.append(
        f"- emit_event(name, payload): events you may emit "
        f"({_join_names(view.events_emitted) or '—'})."
    )
    out.append(
        f"- handoff(flow, quantum): your outgoing handoffs "
        f"({_join_names(view.outgoing_handoffs) or '—'}). Orchestrator validates "
        "the quantum and evaluates axioms before propagating."
    )
    out.append(
        f"- query(flow, query_quantum): your outgoing queries "
        f"({_join_names(view.outgoing_queries) or '—'}). Awaits the typed response."
    )
    out.append(
        f"- advance_fsm(quantum, trigger): lifecycle transition on a quantum you own "
        f"({_join_names(view.fsms_governing_my_quanta) or '—'}). "
        "Orchestrator checks the guard and may route via `on_failure_route_to`."
    )
    out.append(
        "- call_tool(name, input): invoke a declared specialist tool. "
        "(No tools are declared yet — the Tool meta-construct lands in Phase 5.)"
    )
    hi = view.identity.human_involvement
    if hi == "autonomous":
        out.append(
            "- surface_decision(...): present, but your role is declared autonomous; "
            "the orchestrator's policy decides whether it ever fires."
        )
    elif hi in ("required", "conditional"):
        out.append(
            f"- surface_decision(...): your role has human_involvement={hi}; "
            "the orchestrator owns thresholds and mechanisms for when a human is engaged."
        )
    else:
        out.append(
            "- surface_decision(...): your role's human_involvement is unspecified; "
            "the orchestrator's policy decides if and when a human is engaged."
        )
    out.append("")
    return out


def _join_names(items: tuple[Any, ...]) -> str:
    return ", ".join(getattr(i, "name", str(i)) for i in items)


def _render_identity(view: RoleView, *, header: str = "# Role") -> list[str]:
    ident = view.identity
    out = [f"{header}: {ident.name}", ""]
    if ident.domain:
        out.append(f"domain: {ident.domain}")
    out.append(f"is_boundary: {str(ident.is_boundary).lower()}")
    out.append(f"human_involvement: {ident.human_involvement or 'unspecified'}")
    out.append("")
    out.append(ident.description.strip())
    if ident.llm_prompt_hint:
        out.append("")
        out.append(ident.llm_prompt_hint.strip())
    out.append("")
    return out


def _render_markdown(view: RoleView) -> str:
    # Domain-agnostic system orientation prepended verbatim to every role's
    # view (§15.4 — "one render function, multiple consumers"). The preface
    # is identical across roles by design; if you find yourself wanting to
    # vary it per role, that belongs in the role-specific section below.
    out: list[str] = [ORIENTATION.rstrip(), ""]
    out.extend(_render_identity(view, header="# Role"))
    out.extend(_render_section_flows(
        "Incoming handoffs (what arrives at me)", view.incoming_handoffs,
        perspective="incoming",
        empty="(none — no other role hands off to me)",
    ))
    out.extend(_render_section_flows(
        "Outgoing handoffs (what I send)", view.outgoing_handoffs,
        perspective="outgoing",
        empty="(none — I don't transfer responsibility to anyone)",
    ))
    out.extend(_render_section_flows(
        "Incoming queries (what others may ask of me)", view.incoming_queries,
        perspective="incoming",
        empty="(none — no role queries me)",
    ))
    out.extend(_render_section_flows(
        "Outgoing queries (what I may ask of others)", view.outgoing_queries,
        perspective="outgoing",
        empty="(none — I do not query other roles)",
    ))
    out.extend(_render_section_events(
        "Events that arrive at me (trigger my incoming flows)", view.events_observed,
        empty="(none — no incoming flow carries a trigger_event)",
    ))
    out.extend(_render_section_events(
        "Events I produce (observed_by me)", view.events_emitted,
        empty="(none — I produce no events)",
    ))
    out.extend(_render_section_fsms(view.fsms_governing_my_quanta))
    out.extend(_render_tool_kit(view))
    # Phase 5 stubs.
    out.append("## Playbooks anchored to me")
    out.append("")
    out.append("(none — Playbook meta-construct lands in Phase 5.)")
    out.append("")
    out.append("## Specialist tools I can call")
    out.append("")
    out.append("(none — Tool meta-construct lands in Phase 5.)")
    out.append("")
    out.append("## Advisory criteria (named viability inputs)")
    out.append("")
    if view.advisory_criteria:
        for a in view.advisory_criteria:
            out.append(f"- {a.name}: {a.nl}")
    else:
        out.append("(none — no advisory axioms attached to flows I touch.)")
    out.append("")
    return "\n".join(out).rstrip() + "\n"


def _render_agent_prompt(view: RoleView) -> str:
    """Plain-text system prompt. Identical content to the markdown view; only
    the framing changes — no markdown headers, just labelled sections, so that
    an instruction-tuned model doesn't confuse `##` with content boundaries.

    The orientation preface flows through `_render_markdown` as plain text,
    so this adapter doesn't need to know about it — the header transform
    below leaves non-header lines untouched."""
    md = _render_markdown(view)
    # Demote markdown headers to plain labels with a separator rule so
    # section boundaries remain visible to the model after `## ` is stripped.
    lines: list[str] = []
    for line in md.splitlines():
        if line.startswith("# Role: "):
            lines.append("ROLE: " + line[len("# Role: "):])
        elif line.startswith("## "):
            label = line[len("## "):].upper()
            lines.append("---")
            lines.append(label)
        else:
            lines.append(line)
    return "\n".join(lines).rstrip() + "\n"
