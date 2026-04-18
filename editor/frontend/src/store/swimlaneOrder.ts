import { useEffect, useSyncExternalStore } from 'react';
import { DOMAINS } from '../config/domains';

const STORAGE_KEY = 'editor.swimlaneOrder';
const DEFAULT_ORDER = DOMAINS.map((d) => d.id);

let order: string[] = readOrder();
const listeners = new Set<() => void>();

function readOrder(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_ORDER;
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed) || !parsed.every((v) => typeof v === 'string')) return DEFAULT_ORDER;
    return sanitize(parsed as string[]);
  } catch {
    return DEFAULT_ORDER;
  }
}

function sanitize(input: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const id of input) {
    if (!seen.has(id)) {
      out.push(id);
      seen.add(id);
    }
  }
  for (const id of DEFAULT_ORDER) {
    if (!seen.has(id)) {
      out.push(id);
      seen.add(id);
    }
  }
  return out;
}

function persist(): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(order));
  } catch {
    /* storage unavailable — fall through */
  }
}

function notify(): void {
  for (const listener of listeners) listener();
}

export function moveLane(id: string, direction: -1 | 1): void {
  const idx = order.indexOf(id);
  if (idx < 0) return;
  const target = idx + direction;
  if (target < 0 || target >= order.length) return;
  const next = order.slice();
  next[idx] = order[target]!;
  next[target] = order[idx]!;
  order = next;
  persist();
  notify();
}

export function resetLaneOrder(): void {
  order = DEFAULT_ORDER.slice();
  persist();
  notify();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot(): string[] {
  return order;
}

export function useSwimlaneOrder(): string[] {
  const value = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) {
        order = readOrder();
        notify();
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);
  return value;
}
