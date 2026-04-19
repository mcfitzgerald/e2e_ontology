import { create } from 'zustand';

export type ScreenId = 'structure' | 'cascade' | 'fsm';

interface ScreenState {
  current: ScreenId;
  setScreen: (s: ScreenId) => void;
}

/**
 * Lightweight screen router. Kept off `store/ontology.ts` so a screen
 * switch doesn't disturb selection / breadcrumb stack — users often want
 * to inspect the same flow across Structure and Cascade views.
 *
 * Authoring (Screen 3) is intentionally absent: the scope guardrail
 * (editor/AGENTS.md) holds it at mockup-only until other screens prove out.
 */
export const useScreen = create<ScreenState>((set) => ({
  current: 'structure',
  setScreen: (s) => set({ current: s }),
}));
