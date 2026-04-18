import { useEffect } from 'react';
import { useOntology } from './store/ontology';
import { SketchyFilters } from './tokens/SketchyFilters';
import { AppHeader } from './components/AppHeader';
import { StructureScreen } from './screens/Structure';
import './App.css';

export default function App() {
  const { data, loading, error, load } = useOntology();

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="app">
      <SketchyFilters />
      <AppHeader />
      <main className="app-main">
        {loading && <LoadingState />}
        {error && <ErrorState message={error} />}
        {data && <StructureScreen data={data} />}
      </main>
    </div>
  );
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
