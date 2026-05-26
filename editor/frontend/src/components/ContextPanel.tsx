import type { OntologyPayload } from '../api/types';
import { useOntology } from '../store/ontology';
import { Breadcrumb } from './Breadcrumb';
import { PanelDiff } from './PanelDiff';
import { AxiomPanel } from './panels/AxiomPanel';
import { EntityPanel } from './panels/EntityPanel';
import { EventPanel } from './panels/EventPanel';
import { FSMPanel } from './panels/FSMPanel';
import { FlowPanel } from './panels/FlowPanel';
import { RolePanel } from './panels/RolePanel';
import {
  entityByName,
  eventByName,
  flowByName,
  fsmByName,
  roleByName,
} from './panels/helpers';
import './ContextPanel.css';

interface Props {
  data: OntologyPayload;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}

/**
 * Right-rail context panel. The outer Panel's width is owned by App via
 * react-resizable-panels; `collapsed` here just flips the rendered content
 * between the expanded aside and the slim expand affordance. App mirrors
 * this state onto the Panel's imperative collapse/expand API.
 */
export function ContextPanel({ data, collapsed, onToggleCollapsed }: Props) {
  const selection = useOntology((s) => s.selection);
  const navigate = useOntology((s) => s.navigate);

  if (collapsed) {
    return (
      <button
        className="context-panel-collapsed"
        onClick={onToggleCollapsed}
        title="expand context panel"
        aria-label="expand context panel"
      >
        <span className="context-panel-collapsed-chevron">‹</span>
        <span className="context-panel-collapsed-label">context</span>
      </button>
    );
  }

  return (
    <aside className="context-panel" aria-label="context">
      <div className="context-panel-controls">
        <Breadcrumb />
        <button
          className="context-panel-collapse-btn"
          onClick={onToggleCollapsed}
          title="collapse context panel"
          aria-label="collapse context panel"
        >
          ›
        </button>
      </div>
      {selection ? (
        <>
          <PanelDiff selectionKind={selection.kind} name={selection.id} />
          <PanelBody />
        </>
      ) : (
        <EmptyState />
      )}
    </aside>
  );

  function PanelBody() {
    if (!selection) return null;
    switch (selection.kind) {
      case 'role': {
        const role = roleByName(data, selection.id);
        return role ? <RolePanel role={role} data={data} onNavigate={navigate} /> : <NotFound kind="role" id={selection.id} />;
      }
      case 'flow': {
        const flow = flowByName(data, selection.id);
        return flow ? <FlowPanel flow={flow} data={data} onNavigate={navigate} /> : <NotFound kind="flow" id={selection.id} />;
      }
      case 'event': {
        const event = eventByName(data, selection.id);
        return event ? <EventPanel event={event} data={data} onNavigate={navigate} /> : <NotFound kind="event" id={selection.id} />;
      }
      case 'state_machine': {
        const fsm = fsmByName(data, selection.id);
        return fsm ? <FSMPanel fsm={fsm} data={data} onNavigate={navigate} /> : <NotFound kind="state machine" id={selection.id} />;
      }
      case 'entity': {
        const entity = entityByName(data, selection.id);
        return entity ? <EntityPanel entity={entity} data={data} onNavigate={navigate} /> : <NotFound kind="entity" id={selection.id} />;
      }
      case 'axiom':
        return <AxiomPanel axiomName={selection.id} data={data} onNavigate={navigate} />;
      default:
        return null;
    }
  }
}

function EmptyState() {
  return (
    <div className="context-empty">
      <p className="context-empty-hint">↖</p>
      <p>Click any role, flow, event, or axiom dot in the graph to see details here.</p>
      <p className="context-empty-sub">
        Chips inside the panel navigate to related elements. Use the breadcrumb above to retrace.
      </p>
    </div>
  );
}

function NotFound({ kind, id }: { kind: string; id: string }) {
  return (
    <div className="context-empty">
      <p>No {kind} named <code>{id}</code> in this ontology.</p>
    </div>
  );
}
