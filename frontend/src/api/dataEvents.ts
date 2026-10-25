/**
 * App-wide data-change signal, decoupled from any single component's
 * lifecycle. `request()` in client.ts calls `notifyDataChanged()` after
 * every successful mutating call (POST/PATCH/PUT/DELETE) -- including a
 * LeetCode sync, which is a single long-running request. That matters
 * because a mutation's promise keeps running even if the component that
 * started it (e.g. Settings) has since been navigated away from; this
 * module lets whichever page is mounted *when the mutation resolves* find
 * out and refetch, rather than only refetching on its own mount.
 *
 * Also fires on window focus / tab visibility change, so data changed in
 * another tab (or just sitting in a backgrounded tab) gets picked up
 * without requiring a manual reload.
 */

type Listener = () => void;
const listeners = new Set<Listener>();

export function notifyDataChanged() {
  listeners.forEach((l) => l());
}

export function subscribeDataChanged(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

if (typeof window !== "undefined") {
  window.addEventListener("focus", notifyDataChanged);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") notifyDataChanged();
  });
}
