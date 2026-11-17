import { SetStateAction, useCallback, useSyncExternalStore } from 'react';

/**
 * State that survives a component unmounting, for as long as the app window
 * is open.
 *
 * Home only mounts the active tab, so switching tabs (or opening Settings)
 * used to throw away loaded articles and results. useSessionState works like
 * useState, but the value lives in this module instead of in the component,
 * so a tab finds its state again when it comes back.
 *
 * Nothing is written to disk: closing the app or reloading the window
 * (Ctrl+R) clears it.
 *
 * A request that finishes while its tab is hidden still saves its result
 * here, so the result is waiting when the tab is opened again.
 */

const values = new Map<string, unknown>();
const listeners = new Map<string, Set<() => void>>();

const notify = (key: string) => {
  listeners.get(key)?.forEach((listener) => listener());
};

export function useSessionState<T>(
  key: string,
  initialValue: T | (() => T),
): [T, (next: SetStateAction<T>) => void] {
  if (!values.has(key)) {
    values.set(
      key,
      typeof initialValue === 'function' ? (initialValue as () => T)() : initialValue,
    );
  }

  const subscribe = useCallback(
    (onChange: () => void) => {
      let keyListeners = listeners.get(key);
      if (!keyListeners) {
        keyListeners = new Set();
        listeners.set(key, keyListeners);
      }
      keyListeners.add(onChange);
      return () => {
        keyListeners?.delete(onChange);
      };
    },
    [key],
  );

  const value = useSyncExternalStore(subscribe, () => values.get(key) as T);

  const setValue = useCallback(
    (next: SetStateAction<T>) => {
      const previous = values.get(key) as T;
      const resolved =
        typeof next === 'function' ? (next as (prev: T) => T)(previous) : next;
      if (Object.is(resolved, previous)) return;
      values.set(key, resolved);
      notify(key);
    },
    [key],
  );

  return [value, setValue];
}

