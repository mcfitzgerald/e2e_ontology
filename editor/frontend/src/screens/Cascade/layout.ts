import { domainFor, orderedDomains, type DomainConfig } from '../../config/domains';
import type { OntologyPayload, Role } from '../../api/types';
import type { CascadeStep } from './traversal';

export const CARD_WIDTH = 260;
export const CARD_HEIGHT = 64;
export const COL_WIDTH = 340;
const LANE_HEIGHT = 96;
const LANE_GAP = 14;
const LANE_TOP_PAD = 48;
const GRAPH_LEFT_PAD = 36;
const GRAPH_RIGHT_PAD = 48;
const CARD_Y_STEP = CARD_HEIGHT + 10;

export interface PlacedStep {
  step: CascadeStep;
  x: number;
  y: number;
}

export interface CascadeSwimlane {
  domain: DomainConfig;
  y: number;
  height: number;
}

export interface CascadeLayout {
  placed: PlacedStep[];
  swimlanes: CascadeSwimlane[];
  width: number;
  height: number;
  columns: { depth: number; x: number }[];
}

/**
 * Lay out cascade steps in a (depth × domain-swimlane) grid.
 *
 * Y = domain swimlane per the brief (Screen 2 spec: "Y-axis: domain
 * swimlanes, same vertical order as Screen 1"). The domain chosen per
 * step is the *target_role's* domain — cascade is about propagation
 * hitting a role, not originating from one. When multiple flows land in
 * the same (depth, lane) cell they stack vertically within the lane.
 */
export function computeCascadeLayout(
  steps: CascadeStep[],
  data: OntologyPayload,
  preferredOrder: string[],
): CascadeLayout {
  const roleById = new Map(data.roles.map((r) => [r.name, r]));

  const usedDomains = new Set<string>();
  for (const s of steps) {
    const domain = resolveDomainForStep(s, roleById);
    if (domain) usedDomains.add(domain);
  }
  const swimlaneDomains = orderedDomains(usedDomains, preferredOrder);
  const domainIndex = new Map(swimlaneDomains.map((d, i) => [d.id, i] as const));

  const laneY = (idx: number) => LANE_TOP_PAD + idx * (LANE_HEIGHT + LANE_GAP);
  const swimlanes: CascadeSwimlane[] = swimlaneDomains.map((d, i) => ({
    domain: d,
    y: laneY(i),
    height: LANE_HEIGHT,
  }));

  // Bucket steps into (depth, laneIdx) cells
  const buckets = new Map<string, CascadeStep[]>();
  let maxDepth = 0;
  for (const s of steps) {
    const domain = resolveDomainForStep(s, roleById);
    const laneIdx = domain ? domainIndex.get(domain) ?? -1 : -1;
    if (laneIdx < 0) continue;
    maxDepth = Math.max(maxDepth, s.depth);
    const key = `${s.depth}:${laneIdx}`;
    const bucket = buckets.get(key) ?? [];
    bucket.push(s);
    buckets.set(key, bucket);
  }

  const placed: PlacedStep[] = [];
  for (const [key, bucket] of buckets) {
    const [dStr, lStr] = key.split(':');
    const d = Number(dStr);
    const lane = Number(lStr);
    bucket.forEach((s, i) => {
      const laneCenterY = swimlanes[lane]!.y + swimlanes[lane]!.height / 2;
      const stackOffset = (i - (bucket.length - 1) / 2) * CARD_Y_STEP;
      placed.push({
        step: s,
        x: GRAPH_LEFT_PAD + d * COL_WIDTH,
        y: laneCenterY + stackOffset - CARD_HEIGHT / 2,
      });
    });
  }

  const columns = Array.from({ length: maxDepth + 1 }, (_, d) => ({ depth: d, x: GRAPH_LEFT_PAD + d * COL_WIDTH }));
  const width = GRAPH_LEFT_PAD + (maxDepth + 1) * COL_WIDTH + GRAPH_RIGHT_PAD;
  const height = Math.max(laneY(swimlanes.length) - LANE_GAP + LANE_TOP_PAD, 360);

  return { placed, swimlanes, width, height, columns };
}

function resolveDomainForStep(s: CascadeStep, roleById: Map<string, Role>): string | null {
  // Cascade nodes belong to the lane where the work lands = target role's domain.
  const role = roleById.get(s.flow.target_role);
  if (!role) return null;
  // If the target role has a domain we know about, use it. Otherwise use the
  // flow's domain (serialize.py assigns it from the YAML section) as fallback.
  const domain = role.domain ?? s.flow.domain;
  if (domain && domainFor(domain)) return domain;
  return null;
}
