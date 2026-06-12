import { create } from 'zustand';
import { fetchOntology } from '../api/client';
import type { OntologyPayload } from '../api/types';

export type SelectionKind =
  | 'role'
  | 'flow'
  | 'event'
  | 'state_machine'
  | 'entity'
  | 'axiom'
  | 'playbook'
  | 'tool';

export interface Selection {
  kind: SelectionKind;
  id: string;
}

interface OntologyState {
  data: OntologyPayload | null;
  loading: boolean;
  error: string | null;
  history: Selection[];
  selection: Selection | null;
  load: () => Promise<void>;
  /** Push a new selection onto the history stack and focus it. Clears if null. */
  navigate: (sel: Selection | null) => void;
  /** Pop the current selection; returns to the previous or empty if stack exhausts. */
  back: () => void;
  /** Clear history and selection. */
  home: () => void;
  /** Jump to a specific depth in the breadcrumb (0 = oldest, history.length-1 = current). */
  jumpTo: (depth: number) => void;
}

export const useOntology = create<OntologyState>((set) => ({
  data: null,
  loading: false,
  error: null,
  history: [],
  selection: null,
  load: async () => {
    set({ loading: true, error: null });
    try {
      const data = await fetchOntology();
      set({ data, loading: false });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : String(e), loading: false });
    }
  },
  navigate: (sel) =>
    set((state) => {
      if (sel == null) return { history: [], selection: null };
      const top = state.history.at(-1);
      if (top && top.kind === sel.kind && top.id === sel.id) {
        return { selection: sel };
      }
      return { history: [...state.history, sel], selection: sel };
    }),
  back: () =>
    set((state) => {
      if (state.history.length <= 1) return { history: [], selection: null };
      const next = state.history.slice(0, -1);
      return { history: next, selection: next.at(-1) ?? null };
    }),
  home: () => set({ history: [], selection: null }),
  jumpTo: (depth) =>
    set((state) => {
      if (depth < 0 || depth >= state.history.length) return state;
      const next = state.history.slice(0, depth + 1);
      return { history: next, selection: next.at(-1) ?? null };
    }),
}));
