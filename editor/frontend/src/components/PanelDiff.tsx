import type { DiffKind, DiffStatus, FieldChange } from '../api/types';
import { diffStatus, elementChange, useDiff } from '../store/diff';
import type { SelectionKind } from '../store/ontology';

/**
 * Diff banner at the top of any context panel. Renders if the selected
 * element is in the diff. Mockup lines 325–335 + 1268–1277 + 1349–1355.
 *
 * Mockup uses var(--font-hand) for the caret glyph. We swap that to plain
 * JetBrains Mono per AGENTS.md (no handwritten fonts) — flagged as
 * intentional drift in editor/parity_reviews/03_diff_gutters.md.
 */
export function PanelDiff({ selectionKind, name }: { selectionKind: SelectionKind; name: string }) {
  const statusIndex = useDiff((s) => s.statusIndex);
  const changeIndex = useDiff((s) => s.changeIndex);
  const diff = useDiff((s) => s.diff);

  const kind = mapKind(selectionKind);
  if (!kind) return null;
  const status = diffStatus(statusIndex, kind, name);
  if (!status) return null;

  const change = status === 'changed' ? elementChange(changeIndex, kind, name) : null;
  const baseLabel = diff?.base ?? 'HEAD';

  return (
    <div className={`panel-diff ${status}`} role="note">
      <span className="panel-diff-caret">{caretFor(status)}</span>
      <span className="panel-diff-summary">{summary(status, change?.changes.length ?? 0, baseLabel)}</span>
      {change && change.changes.length > 0 && <FieldList changes={change.changes} />}
    </div>
  );
}

function caretFor(status: DiffStatus): string {
  switch (status) {
    case 'added':
      return '+';
    case 'removed':
      return '−';
    case 'changed':
      return '~';
  }
}

function summary(status: DiffStatus, fieldCount: number, base: string): string {
  switch (status) {
    case 'added':
      return ` added since ${base}`;
    case 'removed':
      return ` removed since ${base}`;
    case 'changed': {
      const word = fieldCount === 1 ? 'field' : 'fields';
      return ` ${fieldCount} ${word} modified since ${base}`;
    }
  }
}

function FieldList({ changes }: { changes: FieldChange[] }) {
  return (
    <ul className="panel-diff-fields">
      {changes.map((c) => (
        <li key={c.path}>
          <code className="panel-diff-path">{c.path}</code>
          <span className="panel-diff-arrow">→</span>
          <RenderValue value={c.before} variant="del" />
          <span className="panel-diff-arrow">⇒</span>
          <RenderValue value={c.after} variant="ins" />
        </li>
      ))}
    </ul>
  );
}

function RenderValue({ value, variant }: { value: unknown; variant: 'ins' | 'del' }) {
  const Tag = variant;
  const display = formatValue(value);
  return <Tag className={`panel-diff-${variant}`} title={display}>{display}</Tag>;
}

function formatValue(value: unknown): string {
  if (value == null) return '∅';
  if (typeof value === 'string') {
    return value.length > 60 ? `"${value.slice(0, 57)}…"` : `"${value}"`;
  }
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  try {
    const json = JSON.stringify(value);
    return json.length > 60 ? `${json.slice(0, 57)}…` : json;
  } catch {
    return String(value);
  }
}

function mapKind(s: SelectionKind): DiffKind | null {
  switch (s) {
    case 'role':
      return 'roles';
    case 'flow':
      return 'flows';
    case 'event':
      return 'events';
    case 'state_machine':
      return 'state_machines';
    case 'entity':
      return 'entities';
    case 'axiom':
      // Axioms aren't a top-level diff kind — they're nested in flows. Field
      // paths surface them via 'axioms.<name>.severity' inside the parent
      // flow's change list. Skip the panel-diff banner for axioms.
      return null;
  }
}
