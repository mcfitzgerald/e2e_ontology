import { useEffect, useState } from 'react';
import { SketchyFilters } from './tokens/SketchyFilters';
import { FLOW_STYLES, type FlowKind } from './tokens/flowStyles';

type Health = { status: 'ok'; yaml_path: string; yaml_exists: boolean };

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/health')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setHealth)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <main style={{ padding: '32px 48px', maxWidth: 960 }}>
      <SketchyFilters />
      <h1 style={{ fontWeight: 700, fontSize: 20, marginBottom: 4 }}>
        Ontology Editor{' '}
        <span style={{ fontFamily: 'var(--font-hand)', fontSize: 28, color: 'var(--ink-muted)', display: 'inline-block', transform: 'rotate(-2deg)' }}>
          ~ scaffolding
        </span>
      </h1>
      <p style={{ color: 'var(--ink-muted)', marginTop: 0 }}>
        Phase 0 — toolchain wiring only. Screen 1 (swimlane graph) is next.
      </p>

      <section style={{ marginTop: 32 }}>
        <h2 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--ink-muted)' }}>
          Token smoke-check
        </h2>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginTop: 12 }}>
          {(Object.keys(FLOW_STYLES) as FlowKind[]).map((kind) => {
            const s = FLOW_STYLES[kind];
            return (
              <figure key={kind} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 10 }}>
                <svg width={56} height={14} className="sketchy">
                  {s.doubled ? (
                    <g>
                      <line x1={2} y1={5} x2={48} y2={5} stroke={s.color} strokeWidth={s.strokeWidth} />
                      <line x1={2} y1={9} x2={48} y2={9} stroke={s.color} strokeWidth={s.strokeWidth} markerEnd={s.arrowMarker} />
                    </g>
                  ) : (
                    <line x1={2} y1={7} x2={48} y2={7} stroke={s.color} strokeWidth={s.strokeWidth} strokeDasharray={s.dashArray} markerEnd={s.arrowMarker} />
                  )}
                </svg>
                <figcaption style={{ fontSize: 11 }}>{kind}</figcaption>
              </figure>
            );
          })}
        </div>
      </section>

      <section style={{ marginTop: 32 }}>
        <h2 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--ink-muted)' }}>
          Backend
        </h2>
        {health && (
          <pre style={{ background: 'var(--paper-dark)', padding: 12, marginTop: 8, border: '1px solid var(--ink)', borderRadius: 2 }}>
            {JSON.stringify(health, null, 2)}
          </pre>
        )}
        {error && <p style={{ color: 'var(--axiom-blocking)' }}>Backend unreachable: {error}</p>}
        {!health && !error && <p>Checking /api/health…</p>}
      </section>
    </main>
  );
}
