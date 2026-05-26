import { ViewportPortal } from '@xyflow/react';
import type { CascadeSwimlane } from './layout';

interface Props {
  swimlanes: CascadeSwimlane[];
  columns: { depth: number; x: number }[];
  width: number;
  height: number;
  columnWidth: number;
}

/**
 * Domain swimlanes + depth column headers/dividers rendered inside the
 * React Flow viewport. Pans and zooms with content. Matches the
 * SwimlaneBackground on Structure so the two screens overlay mentally.
 */
export function CascadeBackground({ swimlanes, columns, width, height, columnWidth }: Props) {
  return (
    <ViewportPortal>
      <svg
        className="rf-cascade-background"
        style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
        width={width}
        height={height}
        overflow="visible"
      >
        {swimlanes.map((lane) => (
          <g key={lane.domain.id}>
            <rect
              x={0}
              y={lane.y}
              width={width}
              height={lane.height}
              fill={lane.domain.tint}
              className="swimlane-rect"
            />
            <text x={10} y={lane.y + 16} className="swimlane-label">
              {lane.domain.label.toUpperCase()}
            </text>
          </g>
        ))}
        {columns.map((c) => (
          <g key={c.depth}>
            <text x={c.x} y={20} className="cascade-col-header">
              DEPTH {c.depth}
              {c.depth === 0 ? ' (request)' : ''}
            </text>
            <line
              x1={c.x + columnWidth}
              y1={28}
              x2={c.x + columnWidth}
              y2={height - 4}
              className="cascade-col-divider"
            />
          </g>
        ))}
      </svg>
    </ViewportPortal>
  );
}
