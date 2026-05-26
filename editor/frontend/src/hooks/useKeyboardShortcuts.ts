import { useEffect } from 'react';
import { useOntology } from '../store/ontology';
import { useScreen, type ScreenId } from '../store/screen';

const SCREEN_KEYS: Record<string, ScreenId> = {
  g: 'structure',
  c: 'cascade',
  f: 'fsm',
};

// Don't hijack keys while the user is typing into form controls (cascade
// picker, FSM picker, depth slider, range inputs, future filter rail).
function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if (target.isContentEditable) return true;
  return false;
}

export function useKeyboardShortcuts() {
  const setScreen = useScreen((s) => s.setScreen);
  const navigate = useOntology((s) => s.navigate);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (isEditableTarget(e.target)) return;

      const key = e.key.toLowerCase();
      const screen = SCREEN_KEYS[key];
      if (screen) {
        e.preventDefault();
        setScreen(screen);
        return;
      }

      if (e.key === 'Escape') {
        e.preventDefault();
        navigate(null);
        return;
      }

      if (e.key === '/') {
        e.preventDefault();
        // Forward-keeps the binding for when the filter rail lands; no
        // search input mounts yet, so this surfaces the intent only.
        console.debug('[shortcut] / — search not yet wired (filter rail pending)');
        return;
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [setScreen, navigate]);
}
