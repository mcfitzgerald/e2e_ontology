import { useEffect, useRef } from 'react';
import { Panel, PanelGroup, PanelResizeHandle, type ImperativePanelHandle } from 'react-resizable-panels';
import { useOntology } from './store/ontology';
import { useDiff } from './store/diff';
import { useScreen } from './store/screen';
import { useLocalToggle } from './hooks/useLocalToggle';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import { SketchyFilters } from './tokens/SketchyFilters';
import { AppHeader } from './components/AppHeader';
import { ContextPanel } from './components/ContextPanel';
import { StructureScreen } from './screens/Structure';
import { CascadeScreen } from './screens/Cascade';
import { FSMScreen } from './screens/FSM';
import './App.css';

export default function App() {
  const { data, loading, error, load } = useOntology();
  const loadDiff = useDiff((s) => s.load);
  const [railCollapsed, setRailCollapsed] = useLocalToggle('editor.railCollapsed', false);
  const railPanelRef = useRef<ImperativePanelHandle>(null);
  useKeyboardShortcuts();

  useEffect(() => {
    load();
    loadDiff();
  }, [load, loadDiff]);

  useEffect(() => {
    const onFocus = () => loadDiff();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [loadDiff]);

  // Sync the imperative panel API to the controlled collapsed state. Running
  // this in an effect (rather than inline) ensures the ref is attached.
  useEffect(() => {
    const handle = railPanelRef.current;
    if (!handle) return;
    if (railCollapsed) handle.collapse();
    else handle.expand();
  }, [railCollapsed]);

  return (
    <div className="app">
      <SketchyFilters />
      <AppHeader />
      <main className="app-main">
        {loading && <LoadingState />}
        {error && <ErrorState message={error} />}
        {data && (
          <PanelGroup
            direction="horizontal"
            autoSaveId="editor.layout.outer"
            className="app-canvas-with-rail"
          >
            <Panel defaultSize={72} minSize={40} className="app-canvas-panel">
              <ScreenRouter data={data} />
            </Panel>
            <PanelResizeHandle className="app-resize-handle" />
            <Panel
              ref={railPanelRef}
              defaultSize={28}
              minSize={18}
              maxSize={50}
              collapsible
              collapsedSize={2}
              onCollapse={() => setRailCollapsed(true)}
              onExpand={() => setRailCollapsed(false)}
              className="app-rail-panel"
            >
              <ContextPanel
                data={data}
                collapsed={railCollapsed}
                onToggleCollapsed={() => setRailCollapsed(!railCollapsed)}
              />
            </Panel>
          </PanelGroup>
        )}
      </main>
    </div>
  );
}

function ScreenRouter({ data }: { data: import('./api/types').OntologyPayload }) {
  const current = useScreen((s) => s.current);
  switch (current) {
    case 'structure':
      return <StructureScreen data={data} />;
    case 'cascade':
      return <CascadeScreen data={data} />;
    case 'fsm':
      return <FSMScreen data={data} />;
  }
}

function LoadingState() {
  return (
    <div className="status-pane">
      <p>Loading ontology…</p>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="status-pane">
      <h2>Backend unreachable</h2>
      <p>{message}</p>
      <p style={{ color: 'var(--ink-muted)', marginTop: 12 }}>
        Run the backend with:{' '}
        <code>
          cd editor/backend && uv run --with linkml --with pyyaml --with pydantic --with fastapi --with uvicorn
          uvicorn main:app --reload --port 8787
        </code>
      </p>
    </div>
  );
}
