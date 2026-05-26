import { create } from 'zustand';
import { fetchDiff, fetchGitStatus } from '../api/client';
import type {
  DiffKind,
  DiffPayload,
  DiffStatus,
  ElementChange,
  GitStatus,
  KindDelta,
} from '../api/types';

/**
 * Phase-3 diff slice. Holds diff payload + git-status side by side because
 * both feed the top-bar BranchBadge and ambient gutters and are loaded
 * together. Kept off `store/ontology.ts` so a diff refetch doesn't
 * disturb the selection / breadcrumb stack.
 */

export type StatusIndex = Partial<Record<DiffKind, Map<string, DiffStatus>>>;
export type ChangeIndex = Partial<Record<DiffKind, Map<string, ElementChange>>>;

interface DiffState {
  diff: DiffPayload | null;
  gitStatus: GitStatus | null;
  loading: boolean;
  error: string | null;
  base: string;
  /** Per-kind, per-name → status map. Built from `diff.kinds` once on load
   * so render loops can do O(1) lookups instead of array.find. */
  statusIndex: StatusIndex;
  /** Per-kind, per-name → ElementChange map. Empty for added/removed entries. */
  changeIndex: ChangeIndex;
  load: (base?: string) => Promise<void>;
}

export const useDiff = create<DiffState>((set, get) => ({
  diff: null,
  gitStatus: null,
  loading: false,
  error: null,
  base: 'HEAD',
  statusIndex: {},
  changeIndex: {},
  load: async (base) => {
    const ref = base ?? get().base ?? 'HEAD';
    set({ loading: true, error: null, base: ref });
    try {
      const [diff, gitStatus] = await Promise.all([fetchDiff(ref), fetchGitStatus()]);
      const statusIndex = buildStatusIndex(diff);
      const changeIndex = buildChangeIndex(diff);
      set({ diff, gitStatus, statusIndex, changeIndex, loading: false });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : String(e), loading: false });
    }
  },
}));

function buildStatusIndex(diff: DiffPayload): StatusIndex {
  const out: StatusIndex = {};
  (Object.entries(diff.kinds) as Array<[DiffKind, KindDelta]>).forEach(([kind, delta]) => {
    const m = new Map<string, DiffStatus>();
    delta.added.forEach((n) => m.set(n, 'added'));
    delta.removed.forEach((n) => m.set(n, 'removed'));
    delta.changed.forEach((c) => m.set(c.name, 'changed'));
    out[kind] = m;
  });
  return out;
}

function buildChangeIndex(diff: DiffPayload): ChangeIndex {
  const out: ChangeIndex = {};
  (Object.entries(diff.kinds) as Array<[DiffKind, KindDelta]>).forEach(([kind, delta]) => {
    const m = new Map<string, ElementChange>();
    delta.changed.forEach((c) => m.set(c.name, c));
    out[kind] = m;
  });
  return out;
}

/** Lookup helpers — small, allocation-free, suited for use inside render. */
export function diffStatus(idx: StatusIndex, kind: DiffKind, name: string): DiffStatus | null {
  return idx[kind]?.get(name) ?? null;
}

export function elementChange(idx: ChangeIndex, kind: DiffKind, name: string): ElementChange | null {
  return idx[kind]?.get(name) ?? null;
}
