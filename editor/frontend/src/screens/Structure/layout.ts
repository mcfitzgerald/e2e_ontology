import dagre from '@dagrejs/dagre';
import type { Flow, Role } from '../../api/types';
import type { DomainConfig } from '../../config/domains';

export const ROLE_WIDTH = 170;
export const ROLE_HEIGHT = 36;
const LANE_HEIGHT = 80;
const LANE_GAP = 14;
const LANE_TOP_PAD = 40;
const GRAPH_LEFT_PAD = 180;
const GRAPH_RIGHT_PAD = 80;

export interface LaidOutRole {
  role: Role;
  x: number;
  y: number;
}

export interface Swimlane {
  domain: DomainConfig;
  y: number;
  height: number;
  centerY: number;
}

export interface Layout {
  roles: LaidOutRole[];
  swimlanes: Swimlane[];
  width: number;
  height: number;
}

/**
 * Compute role positions using dagre for X-ordering, with Y forced to each
 * role's domain swimlane. Dagre's crossing-minimization still helps because
 * the X coordinate it assigns reflects causal depth through the graph; we
 * just overwrite Y so the result reads as a supply-chain swimlane chart.
 */
export function computeLayout(roles: Role[], flows: Flow[], domains: DomainConfig[]): Layout {
  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: 'LR',
    nodesep: 48,
    ranksep: 96,
    marginx: 40,
    marginy: 40,
  });
  g.setDefaultEdgeLabel(() => ({}));

  const roleById = new Map(roles.map((r) => [r.name, r] as const));
  roles.forEach((r) => g.setNode(r.name, { width: ROLE_WIDTH, height: ROLE_HEIGHT }));
  flows.forEach((f) => {
    if (roleById.has(f.source_role) && roleById.has(f.target_role) && f.source_role !== f.target_role) {
      g.setEdge(f.source_role, f.target_role);
    }
  });

  dagre.layout(g);

  const laneY = (idx: number) => LANE_TOP_PAD + idx * (LANE_HEIGHT + LANE_GAP);

  const domainIndex = new Map(domains.map((d, i) => [d.id, i] as const));
  const laidOut: LaidOutRole[] = roles.map((r) => {
    const node = g.node(r.name);
    const laneIdx = r.domain != null ? domainIndex.get(r.domain) ?? -1 : -1;
    const y = laneIdx >= 0 ? laneY(laneIdx) + LANE_HEIGHT / 2 : 0;
    return { role: r, x: (node?.x ?? 0) + GRAPH_LEFT_PAD, y };
  });

  // Forcing Y to domain swimlanes can make two roles in the same domain
  // collide on X when dagre assigned them similar ranks. Push-right within
  // each lane to guarantee minimum horizontal spacing.
  const MIN_X_SPACING = ROLE_WIDTH + 40;
  const byDomain = new Map<string, LaidOutRole[]>();
  for (const lr of laidOut) {
    const key = lr.role.domain ?? '__none__';
    const bucket = byDomain.get(key) ?? [];
    bucket.push(lr);
    byDomain.set(key, bucket);
  }
  for (const bucket of byDomain.values()) {
    bucket.sort((a, b) => a.x - b.x);
    for (let i = 1; i < bucket.length; i++) {
      const prev = bucket[i - 1]!;
      const cur = bucket[i]!;
      if (cur.x - prev.x < MIN_X_SPACING) {
        cur.x = prev.x + MIN_X_SPACING;
      }
    }
  }

  const maxX = laidOut.reduce((m, n) => Math.max(m, n.x + ROLE_WIDTH / 2), 0);
  const width = maxX + GRAPH_RIGHT_PAD;
  const height = laneY(domains.length) - LANE_GAP + LANE_TOP_PAD;

  const swimlanes: Swimlane[] = domains.map((d, i) => {
    const y = laneY(i);
    return { domain: d, y, height: LANE_HEIGHT, centerY: y + LANE_HEIGHT / 2 };
  });

  return { roles: laidOut, swimlanes, width, height };
}
