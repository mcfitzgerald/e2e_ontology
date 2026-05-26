import { useCallback, useEffect, useState } from 'react';

/**
 * Boolean state persisted to localStorage. Safe fallback if storage is
 * unavailable. Syncs across tabs via the `storage` event.
 */
export function useLocalToggle(key: string, initial = false): [boolean, (next?: boolean) => void] {
  const [value, setValue] = useState<boolean>(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw == null) return initial;
      return raw === '1';
    } catch {
      return initial;
    }
  });

  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === key && e.newValue != null) {
        setValue(e.newValue === '1');
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, [key]);

  const toggle = useCallback(
    (next?: boolean) => {
      setValue((prev) => {
        const v = next === undefined ? !prev : next;
        try {
          localStorage.setItem(key, v ? '1' : '0');
        } catch {
          /* ignore */
        }
        return v;
      });
    },
    [key],
  );

  return [value, toggle];
}
