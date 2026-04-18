import { create } from 'zustand';
import { fetchOntology } from '../api/client';
import type { OntologyPayload } from '../api/types';

export type Selection =
  | { kind: 'role'; id: string }
  | { kind: 'flow'; id: string }
  | { kind: 'event'; id: string }
  | { kind: 'state_machine'; id: string }
  | { kind: 'entity'; id: string }
  | { kind: 'axiom'; id: string }
  | null;

interface OntologyState {
  data: OntologyPayload | null;
  loading: boolean;
  error: string | null;
  selection: Selection;
  load: () => Promise<void>;
  select: (sel: Selection) => void;
}

export const useOntology = create<OntologyState>((set) => ({
  data: null,
  loading: false,
  error: null,
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
  select: (selection) => set({ selection }),
}));
