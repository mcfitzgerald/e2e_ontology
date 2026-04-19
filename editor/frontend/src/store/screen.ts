import { create } from 'zustand';

export type ScreenId = 'structure' | 'cascade' | 'fsm';

interface ScreenState {
  current: ScreenId;
  setScreen: (s: ScreenId) => void;
}

const STORAGE_KEY = 'editor.screen';
const VALID: readonly ScreenId[] = ['structure', 'cascade', 'fsm'];

function readInitial(): ScreenId {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw && (VALID as readonly string[]).includes(raw)) return raw as ScreenId;
  } catch {
    /* localStorage unavailable */
  }
  return 'structure';
}

function persist(s: ScreenId) {
  try {
    localStorage.setItem(STORAGE_KEY, s);
  } catch {
    /* ignore */
  }
}

/**
 * Lightweight screen router. Kept off `store/ontology.ts` so a screen
 * switch doesn't disturb selection / breadcrumb stack — users often want
 * to inspect the same flow across Structure and Cascade views.
 *
 * The current screen is persisted to localStorage so reload lands the
 * user back where they were; pair of layout widths (editor.layout.*)
 * already persist on the same principle.
 *
 * Authoring (Screen 3) is intentionally absent: the scope guardrail
 * (editor/AGENTS.md) holds it at mockup-only until other screens prove out.
 */
export const useScreen = create<ScreenState>((set) => ({
  current: readInitial(),
  setScreen: (s) => {
    persist(s);
    set({ current: s });
  },
}));
