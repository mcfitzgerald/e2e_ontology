import { useCallback, useMemo, useState } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import {
  Controls,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type EdgeMouseHandler,
  type Node,
  type NodeMouseHandler,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { OntologyPayload } from '../../api/types';
import { useOntology } from '../../store/ontology';
import { useSwimlaneOrder } from '../../store/swimlaneOrder';
import { CARD_HEIGHT, CARD_WIDTH, COL_WIDTH, computeCascadeLayout } from './layout';
import { suggestedStarts, traverse } from './traversal';
import { FlowOccurrenceNode, type FlowOccurrenceNodeData } from './FlowOccurrenceNode';
import { AxiomTripEdge, EventEdge, type CascadeEdgeData } from './CascadeEdges';
import { CascadeBackground } from './CascadeBackground';
import './Cascade.css';

interface Props {
  data: OntologyPayload;
}

const nodeTypes = { flowOccurrence: FlowOccurrenceNode };
const edgeTypes = { event: EventEdge, axiomTrip: AxiomTripEdge };

export function CascadeScreen({ data }: Props) {
  return (
    <ReactFlowProvider>
      <CascadeInner data={data} />
    </ReactFlowProvider>
  );
}

function CascadeInner({ data }: Props) {
  const laneOrder = useSwimlaneOrder();
  const selection = useOntology((s) => s.selection);
  const navigate = useOntology((s) => s.navigate);

  const suggested = useMemo(() => suggestedStarts(data), [data]);
  const defaultStart = suggested[0]?.name ?? data.flows[0]?.name ?? '';

  const [startFlow, setStartFlow] = useState<string>(defaultStart);
  const [depth, setDepth] = useState<number>(5);
  const [showAxioms, setShowAxioms] = useState<boolean>(true);
  const [hovered, setHovered] = useState<string | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<string | null>(null);

  const steps = useMemo(
    () => (startFlow ? traverse({ startFlow, maxDepth: depth, data }) : []),
    [startFlow, depth, data],
  );

  const layout = useMemo(
    () => computeCascadeLayout(steps, data, laneOrder),
    [steps, data, laneOrder],
  );

  const rolesByName = useMemo(() => new Map(data.roles.map((r) => [r.name, r])), [data.roles]);

  // Focus neighborhood: the flow under selection/hover plus the two flows
  // it directly touches on either side of a parent edge. Used to dim
  // non-adjacent cards and edges.
  const focus = useMemo(() => {
    const active = hovered ?? (selection?.kind === 'flow' ? selection.id : null);
    if (!active) return null;
    const touching = new Set<string>([active]);
    for (const p of layout.placed) {
      if (p.step.flow.name === active && p.step.parent) {
        touching.add(p.step.parent.flowName);
      }
      if (p.step.parent?.flowName === active) {
        touching.add(p.step.flow.name);
      }
    }
    return touching;
  }, [hovered, selection, layout.placed]);

  const nodes = useMemo<Node<FlowOccurrenceNodeData>[]>(
    () =>
      layout.placed.map((p) => ({
        id: p.step.flow.name,
        type: 'flowOccurrence',
        position: { x: p.x, y: p.y },
        data: {
          flow: p.step.flow,
          srcDomain: rolesByName.get(p.step.flow.source_role)?.domain ?? null,
          dstDomain: rolesByName.get(p.step.flow.target_role)?.domain ?? null,
          showAxioms,
          dimmed: focus != null && !focus.has(p.step.flow.name),
        },
        selected: selection?.kind === 'flow' && selection.id === p.step.flow.name,
        draggable: false,
        selectable: true,
        width: CARD_WIDTH,
        height: CARD_HEIGHT,
      })),
    [layout.placed, rolesByName, showAxioms, focus, selection],
  );

  const edges = useMemo<Edge<CascadeEdgeData>[]>(() => {
    const out: Edge<CascadeEdgeData>[] = [];
    for (const p of layout.placed) {
      const parent = p.step.parent;
      if (!parent) continue;
      if (parent.kind === 'axiom_trip' && !showAxioms) continue;
      const edgeId = `${parent.flowName}->${p.step.flow.name}`;
      const inFocus =
        focus != null && focus.has(parent.flowName) && focus.has(p.step.flow.name);
      const dimmed = focus != null && !inFocus;
      const showLabel = inFocus || hoveredEdge === edgeId;
      out.push({
        id: edgeId,
        source: parent.flowName,
        target: p.step.flow.name,
        type: parent.kind === 'axiom_trip' ? 'axiomTrip' : 'event',
        data: { via: parent.via, dimmed, showLabel },
      });
    }
    return out;
  }, [layout.placed, showAxioms, focus, hoveredEdge]);

  const onNodeClick = useCallback<NodeMouseHandler>(
    (_, n) => navigate({ kind: 'flow', id: n.id }),
    [navigate],
  );
  const onEdgeClick = useCallback<EdgeMouseHandler>((e) => e.stopPropagation(), []);
  const onPaneClick = useCallback(() => navigate(null), [navigate]);
  const onNodeMouseEnter = useCallback<NodeMouseHandler>((_, n) => setHovered(n.id), []);
  const onNodeMouseLeave = useCallback(() => setHovered(null), []);
  const onEdgeMouseEnter = useCallback<EdgeMouseHandler>((_, e) => setHoveredEdge(e.id), []);
  const onEdgeMouseLeave = useCallback(() => setHoveredEdge(null), []);

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
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              fitView
              fitViewOptions={{ padding: 0.12 }}
              minZoom={0.3}
              maxZoom={2}
              panOnDrag
              zoomOnScroll
              nodesDraggable={false}
              nodesConnectable={false}
              edgesFocusable={false}
              selectNodesOnDrag={false}
              onNodeClick={onNodeClick}
              onEdgeClick={onEdgeClick}
              onPaneClick={onPaneClick}
              onNodeMouseEnter={onNodeMouseEnter}
              onNodeMouseLeave={onNodeMouseLeave}
              onEdgeMouseEnter={onEdgeMouseEnter}
              onEdgeMouseLeave={onEdgeMouseLeave}
              proOptions={{ hideAttribution: false }}
            >
              <CascadeBackground
                swimlanes={layout.swimlanes}
                columns={layout.columns}
                width={layout.width}
                height={layout.height}
                columnWidth={COL_WIDTH - 40}
              />
              <Controls showInteractive={false} position="bottom-right" />
            </ReactFlow>
          )}
        </div>
      </Panel>
    </PanelGroup>
  );
}
