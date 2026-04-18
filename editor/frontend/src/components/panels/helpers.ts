import type { Axiom, Flow, OntologyPayload, Role, Event, StateMachine, Entity } from '../../api/types';

/** Flows where this role is the source. */
export const outgoingFlows = (data: OntologyPayload, roleName: string): Flow[] =>
  data.flows.filter((f) => f.source_role === roleName);

/** Flows where this role is the target. */
export const incomingFlows = (data: OntologyPayload, roleName: string): Flow[] =>
  data.flows.filter((f) => f.target_role === roleName);

/** Events observed by this role. */
export const observedEvents = (data: OntologyPayload, roleName: string): Event[] =>
  data.events.filter((e) => e.observed_by === roleName);

/** Flows whose trigger_event matches this event. */
export const flowsTriggeredBy = (data: OntologyPayload, eventName: string): Flow[] =>
  data.flows.filter((f) => f.trigger_event === eventName);

/** Flows that share this FSM as their lifecycle_ref. */
export const flowsUsingFsm = (data: OntologyPayload, fsmName: string): Flow[] =>
  data.flows.filter((f) => f.lifecycle_ref === fsmName);

/** Flow that owns the given axiom (axioms live on flows). */
export const flowOwningAxiom = (
  data: OntologyPayload,
  axiomName: string,
): { flow: Flow; axiom: Axiom } | null => {
  for (const flow of data.flows) {
    const axiom = flow.axioms.find((a) => a.name === axiomName);
    if (axiom) return { flow, axiom };
  }
  return null;
};

/** Flows using this entity as their quantum (payload class). */
export const flowsCarryingEntity = (data: OntologyPayload, entityName: string): Flow[] =>
  data.flows.filter((f) => f.quantum === entityName);

/** Flows that return this entity (query flows where returns == entityName). */
export const flowsReturningEntity = (data: OntologyPayload, entityName: string): Flow[] =>
  data.flows.filter((f) => f.returns === entityName);

/** Lookup by name. */
export const roleByName = (data: OntologyPayload, name: string): Role | null =>
  data.roles.find((r) => r.name === name) ?? null;
export const flowByName = (data: OntologyPayload, name: string): Flow | null =>
  data.flows.find((f) => f.name === name) ?? null;
export const eventByName = (data: OntologyPayload, name: string): Event | null =>
  data.events.find((e) => e.name === name) ?? null;
export const fsmByName = (data: OntologyPayload, name: string): StateMachine | null =>
  data.state_machines.find((s) => s.name === name) ?? null;
export const entityByName = (data: OntologyPayload, name: string): Entity | null =>
  data.entities.find((e) => e.name === name) ?? null;

/** True if an entity with this name exists in the payload. */
export const hasEntity = (data: OntologyPayload, name: string): boolean =>
  data.entities.some((e) => e.name === name);
