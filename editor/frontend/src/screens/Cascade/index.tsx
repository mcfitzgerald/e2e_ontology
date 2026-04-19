import { useMemo, useState } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import type { Flow, OntologyPayload } from '../../api/types';
import { domainFor } from '../../config/domains';
import { useOntology } from '../../store/ontology';
import { useSwimlaneOrder } from '../../store/swimlaneOrder';
import { CARD_HEIGHT, CARD_WIDTH, computeCascadeLayout } from './layout';
import { suggestedStarts, traverse, type CascadeStep } from './traversal';
import './Cascade.css';

interface Props {
  data: OntologyPayload;
}

export function CascadeScreen({ data }: Props) {
  const laneOrder = useSwimlaneOrder();
  const selection = useOntology((s) => s.selection);
  const navigate = useOntology((s) => s.navigate);

  const suggested = useMemo(() => suggestedStarts(data), [data]);
  const defaultStart = suggested[0]?.name ?? data.flows[0]?.name ?? '';

  const [startFlow, setStartFlow] = useState<string>(defaultStart);
  const [depth, setDepth] = useState<number>(5);
  const [showAxioms, setShowAxioms] = useState<boolean>(true);

  const steps = useMemo(
    () => (startFlow ? traverse({ startFlow, maxDepth: depth, data }) : []),
    [startFlow, depth, data],
  );

  const layout = useMemo(
    () => computeCascadeLayout(steps, data, laneOrder),
    [steps, data, laneOrder],
  );

  const placedByFlow = useMemo(() => {
    const m = new Map<string, (typeof layout.placed)[number]>();
    for (const p of layout.placed) m.set(p.step.flow.name, p);
    return m;
  }, [layout]);

  const rolesByName = useMemo(() => new Map(data.roles.map((r) => [r.name, r])), [data.roles]);

  return (
    <PanelGroup direction="horizontal" autoSaveId="editor.layout.cascade" className="cascade">
      <Panel defaultSize={22} minSize={14} maxSize={40} className="cascade-rail-panel">
      <aside className="cascade-rail" aria-label="cascade controls">
        <h4>start flow</h4>
        <select
          className="cascade-picker"
          value={startFlow}
          onChange={(e) => setStartFlow(e.target.value)}
        >
          {data.flows.map((f) => (
            <option key={f.name} value={f.name}>
              {f.name}
            </option>
          ))}
        </select>

        <h4>max depth</h4>
        <div className="cascade-depth-control">
          <input
            type="range"
            min={1}
            max={8}
            step={1}
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
          />
          <span>{depth}</span>
        </div>

        <h4>options</h4>
        <label className="cascade-toggle">
          <input
            type="checkbox"
            checked={showAxioms}
            onChange={(e) => setShowAxioms(e.target.checked)}
          />
          show axiom trips
        </label>

        <h4>common starting points</h4>
        <div className="cascade-suggested">
          {suggested.map((f) => (
            <button
              key={f.name}
              className={startFlow === f.name ? 'active' : ''}
              onClick={() => setStartFlow(f.name)}
              title={`${f.source_role} → ${f.target_role}`}
            >
              <span className={`cascade-suggested-glyph ${f.kind}`} />
              {f.name}
            </button>
          ))}
        </div>

        <div className="cascade-note">
          <span className="cascade-note-label">why this view</span>
          Trace how a single request cascades downstream. Depth d+1 fires
          when a flow at depth d emits an event that another flow
          triggers on, or when a blocking axiom at depth d trips to its
          recovery flow.
        </div>
      </aside>
      </Panel>
      <PanelResizeHandle className="cascade-resize-handle" />
      <Panel defaultSize={78} minSize={40} className="cascade-canvas-panel">
      <div className="cascade-canvas">
        {steps.length === 0 ? (
          <div className="cascade-empty">
            No cascade — starting flow has no downstream chain at this depth.
          </div>
        ) : (
          <svg
            className="cascade-svg"
            viewBox={`0 0 ${layout.width} ${layout.height}`}
            preserveAspectRatio="xMidYMid meet"
            onClick={() => navigate(null)}
          >
            {/* Swimlane backgrounds */}
            {layout.swimlanes.map((lane) => (
              <g key={lane.domain.id}>
                <rect
                  x={0}
                  y={lane.y}
                  width={layout.width}
                  height={lane.height}
                  fill={lane.domain.tint}
                  className="swimlane-rect"
                />
                <text x={10} y={lane.y + 16} className="swimlane-label">
                  {lane.domain.label.toUpperCase()}
                </text>
              </g>
            ))}

            {/* Depth column headers + dividers */}
            {layout.columns.map((c) => (
              <g key={c.depth}>
                <text x={c.x} y={20} className="cascade-col-header">
                  DEPTH {c.depth}
                  {c.depth === 0 ? ' (request)' : ''}
                </text>
                <line
                  x1={c.x + CARD_WIDTH + 30}
                  y1={28}
                  x2={c.x + CARD_WIDTH + 30}
                  y2={layout.height - 4}
                  className="cascade-col-divider"
                />
              </g>
            ))}

            {/* Parent arrows */}
            <g className="sketchy">
              {layout.placed.map((p) => {
                const parent = p.step.parent;
                if (!parent) return null;
                const parentPlaced = placedByFlow.get(parent.flowName);
                if (!parentPlaced) return null;
                if (parent.kind === 'axiom_trip' && !showAxioms) return null;
                const a = { x: parentPlaced.x + CARD_WIDTH, y: parentPlaced.y + CARD_HEIGHT / 2 };
                const b = { x: p.x, y: p.y + CARD_HEIGHT / 2 };
                const midX = (a.x + b.x) / 2;
                const d = `M${a.x},${a.y} C${midX},${a.y} ${midX},${b.y} ${b.x},${b.y}`;
                const labelText = parent.kind === 'axiom_trip' ? `⊥ ${parent.via}` : `via ${parent.via}`;
                const labelW = labelText.length * 6.2 + 8;
                const labelY = (a.y + b.y) / 2 - 6;
                return (
                  <g key={`${parent.flowName}->${p.step.flow.name}`}>
                    <path d={d} className={`cascade-arrow ${parent.kind}`} markerEnd="url(#arrow-ink)" />
                    <rect
                      x={midX - labelW / 2}
                      y={labelY - 9}
                      width={labelW}
                      height={13}
                      className="cascade-arrow-label-bib"
                    />
                    <text
                      x={midX}
                      y={labelY}
                      textAnchor="middle"
                      className={`cascade-arrow-label ${parent.kind}`}
                    >
                      {labelText}
                    </text>
                  </g>
                );
              })}
            </g>

            {/* Flow-occurrence cards */}
            <g>
              {layout.placed.map((p) => {
                const src = rolesByName.get(p.step.flow.source_role);
                const dst = rolesByName.get(p.step.flow.target_role);
                return (
                  <FlowOccurrenceCard
                    key={p.step.flow.name}
                    step={p.step}
                    x={p.x}
                    y={p.y}
                    selected={selection?.kind === 'flow' && selection.id === p.step.flow.name}
                    showAxiom={showAxioms}
                    srcDomain={src?.domain ?? null}
                    dstDomain={dst?.domain ?? null}
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate({ kind: 'flow', id: p.step.flow.name });
                    }}
                  />
                );
              })}
            </g>
          </svg>
        )}
      </div>
      </Panel>
    </PanelGroup>
  );
}

interface CardProps {
  step: CascadeStep;
  x: number;
  y: number;
  selected: boolean;
  showAxiom: boolean;
  srcDomain: string | null;
  dstDomain: string | null;
  onClick: (e: React.MouseEvent) => void;
}

function FlowOccurrenceCard({ step, x, y, selected, showAxiom, srcDomain, dstDomain, onClick }: CardProps) {
  const flow: Flow = step.flow;
  const srcTint = domainFor(srcDomain)?.tint ?? 'var(--paper-dark)';
  const dstTint = domainFor(dstDomain)?.tint ?? 'var(--paper-dark)';
  const blocking = flow.axioms.find((a) => a.severity === 'blocking');
  const warning = flow.axioms.find((a) => a.severity === 'warning');
  const axiom = blocking ?? warning ?? flow.axioms[0];
  const kindAbbr = flow.kind.slice(0, 4).toUpperCase();

  return (
    <g
      transform={`translate(${x}, ${y})`}
      className={`cascade-card${selected ? ' selected' : ''}`}
      onClick={onClick}
    >
      <rect x={0} y={0} width={CARD_WIDTH} height={CARD_HEIGHT} rx={2} className="cascade-card-body" />
      <rect x={0} y={0} width={CARD_WIDTH} height={5} className="cascade-card-band-src" fill={srcTint} />
      <rect x={0} y={CARD_HEIGHT - 5} width={CARD_WIDTH} height={5} className="cascade-card-band-dst" fill={dstTint} />
      <text x={12} y={28} className="cascade-card-name">
        {flow.name}
      </text>
      <text x={12} y={46} className="cascade-card-route">
        {flow.source_role} → {flow.target_role}
      </text>

      {/* Kind glyph — upper-right */}
      <g transform={`translate(${CARD_WIDTH - 50}, 14)`}>
        <rect width={42} height={16} rx={1} className={`cascade-card-kind-rect ${flow.kind}`} />
        <text x={21} y={11} textAnchor="middle" className="cascade-card-kind">
          {kindAbbr}
        </text>
      </g>

      {/* Axiom dot — below kind glyph, right edge */}
      {showAxiom && axiom && (
        <g transform={`translate(${CARD_WIDTH - 16}, 42)`}>
          <title>{`${axiom.severity ?? 'advisory'} axiom: ${axiom.name}`}</title>
          <circle r={5} className={`cascade-card-axiom ${axiom.severity ?? 'advisory'}`} />
        </g>
      )}
    </g>
  );
}
