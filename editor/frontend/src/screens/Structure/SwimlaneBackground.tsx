import { ViewportPortal } from '@xyflow/react';
import type { Swimlane } from './layout';
import { moveLane } from '../../store/swimlaneOrder';

interface Props {
  swimlanes: Swimlane[];
  width: number;
}

/**
 * Domain swimlane backgrounds rendered inside React Flow's viewport. They
 * pan and zoom along with nodes via ViewportPortal, keeping the domain
 * band under each role as the user moves the canvas.
 *
 * Lane-reorder affordances ride along — two small ↑/↓ buttons pinned to
 * the lane's left edge that swap adjacency in the swimlaneOrder store.
 */
export function SwimlaneBackground({ swimlanes, width }: Props) {
  return (
    <ViewportPortal>
      <svg
        className="rf-swimlane-layer"
        width={width}
        height={swimlanes.at(-1) ? swimlanes.at(-1)!.y + swimlanes.at(-1)!.height : 0}
        style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
      >
        {swimlanes.map((lane, i) => (
          <g key={lane.domain.id}>
            <rect
              x={0}
              y={lane.y}
              width={width}
              height={lane.height}
              fill={lane.domain.tint}
              className="swimlane-rect"
            />
            <text x={34} y={lane.y + 16} className="swimlane-label">
              {lane.domain.label.toUpperCase()}
            </text>
            <LaneReorderButtons
              domainId={lane.domain.id}
              y={lane.y + 10}
              canMoveUp={i > 0}
              canMoveDown={i < swimlanes.length - 1}
            />
          </g>
        ))}
      </svg>
    </ViewportPortal>
  );
}

interface LaneReorderButtonsProps {
  domainId: string;
  y: number;
  canMoveUp: boolean;
  canMoveDown: boolean;
}

function LaneReorderButtons({ domainId, y, canMoveUp, canMoveDown }: LaneReorderButtonsProps) {
  return (
    <g className="lane-reorder" transform={`translate(8, ${y})`} style={{ pointerEvents: 'auto' }}>
      <g
        className={`lane-btn${canMoveUp ? '' : ' disabled'}`}
        transform="translate(0, 0)"
        onClick={(e) => {
          e.stopPropagation();
          if (canMoveUp) moveLane(domainId, -1);
        }}
      >
        <rect x={0} y={0} width={16} height={12} rx={2} />
        <text x={8} y={9} textAnchor="middle">
          ↑
        </text>
      </g>
      <g
        className={`lane-btn${canMoveDown ? '' : ' disabled'}`}
        transform="translate(0, 14)"
        onClick={(e) => {
          e.stopPropagation();
          if (canMoveDown) moveLane(domainId, 1);
        }}
      >
        <rect x={0} y={0} width={16} height={12} rx={2} />
        <text x={8} y={9} textAnchor="middle">
          ↓
        </text>
      </g>
    </g>
  );
}
