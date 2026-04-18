import type { Flow } from '../../api/types';
import type { LaidOutRole } from './layout';

export interface EdgeGeometry {
  flow: Flow;
  path: string;
  labelX: number;
  labelY: number;
  bundleIndex: number;
  bundleTotal: number;
}

/**
 * Group parallel flows between the same role pair and bundle them with
 * perpendicular offsets so they don't render on top of each other. Matches
 * the mockup's `edgePath` routine in RoleGraph.
 */
export function computeEdges(flows: Flow[], rolePos: Map<string, LaidOutRole>): EdgeGeometry[] {
  const byPair = new Map<string, Flow[]>();
  for (const f of flows) {
    const src = rolePos.get(f.source_role);
    const dst = rolePos.get(f.target_role);
    if (!src || !dst) continue;
    const key = `${f.source_role}::${f.target_role}`;
    const bucket = byPair.get(key) ?? [];
    bucket.push(f);
    byPair.set(key, bucket);
  }

  const out: EdgeGeometry[] = [];
  for (const bundle of byPair.values()) {
    bundle.forEach((f, idx) => {
      const a = rolePos.get(f.source_role)!;
      const b = rolePos.get(f.target_role)!;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const mx = (a.x + b.x) / 2;
      const my = (a.y + b.y) / 2;
      const len = Math.sqrt(dx * dx + dy * dy) || 1;
      const nx = -dy / len;
      const ny = dx / len;
      const offset = bundle.length > 1 ? (idx - (bundle.length - 1) / 2) * 24 : 0;
      const cx = mx + nx * (40 + offset);
      const cy = my + ny * (40 + offset);
      out.push({
        flow: f,
        path: `M${a.x},${a.y} Q${cx},${cy} ${b.x},${b.y}`,
        labelX: cx,
        labelY: cy,
        bundleIndex: idx,
        bundleTotal: bundle.length,
      });
    });
  }
  return out;
}
