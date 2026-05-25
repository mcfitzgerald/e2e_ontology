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
import type { OntologyPayload, StateMachine } from '../../api/types';
import { useOntology } from '../../store/ontology';
import { eventByName, flowOwningAxiom, flowsUsingFsm } from '../../components/panels/helpers';
import { StateNode, type StateNodeData } from './StateNode';
import { TransitionEdge, type TransitionEdgeData } from './TransitionEdge';
import { computeFsmLayout, STATE_HEIGHT, STATE_WIDTH } from './layout';
import './FSM.css';

interface Props {
  data: OntologyPayload;
}

const nodeTypes = { fsmState: StateNode };
const edgeTypes = { fsmTransition: TransitionEdge };

export function FSMScreen({ data }: Props) {
  return (
    <ReactFlowProvider>
      <FSMInner data={data} />
    </ReactFlowProvider>
  );
}

function FSMInner({ data }: Props) {
  const selection = useOntology((s) => s.selection);
  const navigate = useOntology((s) => s.navigate);

  const fsms = data.state_machines;
  const defaultFsm = fsms[0]?.name ?? '';
  const [selectedFsm, setSelectedFsm] = useState<string>(defaultFsm);
  const [hovered, setHovered] = useState<string | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<string | null>(null);

  const fsm: StateMachine | null = useMemo(
    () => fsms.find((f) => f.name === selectedFsm) ?? fsms[0] ?? null,
    [fsms, selectedFsm],
  );

  const layout = useMemo(() => (fsm ? computeFsmLayout(fsm) : null), [fsm]);

  const sharingFlows = useMemo(
    () => (fsm ? flowsUsingFsm(data, fsm.name) : []),
    [data, fsm],
  );

  // Focus neighborhood: hovering a state highlights its incoming/outgoing
  // transitions and shows their labels. Clicks navigate to the FSM panel
  // rather than selecting a state, so no selection-driven focus here.
  const focusedState = hovered;

  const onGuardClick = useCallback(
    (guardName: string) => {
      const owner = flowOwningAxiom(data, guardName);
      if (owner) navigate({ kind: 'axiom', id: guardName });
      else if (fsm) navigate({ kind: 'state_machine', id: fsm.name });
    },
    [data, fsm, navigate],
  );

  const onTriggerClick = useCallback(
    (triggerName: string) => {
      if (eventByName(data, triggerName)) navigate({ kind: 'event', id: triggerName });
    },
    [data, navigate],
  );

  const nodes = useMemo<Node<StateNodeData>[]>(() => {
    if (!fsm || !layout) return [];
    return layout.states.map((s) => ({
      id: s.name,
      type: 'fsmState',
      position: { x: s.x - STATE_WIDTH / 2, y: s.y - STATE_HEIGHT / 2 },
      data: {
        name: s.name,
        isInitial: s.isInitial,
        isTerminal: s.isTerminal,
        dimmed: focusedState != null && focusedState !== s.name,
      },
      draggable: false,
      selectable: true,
      selected: false,
      width: STATE_WIDTH,
      height: STATE_HEIGHT,
    }));
  }, [fsm, layout, focusedState]);

  const edges = useMemo<Edge<TransitionEdgeData>[]>(() => {
    if (!fsm) return [];
    return fsm.transitions.map((t, i) => {
      const id = `${t.from_state}->${t.to_state}#${i}`;
      const guardResolves = t.guard ? flowOwningAxiom(data, t.guard) != null : false;
      const triggerResolves = t.trigger ? eventByName(data, t.trigger) != null : false;
      const inFocus =
        focusedState != null &&
        (focusedState === t.from_state || focusedState === t.to_state);
      const dimmed = focusedState != null && !inFocus;
      const showLabel = inFocus || hoveredEdge === id || focusedState == null;
      const isSel =
        selection?.kind === 'axiom' && t.guard != null && selection.id === t.guard;
      return {
        id,
        source: t.from_state,
        target: t.to_state,
        type: 'fsmTransition',
        selected: isSel,
        data: {
          trigger: t.trigger,
          triggerResolves,
          guard: t.guard,
          guardResolves,
          dimmed,
          showLabel,
          onTriggerClick,
          onGuardClick,
        },
      };
    });
  }, [fsm, data, focusedState, hoveredEdge, selection, onGuardClick, onTriggerClick]);

  const onNodeClick = useCallback<NodeMouseHandler>(
    (_, _n) => {
      if (fsm) navigate({ kind: 'state_machine', id: fsm.name });
    },
    [fsm, navigate],
  );

  const onEdgeClick = useCallback<EdgeMouseHandler>(
    (_, _e) => {
      // Edge body click navigates to the FSM panel; the guard chip on the
      // label has its own onClick that routes to the axiom.
      if (fsm) navigate({ kind: 'state_machine', id: fsm.name });
    },
    [fsm, navigate],
  );

  const onPaneClick = useCallback(() => navigate(null), [navigate]);
  const onNodeMouseEnter = useCallback<NodeMouseHandler>((_, n) => setHovered(n.id), []);
  const onNodeMouseLeave = useCallback(() => setHovered(null), []);
  const onEdgeMouseEnter = useCallback<EdgeMouseHandler>((_, e) => setHoveredEdge(e.id), []);
  const onEdgeMouseLeave = useCallback(() => setHoveredEdge(null), []);

  if (!fsm) {
    return (
      <section className="fsm">
        <div className="fsm-empty">No state machines defined in this ontology.</div>
      </section>
    );
  }

  return (
    <PanelGroup direction="horizontal" autoSaveId="editor.layout.fsm" className="fsm">
      <Panel defaultSize={24} minSize={14} maxSize={40} className="fsm-rail-panel">
        <aside className="fsm-rail" aria-label="fsm controls">
          <h4>state machine</h4>
          <select
            className="fsm-picker"
            value={fsm.name}
            onChange={(e) => setSelectedFsm(e.target.value)}
          >
            {fsms.map((f) => (
              <option key={f.name} value={f.name}>
                {f.name}
              </option>
            ))}
          </select>

          <h4>summary</h4>
          <div className="fsm-summary">
            <div>
              <span className="fsm-summary-k">domain</span>
              <span className="fsm-summary-v">{fsm.domain ?? '—'}</span>
            </div>
            <div>
              <span className="fsm-summary-k">states</span>
              <span className="fsm-summary-v">{fsm.states.length}</span>
            </div>
            <div>
              <span className="fsm-summary-k">initial</span>
              <span className="fsm-summary-v">{fsm.initial}</span>
            </div>
            <div>
              <span className="fsm-summary-k">terminal</span>
              <span className="fsm-summary-v">
                {fsm.terminal.length > 0 ? fsm.terminal.join(', ') : '—'}
              </span>
            </div>
            <div>
              <span className="fsm-summary-k">transitions</span>
              <span className="fsm-summary-v">{fsm.transitions.length}</span>
            </div>
          </div>

          <h4>transitions</h4>
          <ul className="fsm-rail-transitions">
            {fsm.transitions.map((t, i) => (
              <li key={`${t.from_state}-${t.to_state}-${i}`}>
                <code className="fsm-rail-state">{t.from_state}</code>
                <span className="fsm-rail-arrow">→</span>
                <code className="fsm-rail-state">{t.to_state}</code>
                {t.trigger && (
                  eventByName(data, t.trigger) ? (
                    <button
                      className="fsm-rail-trigger clickable"
                      onClick={() => onTriggerClick(t.trigger!)}
                      title="open event"
                    >
                      on {t.trigger}
                    </button>
                  ) : (
                    <div className="fsm-rail-trigger">on {t.trigger}</div>
                  )
                )}
                {t.guard && (
                  <button
                    className="fsm-rail-guard"
                    onClick={() => onGuardClick(t.guard!)}
                    title="open guard axiom"
                  >
                    ⊢ {t.guard}
                  </button>
                )}
              </li>
            ))}
          </ul>

          <h4>flows sharing this lifecycle ({sharingFlows.length})</h4>
          <div className="fsm-rail-sharing">
            {sharingFlows.length === 0 && (
              <span className="fsm-rail-empty">no flows reference this fsm</span>
            )}
            {sharingFlows.map((f) => (
              <button
                key={f.name}
                className="fsm-rail-share"
                onClick={() => navigate({ kind: 'flow', id: f.name })}
              >
                <span className={`fsm-rail-share-glyph ${f.kind}`} />
                {f.name}
              </button>
            ))}
          </div>

          <div className="fsm-note">
            <span className="fsm-note-label">why this view</span>
            A lifecycle is shared infrastructure: multiple flows can govern
            the same state machine. Guard axioms may live on any
            participating flow — click a guard chip to jump to the axiom
            even when it isn't on the obvious owner.
          </div>
        </aside>
      </Panel>
      <PanelResizeHandle className="fsm-resize-handle" />
      <Panel defaultSize={76} minSize={40} className="fsm-canvas-panel">
        <div className="fsm-canvas">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
            fitViewOptions={{ padding: 0.18 }}
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
            <Controls showInteractive={false} position="bottom-right" />
          </ReactFlow>
        </div>
      </Panel>
    </PanelGroup>
  );
}
