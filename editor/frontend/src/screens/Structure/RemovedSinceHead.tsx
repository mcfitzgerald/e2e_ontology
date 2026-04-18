import type { DiffKind, DiffPayload } from '../../api/types';
import { useDiff } from '../../store/diff';

/**
 * Banner above the canvas that lists elements removed in the working copy
 * vs. the diff base. Removed elements aren't in `/api/ontology` so we can't
 * paint them in their swimlanes — surfacing them here keeps the loss
 * visible without ghosting them into the layout.
 */
export function RemovedSinceHead() {
  const diff = useDiff((s) => s.diff);
  if (!diff) return null;

  const removed = collectRemoved(diff);
  if (removed.length === 0) return null;

  return (
    <div className="removed-since-head" role="status">
      <span className="removed-since-head-label">removed since {diff.base}</span>
      {removed.map((r) => (
        <span key={`${r.kind}/${r.name}`} className="removed-since-head-chip" title={`${r.kind}: ${r.name}`}>
          <span className="removed-since-head-chip-kind">{labelForKind(r.kind)}</span>
          {r.name}
        </span>
      ))}
    </div>
  );
}

function collectRemoved(diff: DiffPayload): Array<{ kind: DiffKind; name: string }> {
  const out: Array<{ kind: DiffKind; name: string }> = [];
  (Object.entries(diff.kinds) as Array<[DiffKind, { removed: string[] }]>).forEach(([kind, delta]) => {
    delta.removed.forEach((name) => out.push({ kind, name }));
  });
  return out;
}

function labelForKind(kind: DiffKind): string {
  switch (kind) {
    case 'roles':
      return 'role';
    case 'flows':
      return 'flow';
    case 'events':
      return 'event';
    case 'state_machines':
      return 'fsm';
    case 'entities':
      return 'entity';
    case 'enums':
      return 'enum';
    case 'warnings':
      return 'warn';
  }
}
