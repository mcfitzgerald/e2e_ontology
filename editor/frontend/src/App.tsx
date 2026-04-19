import { useEffect } from 'react';
import { useOntology } from './store/ontology';
import { useDiff } from './store/diff';
import { useScreen } from './store/screen';
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

  useEffect(() => {
    load();
    loadDiff();
  }, [load, loadDiff]);

  useEffect(() => {
    const onFocus = () => loadDiff();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [loadDiff]);

  return (
    <div className="app">
      <SketchyFilters />
      <AppHeader />
      <main className="app-main">
        {loading && <LoadingState />}
        {error && <ErrorState message={error} />}
        {data && (
          <div className="app-canvas-with-rail">
            <ScreenRouter data={data} />
            <ContextPanel data={data} />
          </div>
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
