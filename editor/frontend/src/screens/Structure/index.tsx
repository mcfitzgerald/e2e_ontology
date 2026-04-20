import { useCallback, useMemo, useState } from 'react';
import {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
  type NodeMouseHandler,
  type EdgeMouseHandler,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { Flow, OntologyPayload } from '../../api/types';
import { orderedDomains } from '../../config/domains';
import { diffStatus, useDiff } from '../../store/diff';
import { useOntology, type Selection } from '../../store/ontology';
import { useSwimlaneOrder } from '../../store/swimlaneOrder';
import { computeEdgeBundles } from './edgeGeometry';
import { computeLayout, ROLE_HEIGHT, ROLE_WIDTH } from './layout';
import { FlowEdge, type FlowEdgeData } from './FlowEdge';
import { Legend } from './Legend';
import { RemovedSinceHead } from './RemovedSinceHead';
import { RoleNode, type RoleNodeData } from './RoleNode';
import { SwimlaneBackground } from './SwimlaneBackground';
import './Structure.css';

interface Props {
  data: OntologyPayload;
}

const nodeTypes = { roleNode: RoleNode };
const edgeTypes = { flowEdge: FlowEdge };

export function StructureScreen({ data }: Props) {
  return (
    <ReactFlowProvider>
      <StructureInner data={data} />
    </ReactFlowProvider>
  );
}

function StructureInner({ data }: Props) {
  const selection = useOntology((s) => s.selection);
  const navigate = useOntology((s) => s.navigate);
  const laneOrder = useSwimlaneOrder();
  const statusIndex = useDiff((s) => s.statusIndex);
  const [hovered, setHovered] = useState<string | null>(null);

  const layout = useMemo(() => {
    const usedDomains = new Set<string>();
    data.roles.forEach((r) => {
      if (r.domain) usedDomains.add(r.domain);
    });
    const domains = orderedDomains(usedDomains, laneOrder);
    return computeLayout(data.roles, data.flows, domains);
  }, [data.roles, data.flows, laneOrder]);

  const bundleInfo = useMemo(() => {
    const map = new Map<string, { bundleIndex: number; bundleTotal: number }>();
    for (const b of computeEdgeBundles(data.flows)) {
      map.set(b.flow.name, { bundleIndex: b.bundleIndex, bundleTotal: b.bundleTotal });
    }
    return map;
  }, [data.flows]);

  // Hover-based neighborhood: roles + flows touching the currently hovered
  // role, or both endpoints of the currently hovered flow. Combined with
  // explicit selection into the same {roles, flows} sets so downstream dim
  // logic only cares about "is this element in focus or not".
  const focus = useMemo(() => {
    // Hover over a role node wins for dimming while the pointer is over it;
    // otherwise the explicit selection drives focus.
    if (hovered) return focusFor({ kind: 'role', id: hovered }, data.flows);
    if (selection) return focusFor(selection, data.flows);
    return null;
  }, [hovered, selection, data.flows]);

  const nodes = useMemo<Node<RoleNodeData>[]>(
    () =>
      layout.roles.map(({ role, x, y }) => ({
        id: role.name,
        type: 'roleNode',
        position: { x: x - ROLE_WIDTH / 2, y: y - ROLE_HEIGHT / 2 },
        data: {
          role,
          diffStatus: diffStatus(statusIndex, 'roles', role.name),
          dimmed: focus != null && !focus.roles.has(role.name),
        },
        selected: selection?.kind === 'role' && selection.id === role.name,
        draggable: false,
        selectable: true,
        width: ROLE_WIDTH,
        height: ROLE_HEIGHT,
      })),
    [layout.roles, statusIndex, focus, selection],
  );

  const edges = useMemo<Edge<FlowEdgeData>[]>(
    () =>
      data.flows
        .filter((f) => bundleInfo.has(f.name))
        .map((flow) => {
          const bundle = bundleInfo.get(flow.name)!;
          const isSel = selection?.kind === 'flow' && selection.id === flow.name;
          const dimmed = focus != null && !focus.flows.has(flow.name);
          return {
            id: flow.name,
            source: flow.source_role,
            target: flow.target_role,
            type: 'flowEdge',
            selected: isSel,
            data: {
              flow,
              bundleIndex: bundle.bundleIndex,
              bundleTotal: bundle.bundleTotal,
              diffStatus: diffStatus(statusIndex, 'flows', flow.name),
              dimmed,
            },
          };
        }),
    [data.flows, bundleInfo, statusIndex, selection, focus],
  );

  const onNodeClick = useCallback<NodeMouseHandler>(
    (_, n) => navigate({ kind: 'role', id: n.id }),
    [navigate],
  );
  const onEdgeClick = useCallback<EdgeMouseHandler>(
    (_, e) => navigate({ kind: 'flow', id: e.id }),
    [navigate],
  );
  const onPaneClick = useCallback(() => navigate(null), [navigate]);
  const onNodeMouseEnter = useCallback<NodeMouseHandler>((_, n) => setHovered(n.id), []);
  const onNodeMouseLeave = useCallback(() => setHovered(null), []);

  return (
    <section className="structure">
      <div className="structure-canvas">
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
          panOnScroll={false}
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
          proOptions={{ hideAttribution: false }}
        >
          <SwimlaneBackground swimlanes={layout.swimlanes} width={layout.width} />
          <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#d8cfb8" />
          <Controls showInteractive={false} position="bottom-right" />
        </ReactFlow>
        <RemovedSinceHead />
        <Legend />
      </div>
    </section>
  );
}

interface Focus {
  roles: Set<string>;
  flows: Set<string>;
}

function focusFor(sel: Selection, flows: Flow[]): Focus {
  const roles = new Set<string>();
  const flowSet = new Set<string>();
  if (sel.kind === 'role') {
    roles.add(sel.id);
    for (const f of flows) {
      if (f.source_role === sel.id || f.target_role === sel.id) {
        flowSet.add(f.name);
        roles.add(f.source_role);
        roles.add(f.target_role);
      }
    }
  } else if (sel.kind === 'flow') {
    const f = flows.find((x) => x.name === sel.id);
    if (f) {
      roles.add(f.source_role);
      roles.add(f.target_role);
      flowSet.add(f.name);
    }
  }
  return { roles, flows: flowSet };
}
