import dagre from '@dagrejs/dagre';
import type { OntologyPayload, Playbook } from '../../api/types';
import { hasEntity, hasFlow } from '../../components/panels/helpers';
import type { SelectionKind } from '../../store/ontology';

export const NODE_WIDTH = 196;
export const NODE_HEIGHT = 48;
export const PB_WIDTH = 216;
export const PB_HEIGHT = 62;
const GRAPH_PAD_X = 50;
const GRAPH_PAD_Y = 30;

/** Visual grouping of a node in the choreography. */
export type PBVariant = 'source' | 'playbook' | 'query' | 'resolution' | 'effect';

export type PBEdgeVariant = 'trigger' | 'assembly' | 'resolution' | 'effect';

export interface PlacedNode {
  id: string;
  variant: PBVariant;
  label: string;
  /** Selection to navigate to on click, or null if not resolvable. */
  navKind: SelectionKind | null;
  navId: string;
  /** Sub-label shown under the name (e.g. "trigger", "input"). */
  tag?: string;
  width: number;
  height: number;
  x: number;
  y: number;
}

export interface PBEdge {
  id: string;
  source: string;
  target: string;
  variant: PBEdgeVariant;
}

export interface PlaybookLayout {
  nodes: PlacedNode[];
  edges: PBEdge[];
  width: number;
  height: number;
}

interface NodeSpec {
  id: string;
  variant: PBVariant;
  label: string;
  navKind: SelectionKind | null;
  navId: string;
  tag?: string;
}

/**
 * Left-to-right dagre layout of a playbook's choreography:
 *
 *   trigger event ┐
 *   anchor role   ├─▶  PLAYBOOK ─┬─▶ context-assembly query flows
 *   input quantum ┘             ├─▶ resolution flows (selects one of)
 *                               └─▶ always-fires effects
 *
 * Sources land in the first rank, the playbook in the second, and its three
 * branch families fan out into the third. Node ids are variant-prefixed so a
 * flow that appears in two roles (rare) never collides.
 */
export function computePlaybookLayout(pb: Playbook, data: OntologyPayload): PlaybookLayout {
  const specs: NodeSpec[] = [];
  const edges: PBEdge[] = [];

  const PB = 'pb';
  specs.push({ id: PB, variant: 'playbook', label: pb.name, navKind: 'playbook', navId: pb.name });

  // Sources — trigger / anchor / input quantum
  const ev = `src:event:${pb.triggered_by}`;
  specs.push({ id: ev, variant: 'source', label: pb.triggered_by, navKind: 'event', navId: pb.triggered_by, tag: 'trigger' });
  edges.push({ id: `${ev}->pb`, source: ev, target: PB, variant: 'trigger' });

  const role = `src:role:${pb.role}`;
  specs.push({ id: role, variant: 'source', label: pb.role, navKind: 'role', navId: pb.role, tag: 'anchor role' });
  edges.push({ id: `${role}->pb`, source: role, target: PB, variant: 'trigger' });

  const inq = `src:entity:${pb.input_quantum}`;
  specs.push({
    id: inq,
    variant: 'source',
    label: pb.input_quantum,
    navKind: hasEntity(data, pb.input_quantum) ? 'entity' : null,
    navId: pb.input_quantum,
    tag: 'input',
  });
  edges.push({ id: `${inq}->pb`, source: inq, target: PB, variant: 'trigger' });

  // Context-assembly query flows
  for (const step of pb.context_assembly) {
    const id = `q:${step.flow}`;
    specs.push({
      id,
      variant: 'query',
      label: step.flow,
      navKind: hasFlow(data, step.flow) ? 'flow' : null,
      navId: step.flow,
      tag: step.required === false ? 'query · optional' : 'query',
    });
    edges.push({ id: `pb->${id}`, source: PB, target: id, variant: 'assembly' });
  }

  // Resolution flows — selects one of
  for (const flow of pb.decision?.selects_one_of ?? []) {
    const id = `r:${flow}`;
    specs.push({
      id,
      variant: 'resolution',
      label: flow,
      navKind: hasFlow(data, flow) ? 'flow' : null,
      navId: flow,
      tag: 'resolution',
    });
    edges.push({ id: `pb->${id}`, source: PB, target: id, variant: 'resolution' });
  }

  // Always-fires effects
  for (const af of pb.always_fires) {
    if (af.event) {
      const id = `eff:event:${af.event}`;
      specs.push({ id, variant: 'effect', label: af.event, navKind: 'event', navId: af.event, tag: 'always fires' });
      edges.push({ id: `pb->${id}`, source: PB, target: id, variant: 'effect' });
    } else if (af.flow) {
      const id = `eff:flow:${af.flow}`;
      specs.push({
        id,
        variant: 'effect',
        label: af.flow,
        navKind: hasFlow(data, af.flow) ? 'flow' : null,
        navId: af.flow,
        tag: 'always fires',
      });
      edges.push({ id: `pb->${id}`, source: PB, target: id, variant: 'effect' });
    }
  }

  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: 'LR', nodesep: 18, ranksep: 120, marginx: 24, marginy: 24 });
  g.setDefaultEdgeLabel(() => ({}));
  for (const s of specs) {
    const isPb = s.variant === 'playbook';
    g.setNode(s.id, { width: isPb ? PB_WIDTH : NODE_WIDTH, height: isPb ? PB_HEIGHT : NODE_HEIGHT });
  }
  for (const e of edges) g.setEdge(e.source, e.target);
  dagre.layout(g);

  const nodes: PlacedNode[] = specs.map((s) => {
    const n = g.node(s.id);
    const isPb = s.variant === 'playbook';
    return {
      ...s,
      width: isPb ? PB_WIDTH : NODE_WIDTH,
      height: isPb ? PB_HEIGHT : NODE_HEIGHT,
      x: (n?.x ?? 0) + GRAPH_PAD_X,
      y: (n?.y ?? 0) + GRAPH_PAD_Y,
    };
  });

  const maxX = nodes.reduce((m, n) => Math.max(m, n.x + n.width / 2), 0);
  const maxY = nodes.reduce((m, n) => Math.max(m, n.y + n.height / 2), 0);
  return { nodes, edges, width: maxX + GRAPH_PAD_X, height: maxY + GRAPH_PAD_Y };
}
