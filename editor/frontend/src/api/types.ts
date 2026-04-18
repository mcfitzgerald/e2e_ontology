/*
 * TypeScript mirrors of editor/backend/serialize.py payloads.
 * Keep in sync when the backend shape changes.
 */

export type FlowKind = 'material' | 'information' | 'cash';

export type HumanInvolvement = 'required' | 'conditional' | 'autonomous';

export type AxiomSeverity = 'blocking' | 'warning' | 'advisory';

export type AxiomScope = 'class' | 'flow';

export interface Role {
  name: string;
  domain: string | null;
  subdomain: string | null;
  description: string;
  llm_prompt_hint: string;
  is_boundary: boolean;
  human_involvement: HumanInvolvement | null;
  can_be_played_by: string | null;
}

export interface Event {
  name: string;
  domain: string | null;
  subdomain: string | null;
  description: string;
  observed_by: string;
  llm_prompt_hint: string;
}

export interface AxiomReferences {
  metrics: string[];
  classes: string[];
  flows: string[];
  events: string[];
}

export interface Axiom {
  name: string;
  scope: AxiomScope | null;
  severity: AxiomSeverity | null;
  nl: string;
  expr: string | null;
  message: string | null;
  on_failure_route_to: string | null;
  references: AxiomReferences | null;
}

export interface Flow {
  name: string;
  kind: FlowKind;
  domain: string | null;
  subdomain: string | null;
  source_role: string;
  target_role: string;
  quantum: string;
  trigger_event: string | null;
  lifecycle_ref: string | null;
  returns: string | null;
  llm_prompt_hint: string | null;
  axioms: Axiom[];
}

export interface Transition {
  from_state: string;
  to_state: string;
  trigger: string | null;
  guard: string | null;
}

export interface StateMachine {
  name: string;
  domain: string | null;
  subdomain: string | null;
  states: string[];
  initial: string;
  terminal: string[];
  transitions: Transition[];
}

export interface Entity {
  name: string;
  domain: string | null;
  subdomain: string | null;
  description: string | null;
  attributes: string[];
  rule_count: number;
  metrics: string[];
}

export interface ValidationIssue {
  level: 'error' | 'warning';
  element: string;
  field: string | null;
  message: string;
}

export interface OntologyPayload {
  path: string;
  roles: Role[];
  events: Event[];
  flows: Flow[];
  state_machines: StateMachine[];
  entities: Entity[];
  warnings: ValidationIssue[];
  summary: {
    roles: number;
    events: number;
    flows: number;
    state_machines: number;
    entities: number;
    warnings: number;
  };
}

/* ===== Diff payload (mirror of editor/backend/diff.py) ===== */

export type DiffKind =
  | 'roles'
  | 'flows'
  | 'events'
  | 'state_machines'
  | 'entities'
  | 'enums'
  | 'warnings';

export type DiffStatus = 'added' | 'changed' | 'removed';

export interface FieldChange {
  path: string;
  before: unknown;
  after: unknown;
}

export interface ElementChange {
  name: string;
  changes: FieldChange[];
}

export interface KindDelta {
  added: string[];
  removed: string[];
  changed: ElementChange[];
}

export interface DiffSummary {
  added: number;
  changed: number;
  removed: number;
}

export interface DiffPayload {
  base: string;
  base_resolved: string | null;
  head: string;
  head_path: string;
  kinds: Partial<Record<DiffKind, KindDelta>>;
  summary: DiffSummary;
}

export interface GitStatus {
  branch: string | null;
  branch_label: string | null;
  head_short: string | null;
  ahead: number | null;
  behind: number | null;
  dirty: boolean | null;
  reason: string | null;
}
