import type { ReactNode } from 'react';

/** Section wrapper used inside every panel body. */
export function Section({ title, children }: { title?: ReactNode; children: ReactNode }) {
  return (
    <section className="panel-section">
      {title && <h4 className="panel-section-title">{title}</h4>}
      {children}
    </section>
  );
}

/** Row of a key/value grid. */
export function Row({ k, children }: { k: string; children: ReactNode }) {
  return (
    <div className="panel-row">
      <span className="panel-row-k">{k}</span>
      <span className="panel-row-v">{children}</span>
    </div>
  );
}

/** Panel header: kind label + element name. */
export function PanelHeader({
  kindLabel,
  name,
  extra,
}: {
  kindLabel: string;
  name: string;
  extra?: ReactNode;
}) {
  return (
    <header className="panel-header">
      <span className="panel-kind">{kindLabel}</span>
      <h3 className="panel-name">{name}</h3>
      {extra}
    </header>
  );
}

/** Callout used for llm_prompt_hint + axiom nl text. */
export function HintBlock({ label, children }: { label: string; children: ReactNode }) {
  return (
    <aside className="panel-hint">
      <div className="panel-hint-label">{label}</div>
      <div className="panel-hint-body">{children}</div>
    </aside>
  );
}

/** Inline list of chips with an optional empty state. */
export function ChipList({ empty, children }: { empty?: string; children: ReactNode[] | ReactNode }) {
  const nodes = Array.isArray(children) ? children : [children];
  if (nodes.length === 0) {
    return <p className="panel-empty">{empty ?? '—'}</p>;
  }
  return <div className="panel-chiplist">{nodes}</div>;
}
