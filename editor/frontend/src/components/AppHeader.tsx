/*
 * Top bar. Title + version on the left, screen tabs on the right.
 * Only Structure is enabled in Phase 1.
 */

import './AppHeader.css';

export function AppHeader() {
  return (
    <header className="app-header">
      <div className="app-title">
        <span className="title">ontology editor</span>
        <span className="ver">v0.1 · phase 1</span>
      </div>
      <nav className="screen-tabs">
        <button className="active" disabled>
          <span className="num">01</span> structure
        </button>
        <button disabled title="Phase 2">
          <span className="num">02</span> cascade
        </button>
        <button disabled title="Phase 4">
          <span className="num">03</span> authoring
        </button>
        <button disabled title="Phase 4">
          <span className="num">04</span> fsm
        </button>
      </nav>
    </header>
  );
}
