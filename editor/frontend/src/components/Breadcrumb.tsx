import { useOntology } from '../store/ontology';

const KIND_ICON: Record<string, string> = {
  role: '●',
  flow: '→',
  event: '◆',
  state_machine: '○',
  entity: '▢',
  axiom: '!',
};

export function Breadcrumb() {
  const history = useOntology((s) => s.history);
  const jumpTo = useOntology((s) => s.jumpTo);
  const home = useOntology((s) => s.home);

  if (history.length === 0) return null;

  return (
    <nav className="breadcrumb" aria-label="navigation trail">
      <button className="breadcrumb-home" onClick={home} title="clear selection">
        home
      </button>
      {history.map((sel, i) => {
        const isLast = i === history.length - 1;
        return (
          <span key={`${sel.kind}:${sel.id}:${i}`} className="breadcrumb-item">
            <span className="breadcrumb-sep">›</span>
            {isLast ? (
              <span className="breadcrumb-current">
                <span className="breadcrumb-kind">{KIND_ICON[sel.kind] ?? '·'}</span>
                {sel.id}
              </span>
            ) : (
              <button className="breadcrumb-link" onClick={() => jumpTo(i)}>
                <span className="breadcrumb-kind">{KIND_ICON[sel.kind] ?? '·'}</span>
                {sel.id}
              </button>
            )}
          </span>
        );
      })}
    </nav>
  );
}
