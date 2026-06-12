import { useScreen, type ScreenId } from '../store/screen';
import { BranchBadge } from './BranchBadge';
import './AppHeader.css';

const TABS: Array<{ id: ScreenId | 'authoring'; num: string; label: string; disabled?: boolean; title?: string }> = [
  { id: 'structure', num: '01', label: 'structure' },
  { id: 'cascade', num: '02', label: 'cascade' },
  { id: 'authoring', num: '03', label: 'authoring', disabled: true, title: 'deferred — mockup only' },
  { id: 'fsm', num: '04', label: 'fsm' },
  { id: 'playbook', num: '05', label: 'playbook' },
];

export function AppHeader() {
  const current = useScreen((s) => s.current);
  const setScreen = useScreen((s) => s.setScreen);
  return (
    <header className="app-header">
      <div className="app-title">
        <span className="title">ontology editor</span>
        <span className="ver">v0.1 · phase 4</span>
      </div>
      <BranchBadge />
      <nav className="screen-tabs">
        {TABS.map((t) => {
          const isActive = !t.disabled && t.id === current;
          return (
            <button
              key={t.id}
              className={isActive ? 'active' : ''}
              disabled={t.disabled}
              title={t.title}
              onClick={() => !t.disabled && setScreen(t.id as ScreenId)}
            >
              <span className="num">{t.num}</span> {t.label}
            </button>
          );
        })}
      </nav>
    </header>
  );
}
