import { useMemo } from 'react';
import type { Flow, OntologyPayload, Role } from '../../api/types';
import { orderedDomains } from '../../config/domains';
import { useOntology, type Selection } from '../../store/ontology';
import { moveLane, useSwimlaneOrder } from '../../store/swimlaneOrder';
import { computeLayout, ROLE_HEIGHT, ROLE_WIDTH, type LaidOutRole } from './layout';
import { computeEdges } from './edgeGeometry';

interface Props {
  data: OntologyPayload;
}

export function SwimlaneGraph({ data }: Props) {
  const selection = useOntology((s) => s.selection);
  const navigate = useOntology((s) => s.navigate);
  const laneOrder = useSwimlaneOrder();

  const { layout, edges } = useMemo(() => {
    const usedDomains = new Set<string>();
    data.roles.forEach((r) => { if (r.domain) usedDomains.add(r.domain); });
    const domains = orderedDomains(usedDomains, laneOrder);
    const laid = computeLayout(data.roles, data.flows, domains);
    const pos = new Map<string, LaidOutRole>(laid.roles.map((r) => [r.role.name, r]));
    const edgeList = computeEdges(data.flows, pos);
    return { layout: laid, edges: edgeList };
  }, [data.roles, data.flows, laneOrder]);

  const highlighted = computeHighlight(selection, data.flows);

  return (
    <svg
      viewBox={`0 0 ${layout.width} ${layout.height}`}
      className="graph-svg"
      preserveAspectRatio="xMidYMid meet"
      onClick={() => navigate(null)}
    >
      {/* Swimlane backgrounds */}
      {layout.swimlanes.map((lane, i) => (
        <g key={lane.domain.id}>
          <rect
            x={0}
            y={lane.y}
            width={layout.width}
            height={lane.height}
            fill={lane.domain.tint}
            className="swimlane-rect"
          />
          <text x={34} y={lane.y + 16} className="swimlane-label">
            {lane.domain.label.toUpperCase()}
          </text>
          {lane.domain.hand && (
            <text x={layout.width - 12} y={lane.y + 22} textAnchor="end" className="swimlane-label-hand">
              {lane.domain.hand}
            </text>
          )}
          <LaneReorderButtons
            domainId={lane.domain.id}
            y={lane.y + 10}
            canMoveUp={i > 0}
            canMoveDown={i < layout.swimlanes.length - 1}
          />
        </g>
      ))}

      {/* Edges */}
      <g className="sketchy">
        {edges.map((e) => {
          const isSel = selection?.kind === 'flow' && selection.id === e.flow.name;
          const dim = selection != null && !isSel && !edgeTouchesHighlight(e.flow, highlighted);
          const cls = `flow-edge ${e.flow.kind}${isSel ? ' selected' : ''}${dim ? ' dimmed' : ''}`;
          return (
            <g
              key={e.flow.name}
              onClick={(evt) => {
                evt.stopPropagation();
                navigate({ kind: 'flow', id: e.flow.name });
              }}
            >
              <path d={e.path} className={cls} markerEnd={`url(#arrow-${e.flow.kind})`} />
              {e.flow.kind === 'cash' && (
                <path d={e.path} className="flow-edge-cash-inner" />
              )}
              <AxiomBadge flow={e.flow} x={e.labelX} y={e.labelY} onClick={(ev) => {
                ev.stopPropagation();
                const ax = e.flow.axioms[0];
                if (ax) navigate({ kind: 'axiom', id: ax.name });
              }} />
            </g>
          );
        })}
      </g>

      {/* Role nodes */}
      <g>
        {layout.roles.map(({ role, x, y }) => (
          <RoleNode
            key={role.name}
            role={role}
            x={x}
            y={y}
            selected={selection?.kind === 'role' && selection.id === role.name}
            dimmed={selection != null && !(selection.kind === 'role' && selection.id === role.name) && !highlighted.roles.has(role.name)}
            onClick={(evt) => {
              evt.stopPropagation();
              navigate({ kind: 'role', id: role.name });
            }}
          />
        ))}
      </g>
    </svg>
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
    <g className="lane-reorder" transform={`translate(8, ${y})`}>
      <g
        className={`lane-btn${canMoveUp ? '' : ' disabled'}`}
        transform="translate(0, 0)"
        onClick={(e) => { e.stopPropagation(); if (canMoveUp) moveLane(domainId, -1); }}
      >
        <rect x={0} y={0} width={16} height={12} rx={2} />
        <text x={8} y={9} textAnchor="middle">↑</text>
      </g>
      <g
        className={`lane-btn${canMoveDown ? '' : ' disabled'}`}
        transform="translate(0, 14)"
        onClick={(e) => { e.stopPropagation(); if (canMoveDown) moveLane(domainId, 1); }}
      >
        <rect x={0} y={0} width={16} height={12} rx={2} />
        <text x={8} y={9} textAnchor="middle">↓</text>
      </g>
    </g>
  );
}

interface RoleNodeProps {
  role: Role;
  x: number;
  y: number;
  selected: boolean;
  dimmed: boolean;
  onClick: (e: React.MouseEvent) => void;
}

function RoleNode({ role, x, y, selected, dimmed, onClick }: RoleNodeProps) {
  const cls = ['node-role'];
  if (role.is_boundary) cls.push('boundary');
  if (selected) cls.push('selected');
  if (dimmed) cls.push('dimmed');
  const halfW = ROLE_WIDTH / 2;
  const halfH = ROLE_HEIGHT / 2;
  return (
    <g transform={`translate(${x}, ${y})`} className={cls.join(' ')} onClick={onClick}>
      <rect x={-halfW} y={-halfH} width={ROLE_WIDTH} height={ROLE_HEIGHT} rx={2} />
      <text textAnchor="middle" y={4}>{role.name}</text>
      {role.human_involvement && role.human_involvement !== 'autonomous' && (
        <g className="hitl-badge" transform={`translate(${halfW - 8}, ${-halfH + 6})`}>
          <circle r={8} />
          <text textAnchor="middle" y={4}>{role.human_involvement === 'required' ? '!' : '?'}</text>
        </g>
      )}
    </g>
  );
}

interface AxiomBadgeProps {
  flow: Flow;
  x: number;
  y: number;
  onClick: (e: React.MouseEvent) => void;
}

function AxiomBadge({ flow, x, y, onClick }: AxiomBadgeProps) {
  if (flow.axioms.length === 0) return null;
  const sev = flow.axioms[0]!.severity ?? 'advisory';
  const color = sev === 'blocking' ? '#c04a3a' : sev === 'warning' ? '#d49a2a' : '#8a8070';
  return (
    <g className="axiom-badge" transform={`translate(${x}, ${y})`} onClick={onClick}>
      <circle r={8} fill={color} />
      <text textAnchor="middle" y={3}>!</text>
    </g>
  );
}

interface Highlight {
  roles: Set<string>;
  flows: Set<string>;
}

function computeHighlight(selection: Selection | null, flows: Flow[]): Highlight {
  const roles = new Set<string>();
  const sFlows = new Set<string>();
  if (!selection) return { roles, flows: sFlows };
  if (selection.kind === 'role') {
    roles.add(selection.id);
    for (const f of flows) {
      if (f.source_role === selection.id || f.target_role === selection.id) {
        sFlows.add(f.name);
        roles.add(f.source_role);
        roles.add(f.target_role);
      }
    }
  } else if (selection.kind === 'flow') {
    const f = flows.find((x) => x.name === selection.id);
    if (f) {
      roles.add(f.source_role);
      roles.add(f.target_role);
      sFlows.add(f.name);
    }
  }
  return { roles, flows: sFlows };
}

function edgeTouchesHighlight(flow: Flow, h: Highlight): boolean {
  return h.roles.has(flow.source_role) || h.roles.has(flow.target_role) || h.flows.has(flow.name);
}
