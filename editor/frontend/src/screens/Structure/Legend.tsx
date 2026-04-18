/*
 * Bottom-left legend panel. Matches the mockup's Legend component:
 * three flow kinds with their canonical stroke styles, the axiom-severity
 * dot, and the boundary-role marker.
 */

export function Legend() {
  return (
    <aside className="legend">
      <div className="legend-section">
        <h5>flow kinds</h5>
        <div className="legend-row">
          <svg width={50} height={12}>
            <line x1={2} y1={6} x2={44} y2={6} stroke="#5a3b22" strokeWidth={3.2} markerEnd="url(#arrow-material)" />
          </svg>
          <span>material</span>
          <span style={{ color: 'var(--ink-muted)', marginLeft: 'auto' }}>heavy</span>
        </div>
        <div className="legend-row">
          <svg width={50} height={12}>
            <line x1={2} y1={6} x2={44} y2={6} stroke="#3b6a96" strokeWidth={1.4} strokeDasharray="5 3" markerEnd="url(#arrow-information)" />
          </svg>
          <span>information</span>
          <span style={{ color: 'var(--ink-muted)', marginLeft: 'auto' }}>dashed</span>
        </div>
        <div className="legend-row">
          <svg width={50} height={12}>
            <line x1={2} y1={4} x2={44} y2={4} stroke="#b78d2a" strokeWidth={1.4} />
            <line x1={2} y1={8} x2={44} y2={8} stroke="#b78d2a" strokeWidth={1.4} markerEnd="url(#arrow-cash)" />
          </svg>
          <span>cash</span>
          <span style={{ color: 'var(--ink-muted)', marginLeft: 'auto' }}>doubled</span>
        </div>
      </div>
      <div className="legend-section">
        <h5>annotations</h5>
        <div className="legend-row">
          <svg width={18} height={12}>
            <circle cx={9} cy={6} r={5} fill="#c04a3a" stroke="#1a1a1a" strokeWidth={1} />
            <text x={9} y={9} textAnchor="middle" fontSize={7} fontWeight={700} fill="#f7f3ea">!</text>
          </svg>
          <span>blocking axiom</span>
        </div>
        <div className="legend-row">
          <svg width={18} height={12}>
            <rect x={1} y={1} width={16} height={10} fill="var(--paper)" stroke="#1a1a1a" strokeWidth={1.2} strokeDasharray="3 2" rx={1} />
          </svg>
          <span>boundary role</span>
        </div>
        <div className="legend-row">
          <svg width={18} height={12}>
            <circle cx={9} cy={6} r={5} fill="#fff6cf" stroke="#1a1a1a" strokeWidth={1} />
            <text x={9} y={9.5} textAnchor="middle" fontFamily="var(--font-mono)" fontSize={9} fontWeight={700} fill="#1a1a1a">?</text>
          </svg>
          <span>HITL conditional</span>
        </div>
      </div>
    </aside>
  );
}
