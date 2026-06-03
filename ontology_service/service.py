"""Ontology Service — role-scoped queryable API over a loaded Ontology.

Wraps `exploder.load_ontology()` and `exploder.Ontology` with role-centric
lookups: what flows arrive at me, what I emit, what I can query, what events
hit me, what FSMs govern my quanta. The Service does not assemble the
rendered view directly; it returns resolved ontology objects. `render_role_view`
composes them into a typed `RoleView` snapshot, which the format adapters at
the view-side edge convert to prompt / markdown / JSON.

Design discipline (§2):
  - Order: lists sorted by `name` (or stable key). No priority, no ranking.
    The ontology declares no preference; the renderer must not invent one.
  - Read-only: the Ontology is loaded once at construction; nothing mutates.
  - Resolution boundary: this module hides `SchemaView` from callers. The
    renderer talks to the Service; callers needing raw LinkML access go via
    `exploder.load_ontology()` themselves.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from exploder import (
    AxiomBody,
    Ontology,
    ResolvedEvent,
    ResolvedFlow,
    ResolvedPlaybook,
    ResolvedRole,
    ResolvedStateMachine,
    ResolvedTool,
    load_ontology,
)
from linkml_runtime import SchemaView

from .views import (
    AxiomSummary,
    EventSummary,
    FlowSummary,
    FSMSummary,
    PlaybookCriterionView,
    PlaybookEffectView,
    PlaybookInputBindingView,
    PlaybookQueryStepView,
    PlaybookResolutionView,
    PlaybookSummary,
    QuantumSchema,
    QuantumSlotSchema,
    RoleIdentity,
    RoleView,
    ToolSummary,
    TransitionSummary,
)


class UnknownRoleError(KeyError):
    """Raised when a role lookup fails. Kept distinct from KeyError so callers
    can route to a friendly error without swallowing genuine bugs."""


class OntologyService:
    """Role-scoped query layer over a loaded `Ontology`. Construct via
    `OntologyService.load(path)` for normal use, or pass an already-loaded
    `Ontology` directly for tests that build fixtures in memory."""

    def __init__(self, ontology: Ontology):
        self._ont = ontology

    @classmethod
    def load(cls, path: str | Path) -> "OntologyService":
        return cls(load_ontology(path))

    @property
    def ontology(self) -> Ontology:
        """Escape hatch for callers that need the raw resolved ontology
        (diff, summary, lint, etc.). The Service stays read-only either way."""
        return self._ont

    # ---- existence + identity ---------------------------------------------

    def get_role(self, name: str) -> ResolvedRole | None:
        return self._ont.get_role(name)

    def _require_role(self, name: str) -> ResolvedRole:
        role = self.get_role(name)
        if role is None:
            raise UnknownRoleError(name)
        return role

    def human_involvement(self, role: str) -> str | None:
        """`required` | `conditional` | `autonomous` | None when unspecified.
        Returns the raw enum value (Pydantic enum value, not the enum)."""
        body = self._require_role(role).body
        hi = body.human_involvement
        return hi.value if hi is not None and hasattr(hi, "value") else hi

    # ---- flow-side queries -------------------------------------------------

    def incoming_handoffs(self, role: str) -> list[ResolvedFlow]:
        """Flows targeting this role with no `returns:` — handoffs where
        responsibility transfers in."""
        self._require_role(role)
        out = [
            f for f in self._ont.flows.values()
            if f.body.target_role == role and not f.body.returns
        ]
        return _by_name(out)

    def outgoing_handoffs(self, role: str) -> list[ResolvedFlow]:
        """Flows sourced from this role with no `returns:`."""
        self._require_role(role)
        out = [
            f for f in self._ont.flows.values()
            if f.body.source_role == role and not f.body.returns
        ]
        return _by_name(out)

    def incoming_queries(self, role: str) -> list[ResolvedFlow]:
        """Query flows targeting this role — questions the agent may need to
        answer. `returns:` set means the source retains responsibility; this
        role responds and returns a typed answer."""
        self._require_role(role)
        out = [
            f for f in self._ont.flows.values()
            if f.body.target_role == role and f.body.returns
        ]
        return _by_name(out)

    def outgoing_queries(self, role: str) -> list[ResolvedFlow]:
        """Query flows sourced from this role."""
        self._require_role(role)
        out = [
            f for f in self._ont.flows.values()
            if f.body.source_role == role and f.body.returns
        ]
        return _by_name(out)

    def _flows_touching(self, role: str) -> list[ResolvedFlow]:
        """All flows where this role is either source or target. Used to
        derive the FSM set and the event surface."""
        out = [
            f for f in self._ont.flows.values()
            if f.body.source_role == role or f.body.target_role == role
        ]
        return _by_name(out)

    # ---- event surface -----------------------------------------------------

    def events_observed(self, role: str) -> list[ResolvedEvent]:
        """Events that fire flows arriving at this role — events the agent
        reacts to. De-duplicated across multiple incoming flows that may
        share a trigger."""
        self._require_role(role)
        names: set[str] = set()
        for f in self._ont.flows.values():
            if f.body.target_role != role:
                continue
            if f.body.trigger_event:
                names.add(f.body.trigger_event)
        events = [self._ont.events[n] for n in names if n in self._ont.events]
        return _by_name(events)

    def events_emitted(self, role: str) -> list[ResolvedEvent]:
        """Events whose `observed_by` is this role — events the role
        produces / raises onto the bus."""
        self._require_role(role)
        out = [e for e in self._ont.events.values() if e.body.observed_by == role]
        return _by_name(out)

    # ---- lifecycles --------------------------------------------------------

    def fsms_for_role(self, role: str) -> list[ResolvedStateMachine]:
        """State machines referenced by `lifecycle_ref` on any flow this role
        touches. De-duplicated; ordered by name."""
        self._require_role(role)
        names: set[str] = set()
        for f in self._flows_touching(role):
            if f.body.lifecycle_ref:
                names.add(f.body.lifecycle_ref)
        sms = [self._ont.state_machines[n] for n in names if n in self._ont.state_machines]
        return _by_name(sms)

    def flows_governed_by_fsm(self, fsm_name: str, role: str) -> list[ResolvedFlow]:
        """Flows the role touches that share the given FSM. Surfaces the
        multi-flow shared-lifecycle pattern (e.g. request_production +
        re_request_production both on ProductionRequestLifecycle)."""
        out = [
            f for f in self._flows_touching(role)
            if f.body.lifecycle_ref == fsm_name
        ]
        return _by_name(out)

    # ---- axioms ------------------------------------------------------------

    def axioms_on_flow(self, flow: str) -> list[AxiomBody]:
        return list(self._ont.get_axioms_for(flow))

    def advisory_axioms_for(self, role: str) -> list[tuple[str, AxiomBody]]:
        """Advisory axioms on any flow this role touches — these are the
        named viability inputs the agent's decisions can reference. Returns
        (flow_name, axiom) tuples so the agent knows where each criterion
        came from. Sorted by (flow_name, axiom_name)."""
        out: list[tuple[str, AxiomBody]] = []
        for f in self._flows_touching(role):
            for ax in f.axioms:
                sev = ax.severity.value if ax.severity is not None and hasattr(ax.severity, "value") else ax.severity
                if sev == "advisory":
                    out.append((f.name, ax))
        out.sort(key=lambda pair: (pair[0], pair[1].name))
        return out

    def _axioms_by_name(self) -> dict[str, AxiomBody]:
        """Every flow-declared axiom, indexed by name. Used to resolve a
        Playbook's criteria_refs to their authoritative `nl` definitions."""
        out: dict[str, AxiomBody] = {}
        for f in self._ont.flows.values():
            for ax in f.axioms:
                out[ax.name] = ax
        return out

    # ---- playbooks + tools -------------------------------------------------

    def playbooks_anchored_to(self, role: str) -> list[ResolvedPlaybook]:
        """Playbooks whose `role` is this role — the Mode 2 scaffolds the
        agent runs. Sorted by name."""
        self._require_role(role)
        return self._ont.playbooks_for_role(role)

    def tools_available_to(self, role: str) -> list[ResolvedTool]:
        """Tools this role may invoke via `call_tool` (role in available_to).
        Sorted by name."""
        self._require_role(role)
        return self._ont.tools_for_role(role)

    # ---- view assembly -----------------------------------------------------

    def render_role_view(self, role: str) -> RoleView:
        """Compose the full typed snapshot of a role. Pure resolution — no
        format decisions, no ordering inventions, no inferred preferences.
        The returned `RoleView`'s adapter methods (`as_agent_prompt`,
        `as_markdown`, `as_json`) format without re-querying."""
        r = self._require_role(role)
        identity = _to_identity(r)
        sv = self._ont.schema_view

        in_handoffs = tuple(_to_flow_summary(f, sv) for f in self.incoming_handoffs(role))
        out_handoffs = tuple(_to_flow_summary(f, sv) for f in self.outgoing_handoffs(role))
        in_queries = tuple(_to_flow_summary(f, sv) for f in self.incoming_queries(role))
        out_queries = tuple(_to_flow_summary(f, sv) for f in self.outgoing_queries(role))

        observed = tuple(_to_event_summary(e) for e in self.events_observed(role))
        emitted = tuple(_to_event_summary(e) for e in self.events_emitted(role))

        fsms = tuple(
            _to_fsm_summary(sm, [f.name for f in self.flows_governed_by_fsm(sm.name, role)])
            for sm in self.fsms_for_role(role)
        )

        advisory = tuple(_to_axiom_summary(ax) for _flow, ax in self.advisory_axioms_for(role))

        axiom_index = self._axioms_by_name()
        playbooks = tuple(
            _to_playbook_summary(pb, self._ont, axiom_index)
            for pb in self.playbooks_anchored_to(role)
        )
        tools = tuple(
            _to_tool_summary(t, sv) for t in self.tools_available_to(role)
        )

        return RoleView(
            identity=identity,
            incoming_handoffs=in_handoffs,
            outgoing_handoffs=out_handoffs,
            incoming_queries=in_queries,
            outgoing_queries=out_queries,
            events_observed=observed,
            events_emitted=emitted,
            fsms_governing_my_quanta=fsms,
            playbooks_anchored_to=playbooks,
            tools_available_to=tools,
            advisory_criteria=advisory,
        )


# ============================================================================
# Resolved → Pydantic conversion helpers
# ============================================================================


def _enum_value(v: object) -> str | None:
    if v is None:
        return None
    return v.value if hasattr(v, "value") else str(v)


def _to_axiom_summary(ax: AxiomBody) -> AxiomSummary:
    return AxiomSummary(
        name=ax.name,
        scope=_enum_value(ax.scope) or "flow",
        severity=_enum_value(ax.severity),
        nl=ax.nl,
        expr=ax.expr,
        message=ax.message,
        on_failure_route_to=ax.on_failure_route_to,
    )


def _to_flow_summary(f: ResolvedFlow, sv: SchemaView) -> FlowSummary:
    return FlowSummary(
        name=f.name,
        kind=f.kind,
        source_role=f.body.source_role,
        target_role=f.body.target_role,
        quantum=f.body.quantum,
        trigger_event=f.body.trigger_event,
        lifecycle_ref=f.body.lifecycle_ref,
        returns=f.body.returns,
        domain=f.domain,
        llm_prompt_hint=f.llm_prompt_hint,
        axioms=tuple(_to_axiom_summary(a) for a in f.axioms),
        quantum_schema=_to_quantum_schema(sv, f.body.quantum),
        returns_schema=_to_quantum_schema(sv, f.body.returns) if f.body.returns else None,
    )


def _classify_range(sv: SchemaView, range_name: str) -> str:
    """Discriminate primitive vs. class vs. enum range. Order matters: enums
    and classes can in principle share a name with LinkML primitives, so we
    check enum first, then class, then fall through to primitive."""
    try:
        if sv.get_enum(range_name) is not None:
            return "enum"
    except (KeyError, ValueError):
        pass
    try:
        if sv.get_class(range_name) is not None:
            return "class"
    except (KeyError, ValueError):
        pass
    return "primitive"


def _to_quantum_schema(sv: SchemaView, class_name: str | None) -> QuantumSchema | None:
    """Resolve a class's induced slots into a QuantumSchema. Returns None for
    a missing class (defensive — the cross-ref validator catches unknown
    quantum names at strict-validate time, so this should only fire if a
    caller hands in a non-class string)."""
    if class_name is None:
        return None
    try:
        cls = sv.get_class(class_name)
    except (KeyError, ValueError):
        return None
    if cls is None:
        return None
    try:
        induced = sv.class_induced_slots(class_name)
    except (KeyError, ValueError):
        return None

    slot_summaries: list[QuantumSlotSchema] = []
    for s in induced:
        range_name = s.range or sv.schema.default_range or "string"
        range_kind = _classify_range(sv, range_name)
        perms: tuple[str, ...] = ()
        if range_kind == "enum":
            try:
                enum_def = sv.get_enum(range_name)
            except (KeyError, ValueError):
                enum_def = None
            if enum_def is not None and enum_def.permissible_values:
                perms = tuple(enum_def.permissible_values.keys())
        slot_summaries.append(
            QuantumSlotSchema(
                name=s.name,
                range=range_name,
                range_kind=range_kind,
                required=bool(s.required),
                multivalued=bool(s.multivalued),
                description=s.description,
                permissible_values=perms,
            )
        )
    return QuantumSchema(
        name=class_name,
        description=cls.description,
        slots=tuple(slot_summaries),
    )


def _to_event_summary(e: ResolvedEvent) -> EventSummary:
    return EventSummary(
        name=e.name,
        description=e.body.description,
        observed_by=e.body.observed_by,
        llm_prompt_hint=e.body.llm_prompt_hint,
        domain=e.domain,
    )


def _to_fsm_summary(sm: ResolvedStateMachine, governs_flows: list[str]) -> FSMSummary:
    transitions = tuple(
        TransitionSummary(
            from_state=t.from_state,
            to_state=t.to_state,
            trigger=t.trigger,
            guard=t.guard,
        )
        for t in sm.body.transitions
    )
    return FSMSummary(
        name=sm.name,
        states=tuple(sm.body.states),
        initial=sm.body.initial,
        terminal=tuple(sm.body.terminal or ()),
        transitions=transitions,
        governs_flows=tuple(sorted(governs_flows)),
    )


def _to_playbook_summary(
    pb: ResolvedPlaybook, ont: Ontology, axiom_index: dict[str, AxiomBody]
) -> PlaybookSummary:
    """Resolve a Playbook into the rendered summary. The four inner lists are
    sorted by name so list position never implies priority (§2). Each query
    step is enriched with its `returns` class; each resolution path with its
    `target_role`; each criterion with the axiom's authoritative `nl`."""
    b = pb.body

    steps = sorted(b.context_assembly or [], key=lambda s: s.flow)
    context_assembly = tuple(
        PlaybookQueryStepView(
            flow=s.flow,
            returns=(ont.flows[s.flow].body.returns if s.flow in ont.flows else None),
            required=True if s.required is None else bool(s.required),
            inputs_from_quantum=tuple(
                PlaybookInputBindingView(param=bnd.param, from_quantum=bnd.from_quantum)
                for bnd in (s.inputs_from_quantum or [])
            ),
        )
        for s in steps
    )

    criteria: tuple[PlaybookCriterionView, ...] = ()
    resolutions: tuple[PlaybookResolutionView, ...] = ()
    if b.decision is not None:
        criteria = tuple(
            PlaybookCriterionView(
                name=name,
                nl=(axiom_index[name].nl if name in axiom_index else "(criterion not found)"),
            )
            for name in sorted(b.decision.criteria_refs or [])
        )
        resolutions = tuple(
            PlaybookResolutionView(
                flow=flow,
                target_role=(ont.flows[flow].body.target_role if flow in ont.flows else "?"),
            )
            for flow in sorted(b.decision.selects_one_of or [])
        )

    effects = sorted(
        b.always_fires or [], key=lambda e: e.event or e.flow or ""
    )
    always_fires = tuple(
        PlaybookEffectView(
            kind="event" if e.event else "flow",
            name=e.event or e.flow,
        )
        for e in effects
    )

    return PlaybookSummary(
        name=pb.name,
        triggered_by=b.triggered_by,
        input_quantum=b.input_quantum,
        synchronization=_enum_value(b.synchronization) or "wait_all",
        closed_set=bool(b.closed_set),
        context_assembly=context_assembly,
        criteria=criteria,
        selects_one_of=resolutions,
        always_fires=always_fires,
        llm_prompt_hint=pb.llm_prompt_hint,
    )


def _to_tool_summary(t: ResolvedTool, sv: SchemaView) -> ToolSummary:
    b = t.body
    return ToolSummary(
        name=t.name,
        category=_enum_value(b.category) or "reader",
        description=b.description,
        input_class=b.input_class,
        output_class=b.output_class,
        implementation=b.implementation,
        input_schema=_to_quantum_schema(sv, b.input_class),
        output_schema=_to_quantum_schema(sv, b.output_class),
        llm_prompt_hint=t.llm_prompt_hint,
    )


def _to_identity(r: ResolvedRole) -> RoleIdentity:
    return RoleIdentity(
        name=r.name,
        domain=r.domain,
        description=r.body.description,
        llm_prompt_hint=r.body.llm_prompt_hint,
        is_boundary=bool(r.body.is_boundary),
        human_involvement=_enum_value(r.body.human_involvement),
    )


def _by_name(items: Iterable):
    """Stable alphabetical sort by `.name`. Order discipline from §2 — the
    ontology declares no priority; the renderer must not invent one."""
    return sorted(items, key=lambda x: x.name)
