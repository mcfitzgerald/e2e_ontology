import { BaseEdge, EdgeLabelRenderer, type EdgeProps } from '@xyflow/react';
import type { DiffStatus, Flow } from '../../api/types';

export interface FlowEdgeData extends Record<string, unknown> {
  flow: Flow;
  bundleIndex: number;
  bundleTotal: number;
  diffStatus: DiffStatus | null;
  dimmed: boolean;
}

const BUNDLE_STEP = 24;
const BASE_OFFSET = 40;

/**
 * Flow edge rendered inside React Flow's SVG layer. Quadratic bezier with
 * a perpendicular control-point offset driven by bundle index, so parallel
 * flows between the same role pair fan out instead of stacking. Carries
 * the same visual grammar as the pre-port SVG edge: kind-specific stroke,
 * diff underlay, axiom dot, cash double-line. Uses SketchyFilters arrow
 * markers (`arrow-information` / `arrow-material` / `arrow-cash`) mounted
 * at app root.
 */
export function FlowEdge({ id, sourceX, sourceY, targetX, targetY, data, selected }: EdgeProps) {
  const d = (data ?? {}) as FlowEdgeData;
  const { flow, bundleIndex, bundleTotal, diffStatus, dimmed } = d;

  const dx = targetX - sourceX;
  const dy = targetY - sourceY;
  const mx = (sourceX + targetX) / 2;
  const my = (sourceY + targetY) / 2;
  const len = Math.hypot(dx, dy) || 1;
  const nx = -dy / len;
  const ny = dx / len;
  const offset = bundleTotal > 1 ? (bundleIndex - (bundleTotal - 1) / 2) * BUNDLE_STEP : 0;
  const cx = mx + nx * (BASE_OFFSET + offset);
  const cy = my + ny * (BASE_OFFSET + offset);
  const path = `M${sourceX},${sourceY} Q${cx},${cy} ${targetX},${targetY}`;

  const strokeCls = [
    'flow-edge',
    flow.kind,
    selected ? 'selected' : '',
    dimmed ? 'dimmed' : '',
    diffStatus ? `diff-${diffStatus}` : '',
  ]
    .filter(Boolean)
    .join(' ');

  const axiom = flow.axioms[0];
  const axiomSev = axiom?.severity ?? 'advisory';
  const axiomColor =
    axiomSev === 'blocking' ? '#c04a3a' : axiomSev === 'warning' ? '#d49a2a' : '#8a8070';

  return (
    <>
      {diffStatus && diffStatus !== 'removed' && (
        <path d={path} className={`flow-edge-diff-underlay ${diffStatus}`} fill="none" />
      )}
      <BaseEdge id={id} path={path} className={strokeCls} markerEnd={`url(#arrow-${flow.kind})`} />
      {flow.kind === 'cash' && <path d={path} className="flow-edge-cash-inner" fill="none" />}
      {axiom && (
        <EdgeLabelRenderer>
          <div
            className={`rf-axiom-dot ${axiomSev}`}
            style={{
              transform: `translate(-50%, -50%) translate(${cx}px, ${cy}px)`,
              backgroundColor: axiomColor,
            }}
            title={`${axiomSev} axiom: ${axiom.name}`}
          />
        </EdgeLabelRenderer>
      )}
    </>
  );
}
