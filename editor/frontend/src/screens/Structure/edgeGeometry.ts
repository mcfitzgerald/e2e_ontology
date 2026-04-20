import type { Flow } from '../../api/types';

export interface EdgeBundleInfo {
  flow: Flow;
  bundleIndex: number;
  bundleTotal: number;
}

/**
 * Group parallel flows between the same role pair and return their bundle
 * positions. The custom FlowEdge component uses these to offset its
 * control point perpendicularly so parallel flows don't stack visually.
 *
 * Path computation moved into FlowEdge itself so that pan/zoom + React
 * Flow's handle-position changes stay in sync without a re-layout pass.
 */
export function computeEdgeBundles(flows: Flow[]): EdgeBundleInfo[] {
  const byPair = new Map<string, Flow[]>();
  for (const f of flows) {
    const key = `${f.source_role}::${f.target_role}`;
    const bucket = byPair.get(key) ?? [];
    bucket.push(f);
    byPair.set(key, bucket);
  }

  const out: EdgeBundleInfo[] = [];
  for (const bundle of byPair.values()) {
    bundle.forEach((f, idx) => {
      out.push({ flow: f, bundleIndex: idx, bundleTotal: bundle.length });
    });
  }
  return out;
}
