from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "1.7.0"
version = "0.1.0"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )





class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'scont',
     'default_range': 'string',
     'description': 'Metaschema declaring the shapes of scont annotation bodies. '
                    'Concrete supply chain ontology classes carry '
                    'JSON-in-folded-string annotations whose content conforms to '
                    'the classes defined here.',
     'id': 'https://e2e-ontology.dev/schemas/scont_meta',
     'imports': ['linkml:types'],
     'name': 'scont_meta',
     'prefixes': {'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'},
                  'scont': {'prefix_prefix': 'scont',
                            'prefix_reference': 'https://e2e-ontology.dev/'}},
     'source_file': 'scont_meta.yaml'} )

class Severity(str, Enum):
    """
    Severity of an axiom violation. Blocking axioms halt the flow and route via `on_failure_route_to`. Warnings surface to humans but do not block. Advisory are informational only.
    """
    blocking = "blocking"
    """
    Violation halts the flow; recovery routing required.
    """
    warning = "warning"
    """
    Violation is surfaced to an operator but does not halt.
    """
    advisory = "advisory"
    """
    Informational; flagged but neither halting nor surfaced.
    """


class Scope(str, Enum):
    """
    Whether an axiom attaches to a class or a flow.
    """
    class_ = "class"
    """
    Class-level invariant — a constraint on the class itself.
    """
    flow = "flow"
    """
    Flow-scoped invariant — a constraint on the handoff.
    """


class HumanInvolvement(str, Enum):
    """
    Declares the autonomy envelope for a role. The orchestrator uses this alongside its own policy (thresholds, SLAs, mechanisms) to decide whether to involve a human for a given decision. Design-time domain knowledge; runtime policy stays in the orchestrator.
    """
    required = "required"
    """
    This role must always be played by a human actor.
    """
    conditional = "conditional"
    """
    A human may be required depending on situation complexity or thresholds. Orchestrator decides per-decision based on its policy.
    """
    autonomous = "autonomous"
    """
    This role is always agent-played; no human involvement.
    """


class FlowKind(str, Enum):
    """
    Conservation/reversibility kind of a flow's quantum.
    """
    information = "information"
    """
    Non-conserved, copyable. Freshness and authority are key.
    """
    material = "material"
    """
    Mass-conserving minus loss, physical, hard to reverse.
    """
    cash = "cash"
    """
    Value-conserving, directional, settlement-final.
    """


class MetricKind(str, Enum):
    """
    MetricFlow-compatible metric kind.
    """
    measure = "measure"
    """
    A raw aggregation over an entity.
    """
    dimension = "dimension"
    """
    A categorical or temporal grouping axis.
    """
    metric = "metric"
    """
    A derived measure, typically over one or more measures.
    """


class MetricSource(str, Enum):
    """
    Where a metric's definition currently lives. Ontology is authoritative while dbt is not yet deployed at scale; `promotion_target: dbt` on a local metric flags it as a candidate for future upstream migration.
    """
    local = "local"
    """
    Defined here in the ontology.
    """
    dbt = "dbt"
    """
    Delegated to the dbt semantic layer (future).
    """



class RoleBody(ConfiguredBaseModel):
    """
    Shape of the `scont:role` annotation carried by a class tagged `instantiates: [scont:Role]`. Describes the role's semantic purpose and declares its autonomy envelope for downstream orchestrators.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'scont:RoleBody',
         'from_schema': 'https://e2e-ontology.dev/schemas/scont_meta'})

    description: str = Field(default=..., description="""One-line human description of what this role is responsible for in the supply chain.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RoleBody', 'EventBody']} })
    llm_prompt_hint: str = Field(default=..., description="""Navigation/reasoning aid for an LLM agent consuming this role: what signals it owns, what flows it participates in, what gotchas exist, how it relates to adjacent roles.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RoleBody', 'EventBody']} })
    is_boundary: Optional[bool] = Field(default=None, description="""True if this role represents an external function the ontology does not model (commercial/customer development, co-manufacturer, regulatory body, etc.). Boundary roles participate in flows crossing the SC boundary but their internals are outside scope.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RoleBody']} })
    human_involvement: Optional[HumanInvolvement] = Field(default=None, description="""Autonomy envelope for this role. Ontology declares the domain truth (\"this role may require a human for complex decisions\"); the orchestrator decides when and how based on its policy.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RoleBody']} })
    can_be_played_by: Optional[str] = Field(default=None, description="""Optional free-form note describing the kinds of entities or actors that typically play this role. Informational; not validated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RoleBody']} })


class EventBody(ConfiguredBaseModel):
    """
    Shape of the `scont:event` annotation on a class tagged `instantiates: [scont:Event]`. Events trigger flows and represent first-class observable happenings in the domain.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'scont:EventBody',
         'from_schema': 'https://e2e-ontology.dev/schemas/scont_meta'})

    description: str = Field(default=..., description="""One-line description of what this event represents.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RoleBody', 'EventBody']} })
    observed_by: str = Field(default=..., description="""Name of the Role that produces or detects this event. Must resolve to a declared Role in the ontology.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EventBody']} })
    llm_prompt_hint: str = Field(default=..., description="""Navigation aid: when this event fires, what downstream flows are triggered, what upstream signal produced it, what an agent should do when it observes it.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RoleBody', 'EventBody']} })


class FlowBody(ConfiguredBaseModel):
    """
    Shape of the `scont:flow` annotation on a class tagged with any of `instantiates: [scont:InformationFlow | scont:MaterialFlow | scont:CashFlow]`. Declares the handoff's source, target, payload, trigger, and lifecycle. When `returns` is populated the flow is a query (request-response); when absent it is a handoff (responsibility transfers).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'scont:FlowBody',
         'from_schema': 'https://e2e-ontology.dev/schemas/scont_meta'})

    source_role: str = Field(default=..., description="""Name of the Role that originates this flow. Must resolve to a declared Role.""", json_schema_extra = { "linkml_meta": {'domain_of': ['FlowBody']} })
    target_role: str = Field(default=..., description="""Name of the Role that receives this flow. Must resolve to a declared Role.""", json_schema_extra = { "linkml_meta": {'domain_of': ['FlowBody']} })
    quantum: str = Field(default=..., description="""Name of the class carrying the flow's payload. For handoff flows this is the business object being moved. For query flows this is the request payload; the response shape is declared by `returns`. Must resolve to a declared class.""", json_schema_extra = { "linkml_meta": {'domain_of': ['FlowBody']} })
    trigger_event: Optional[str] = Field(default=None, description="""Name of the Event that causes an occurrence of this flow. Must resolve to a declared Event if set.""", json_schema_extra = { "linkml_meta": {'domain_of': ['FlowBody']} })
    lifecycle_ref: Optional[str] = Field(default=None, description="""Name of the StateMachine tracking the quantum's state transitions through this flow. Must resolve to a declared StateMachine if set.""", json_schema_extra = { "linkml_meta": {'domain_of': ['FlowBody']} })
    returns: Optional[str] = Field(default=None, description="""Name of the class that describes the response payload for a query flow. Presence of this field is the machine-validatable signal that the flow is request-response (not fire-and-forget). Must resolve to a declared class if set. Absent on handoff flows.""", json_schema_extra = { "linkml_meta": {'domain_of': ['FlowBody']} })


class AxiomReferences(ConfiguredBaseModel):
    """
    Structured references an axiom makes to other ontology elements. Each slot is a list of names that should resolve to declared ontology objects of the corresponding kind.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'scont:AxiomReferences',
         'from_schema': 'https://e2e-ontology.dev/schemas/scont_meta'})

    metrics: Optional[list[str]] = Field(default=None, description="""Names of metrics the axiom references in its expr or nl body.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AxiomReferences']} })
    classes: Optional[list[str]] = Field(default=None, description="""Names of classes the axiom references.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AxiomReferences']} })
    flows: Optional[list[str]] = Field(default=None, description="""Names of flows the axiom references.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AxiomReferences']} })
    events: Optional[list[str]] = Field(default=None, description="""Names of events the axiom references.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AxiomReferences']} })


class AxiomBody(ConfiguredBaseModel):
    """
    Shape of a single axiom entry within the `scont:axioms` annotation list on a class or flow. Each axiom is either a hard-gate blocking constraint with deterministic recovery routing, or a soft constraint (warning/advisory) that informs agent judgment.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'scont:AxiomBody',
         'from_schema': 'https://e2e-ontology.dev/schemas/scont_meta'})

    name: str = Field(default=..., description="""Unique axiom name. Used for cross-references (including the convention that an FSM transition's `guard` field matches an axiom name on the parent flow).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AxiomBody', 'MetricBody']} })
    scope: Scope = Field(default=..., description="""Whether the axiom attaches to a class (invariant on the class's instance data) or a flow (invariant on the handoff).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AxiomBody']} })
    expr: Optional[str] = Field(default=None, description="""Optional machine-evaluable expression in LinkML's `equals_expression` syntax. Slot names in curly braces; Python-subset operators and comparisons. Evaluates to None on missing values. When absent, the axiom is evaluated by the LLM reading `nl`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AxiomBody', 'MetricBody']} })
    nl: str = Field(default=..., description="""Natural-language statement of the axiom. Always required. Survives schema refactors where `expr` may break. Read by LLM validators and by agents as navigation context.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AxiomBody']} })
    severity: Optional[Severity] = Field(default=None, description="""Severity level controlling agent response to a violation.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AxiomBody']} })
    message: Optional[str] = Field(default=None, description="""Short message emitted when the axiom is violated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AxiomBody']} })
    references: Optional[AxiomReferences] = Field(default=None, description="""Structured cross-references to other ontology elements.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AxiomBody']} })
    on_failure_route_to: Optional[str] = Field(default=None, description="""Name of the recovery flow the orchestrator should invoke when a blocking axiom violation fires. Must resolve to a declared flow if set. Absence on a blocking axiom indicates the conflict requires context assembly and potential human involvement at the target role (see initial_design_draft.md §3.7 and §4 Two reasoning modes).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AxiomBody']} })


class TransitionBody(ConfiguredBaseModel):
    """
    A single transition within a StateMachineBody's transitions list. Wire form uses `from` and `to` (JSON keys); Pydantic models expose these as `from_state` and `to_state` via field aliases.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'scont:TransitionBody',
         'from_schema': 'https://e2e-ontology.dev/schemas/scont_meta'})

    from_state: str = Field(default=..., description="""Source state name. Must be a declared state.""", json_schema_extra = { "linkml_meta": {'aliases': ['from'], 'domain_of': ['TransitionBody']} })
    to_state: str = Field(default=..., description="""Target state name. Must be a declared state.""", json_schema_extra = { "linkml_meta": {'aliases': ['to'], 'domain_of': ['TransitionBody']} })
    trigger: Optional[str] = Field(default=None, description="""Event name or short string naming what drives the transition.""", json_schema_extra = { "linkml_meta": {'domain_of': ['TransitionBody']} })
    guard: Optional[str] = Field(default=None, description="""Axiom name that gates this transition. By convention, resolves to an axiom declared on the parent flow or class. The exploder enforces the resolution (see initial_design_draft.md §11).""", json_schema_extra = { "linkml_meta": {'domain_of': ['TransitionBody']} })


class StateMachineBody(ConfiguredBaseModel):
    """
    Shape of the `scont:state_machine` annotation on a class tagged `instantiates: [scont:StateMachine]`. Declares states, transitions, initial, and terminal states.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'scont:StateMachineBody',
         'from_schema': 'https://e2e-ontology.dev/schemas/scont_meta'})

    states: list[str] = Field(default=..., description="""All declared states in the FSM. Must be unique.""", json_schema_extra = { "linkml_meta": {'domain_of': ['StateMachineBody']} })
    transitions: list[TransitionBody] = Field(default=..., description="""List of allowed transitions. Each transition's from_state and to_state must appear in `states`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['StateMachineBody']} })
    initial: str = Field(default=..., description="""Initial state for new instances. Must appear in `states`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['StateMachineBody']} })
    terminal: Optional[list[str]] = Field(default=None, description="""Terminal states. Each must appear in `states`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['StateMachineBody']} })


class MetricBody(ConfiguredBaseModel):
    """
    Shape of a single metric entry within the `scont:metrics` annotation list on an entity class. MetricFlow-compatible vocabulary so that promotion to the dbt semantic layer is a translation, not a rewrite (see initial_design_draft.md §5).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'scont:MetricBody',
         'from_schema': 'https://e2e-ontology.dev/schemas/scont_meta'})

    name: str = Field(default=..., description="""Unique metric name.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AxiomBody', 'MetricBody']} })
    kind: MetricKind = Field(default=..., description="""MetricFlow metric kind.""", json_schema_extra = { "linkml_meta": {'domain_of': ['MetricBody']} })
    entity: str = Field(default=..., description="""Name of the entity class this metric attaches to. Must resolve to a declared class.""", json_schema_extra = { "linkml_meta": {'domain_of': ['MetricBody']} })
    aggregation: Optional[str] = Field(default=None, description="""Aggregation function (avg, sum, count, min, max, p50, p90, etc.).""", json_schema_extra = { "linkml_meta": {'domain_of': ['MetricBody']} })
    expr: Optional[str] = Field(default=None, description="""Optional computed expression in LinkML's `equals_expression` syntax. If absent, the metric is a simple aggregation over a slot.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AxiomBody', 'MetricBody']} })
    time_grain: Optional[str] = Field(default=None, description="""Granularity of time bucketing (day, week, month, etc.).""", json_schema_extra = { "linkml_meta": {'domain_of': ['MetricBody']} })
    unit: Optional[str] = Field(default=None, description="""Unit of measure for the metric value.""", json_schema_extra = { "linkml_meta": {'domain_of': ['MetricBody']} })
    definition: Optional[str] = Field(default=None, description="""Human-readable definition of what this metric measures.""", json_schema_extra = { "linkml_meta": {'domain_of': ['MetricBody']} })
    source: Optional[MetricSource] = Field(default=None, description="""Where the metric's definition currently lives. `local` means the ontology is authoritative; `dbt` means the ontology delegates to the dbt semantic layer (future).""", json_schema_extra = { "linkml_meta": {'domain_of': ['MetricBody']} })
    promotion_target: Optional[str] = Field(default=None, description="""Optional hint that this local metric is a candidate for future promotion to the dbt semantic layer. Informational.""", json_schema_extra = { "linkml_meta": {'domain_of': ['MetricBody']} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
RoleBody.model_rebuild()
EventBody.model_rebuild()
FlowBody.model_rebuild()
AxiomReferences.model_rebuild()
AxiomBody.model_rebuild()
TransitionBody.model_rebuild()
StateMachineBody.model_rebuild()
MetricBody.model_rebuild()
