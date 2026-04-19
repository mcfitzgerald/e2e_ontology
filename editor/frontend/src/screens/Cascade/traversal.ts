import type { Flow, OntologyPayload } from '../../api/types';

/**
 * Cascade traversal — BFS over causal chains rooted at a starting flow.
 *
 * Edges into depth d+1 come from two sources:
 *
 *  (1) Event-mediated: events whose `observed_by` equals the parent flow's
 *      `target_role` → flows whose `trigger_event` is that event.
 *      This is the canonical propagation pattern in the ontology.
 *
 *  (2) Axiom-mediated: any blocking axiom on the parent flow with an
 *      `on_failure_route_to` pointing at another flow. These represent
 *      recovery branches — the cascade forks into them when the gate
 *      trips. They're tagged separately so the UI can style them as
 *      "(on axiom trip)" rather than "via <event>".
 *
 * Cycles are suppressed by a first-touch seen-set: each flow appears at
 * most once, at its shallowest depth. `hardCap` bounds the output so a
 * runaway cycle can't produce a million-node canvas.
 */

export type CascadeEdgeKind = 'event' | 'axiom_trip';

export interface CascadeStep {
  flow: Flow;
  depth: number;
  parent: {
    flowName: string;
    via: string; // event name or axiom name
    kind: CascadeEdgeKind;
  } | null;
}

interface TraverseOptions {
  startFlow: string;
  maxDepth: number;
  data: OntologyPayload;
  hardCap?: number;
}

export function traverse({ startFlow, maxDepth, data, hardCap = 80 }: TraverseOptions): CascadeStep[] {
  const flowsByName = new Map(data.flows.map((f) => [f.name, f]));
  const eventsByName = new Map(data.events.map((e) => [e.name, e]));
  const flowsByTrigger = new Map<string, Flow[]>();
  for (const f of data.flows) {
    if (f.trigger_event) {
      const bucket = flowsByTrigger.get(f.trigger_event) ?? [];
      bucket.push(f);
      flowsByTrigger.set(f.trigger_event, bucket);
    }
  }
  const eventsByObserver = new Map<string, string[]>();
  for (const e of data.events) {
    const bucket = eventsByObserver.get(e.observed_by) ?? [];
    bucket.push(e.name);
    eventsByObserver.set(e.observed_by, bucket);
  }

  const steps: CascadeStep[] = [];
  const seen = new Set<string>();
  const queue: CascadeStep[] = [{ flow: flowsByName.get(startFlow)!, depth: 0, parent: null }];
  if (!queue[0]?.flow) return [];

  while (queue.length > 0 && steps.length < hardCap) {
    const step = queue.shift()!;
    if (seen.has(step.flow.name)) continue;
    if (step.depth > maxDepth) continue;
    seen.add(step.flow.name);
    steps.push(step);

    if (step.depth >= maxDepth) continue;

    // Axiom-trip FIRST so that when a downstream flow is reachable via both
    // an axiom trip AND an ordinary event, the axiom-trip wins the seen-set
    // race. These are the interesting edges: ordinary event edges reflect
    // happy-path propagation, axiom trips are the recovery branches the
    // cascade view exists to make visible.
    for (const ax of step.flow.axioms) {
      if (ax.severity !== 'blocking' || !ax.on_failure_route_to) continue;
      const df = flowsByName.get(ax.on_failure_route_to);
      if (!df || seen.has(df.name)) continue;
      queue.push({
        flow: df,
        depth: step.depth + 1,
        parent: { flowName: step.flow.name, via: ax.name, kind: 'axiom_trip' },
      });
    }

    // Event-mediated propagation
    const events = eventsByObserver.get(step.flow.target_role) ?? [];
    for (const evName of events) {
      if (!eventsByName.has(evName)) continue;
      const downstream = flowsByTrigger.get(evName) ?? [];
      for (const df of downstream) {
        if (seen.has(df.name)) continue;
        queue.push({
          flow: df,
          depth: step.depth + 1,
          parent: { flowName: step.flow.name, via: evName, kind: 'event' },
        });
      }
    }
  }

  return steps;
}

/**
 * Pick sensible starting flows surfaced in the left-rail chip list.
 *
 * Heuristic: a flow is a "good starting point" if it originates at a
 * boundary role (external signal entering the chain) OR has no inbound
 * flow-chain (nothing triggers it — it's a root). Sort by name for stable
 * ordering. Falls back to the first 5 flows if nothing matches.
 */
export function suggestedStarts(data: OntologyPayload): Flow[] {
  const boundaryRoles = new Set(data.roles.filter((r) => r.is_boundary).map((r) => r.name));
  const triggeredEvents = new Set<string>();
  for (const f of data.flows) if (f.trigger_event) triggeredEvents.add(f.trigger_event);
  const eventByObserver = new Map<string, string[]>();
  for (const e of data.events) {
    const bucket = eventByObserver.get(e.observed_by) ?? [];
    bucket.push(e.name);
    eventByObserver.set(e.observed_by, bucket);
  }
  const candidates = data.flows.filter((f) => {
    if (boundaryRoles.has(f.source_role)) return true;
    // Roots: this flow's trigger_event isn't observed by anyone (no upstream)
    if (!f.trigger_event) return false;
    const observers = data.events.find((e) => e.name === f.trigger_event)?.observed_by;
    if (!observers) return true;
    return boundaryRoles.has(observers);
  });
  const sorted = [...candidates].sort((a, b) => a.name.localeCompare(b.name));
  return sorted.length > 0 ? sorted.slice(0, 6) : data.flows.slice(0, 5);
}
