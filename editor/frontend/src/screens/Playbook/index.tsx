import { useCallback, useMemo, useState } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import {
  Controls,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
  type NodeMouseHandler,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { OntologyPayload, Playbook } from '../../api/types';
import { useOntology, type Selection } from '../../store/ontology';
import { toolsAvailableTo } from '../../components/panels/helpers';
import { PlaybookNode, type PlaybookNodeData } from './PlaybookNode';
import { computePlaybookLayout } from './layout';
import './Playbook.css';

interface Props {
  data: OntologyPayload;
}

const nodeTypes = { pbNode: PlaybookNode };

export function PlaybookScreen({ data }: Props) {
  return (
    <ReactFlowProvider>
      <PlaybookInner data={data} />
    </ReactFlowProvider>
  );
}

function PlaybookInner({ data }: Props) {
  const selection = useOntology((s) => s.selection);
  const navigate = useOntology((s) => s.navigate);

  const playbooks = data.playbooks;
  const defaultPb = playbooks[0]?.name ?? '';
  const [selectedPb, setSelectedPb] = useState<string>(defaultPb);

  const pb: Playbook | null = useMemo(
    () => playbooks.find((p) => p.name === selectedPb) ?? playbooks[0] ?? null,
    [playbooks, selectedPb],
  );

  const layout = useMemo(() => (pb ? computePlaybookLayout(pb, data) : null), [pb, data]);

  const railTools = useMemo(() => (pb ? toolsAvailableTo(data, pb.role) : []), [data, pb]);
  const otherTools = useMemo(
    () => (pb ? data.tools.filter((t) => !t.available_to.includes(pb.role)) : data.tools),
    [data, pb],
  );

  const nodes = useMemo<Node<PlaybookNodeData>[]>(() => {
    if (!layout) return [];
    return layout.nodes.map((n) => ({
      id: n.id,
      type: 'pbNode',
      position: { x: n.x - n.width / 2, y: n.y - n.height / 2 },
      data: {
        label: n.label,
        variant: n.variant,
        tag: n.tag,
        clickable: n.navKind != null,
        dimmed: false,
      },
      draggable: false,
      selectable: n.navKind != null,
      selected:
        n.navKind != null && selection?.kind === n.navKind && selection.id === n.navId,
      width: n.width,
      height: n.height,
    }));
  }, [layout, selection]);

  const edges = useMemo<Edge[]>(() => {
    if (!layout) return [];
    return layout.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: 'default',
      className: `rf-pb-edge rf-pb-edge--${e.variant}`,
      markerEnd: 'url(#arrow-ink)',
      focusable: false,
    }));
  }, [layout]);

  const navById = useMemo(() => {
    const m = new Map<string, Selection | null>();
    layout?.nodes.forEach((n) => m.set(n.id, n.navKind ? { kind: n.navKind, id: n.navId } : null));
    return m;
  }, [layout]);

  const onNodeClick = useCallback<NodeMouseHandler>(
    (_, n) => {
      const nav = navById.get(n.id);
      if (nav) navigate(nav);
    },
    [navById, navigate],
  );

  const onPaneClick = useCallback(() => navigate(null), [navigate]);

  if (!pb) {
    return (
      <section className="pb">
        <div className="pb-empty">No playbooks defined in this ontology.</div>
      </section>
    );
  }

  const queryCount = pb.context_assembly.length;
  const pathCount = pb.decision?.selects_one_of.length ?? 0;

  return (
    <PanelGroup direction="horizontal" autoSaveId="editor.layout.playbook" className="pb">
      <Panel defaultSize={26} minSize={16} maxSize={42} className="pb-rail-panel">
        <aside className="pb-rail" aria-label="playbook controls">
          <h4>playbook</h4>
          <select className="pb-picker" value={pb.name} onChange={(e) => setSelectedPb(e.target.value)}>
            {playbooks.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>

          <h4>summary</h4>
          <div className="pb-summary">
            <SummaryRow k="role" v={pb.role} onClick={() => navigate({ kind: 'role', id: pb.role })} />
            <SummaryRow
              k="trigger"
              v={pb.triggered_by}
              onClick={() => navigate({ kind: 'event', id: pb.triggered_by })}
            />
            <SummaryRow k="input" v={pb.input_quantum} />
            <SummaryRow k="sync" v={pb.synchronization ?? '—'} />
            <SummaryRow k="evidence" v={pb.closed_set ? 'closed' : 'open'} />
            <SummaryRow k="queries" v={String(queryCount)} />
            <SummaryRow k="paths" v={String(pathCount)} />
          </div>

          {pb.decision && pb.decision.criteria_refs.length > 0 && (
            <>
              <h4>advisory criteria ({pb.decision.criteria_refs.length})</h4>
              <div className="pb-rail-list">
                {pb.decision.criteria_refs.map((c) => (
                  <button key={c} className="pb-rail-item criterion" onClick={() => navigate({ kind: 'axiom', id: c })}>
                    {c}
                  </button>
                ))}
              </div>
            </>
          )}

          <h4>tools — {pb.role} can call ({railTools.length})</h4>
          <div className="pb-rail-list">
            {railTools.length === 0 && <span className="pb-rail-empty">no tools available to this role</span>}
            {railTools.map((t) => (
              <button key={t.name} className="pb-rail-item tool" onClick={() => navigate({ kind: 'tool', id: t.name })}>
                <span className={`pb-tool-cat ${t.category ?? ''}`}>{t.category ?? 'tool'}</span>
                {t.name}
              </button>
            ))}
          </div>

          {otherTools.length > 0 && (
            <>
              <h4>other tools ({otherTools.length})</h4>
              <div className="pb-rail-list">
                {otherTools.map((t) => (
                  <button key={t.name} className="pb-rail-item tool muted" onClick={() => navigate({ kind: 'tool', id: t.name })}>
                    <span className={`pb-tool-cat ${t.category ?? ''}`}>{t.category ?? 'tool'}</span>
                    {t.name}
                  </button>
                ))}
              </div>
            </>
          )}

          <div className="pb-note">
            <span className="pb-note-label">why this view</span>
            A playbook scaffolds context assembly and the choice space for a
            situation — it never ranks the resolution paths. The fan-out reads
            left→right: trigger and input on the left, the typed queries and the
            resolution options on the right. Tools are the deterministic reads
            the anchored role's agent can make while reasoning.
          </div>
        </aside>
      </Panel>
      <PanelResizeHandle className="pb-resize-handle" />
      <Panel defaultSize={74} minSize={40} className="pb-canvas-panel">
        <div className="pb-canvas">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.16 }}
            minZoom={0.3}
            maxZoom={2}
            panOnDrag
            zoomOnScroll
            nodesDraggable={false}
            nodesConnectable={false}
            edgesFocusable={false}
            selectNodesOnDrag={false}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
          >
            <Controls showInteractive={false} position="bottom-right" />
          </ReactFlow>
          <Legend />
        </div>
      </Panel>
    </PanelGroup>
  );
}

function SummaryRow({ k, v, onClick }: { k: string; v: string; onClick?: () => void }) {
  return (
    <div>
      <span className="pb-summary-k">{k}</span>
      {onClick ? (
        <button className="pb-summary-v link" onClick={onClick}>
          {v}
        </button>
      ) : (
        <span className="pb-summary-v">{v}</span>
      )}
    </div>
  );
}

function Legend() {
  const items: Array<[string, string]> = [
    ['source', 'trigger / anchor / input'],
    ['query', 'context assembly'],
    ['resolution', 'selects one of'],
    ['effect', 'always fires'],
  ];
  return (
    <div className="pb-legend" aria-hidden>
      {items.map(([variant, label]) => (
        <span key={variant} className="pb-legend-item">
          <span className={`pb-legend-swatch ${variant}`} />
          {label}
        </span>
      ))}
    </div>
  );
}
