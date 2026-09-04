/** In-memory request cache with in-flight de-duplication.
 *
 *  Generalises what `lib/photos.ts` already does by hand, including its one
 *  hard-won rule: **only a real answer is cached**. A rejected promise is
 *  dropped from the map entirely, so a transient failure is retried on the next
 *  call rather than being remembered as the truth for the rest of the TTL.
 *
 *  Deliberately memory-only. `localStorage` is for things that should outlive
 *  the tab — the profile, saved places, place photographs. Route and layer data
 *  is not that: stale transit data is worse than a request.
 */

interface Entry<T> {
  value: Promise<T>;
  /** null while the promise is pending; set once it resolves. */
  expiresAt: number | null;
}

const store = new Map<string, Entry<unknown>>();

/** Cache for the whole session. Use for data that cannot change under us. */
export const SESSION = Number.POSITIVE_INFINITY;

export function memo<T>(key: string, ttlMs: number, fn: () => Promise<T>): Promise<T> {
  const hit = store.get(key) as Entry<T> | undefined;
  // A pending entry (expiresAt null) is joined rather than re-issued: two
  // components asking for the same thing in the same tick make one request.
  if (hit && (hit.expiresAt === null || hit.expiresAt > Date.now())) {
    return hit.value;
  }

  const entry: Entry<T> = { value: fn(), expiresAt: null };
  store.set(key, entry);

  entry.value.then(
    () => {
      // Re-read: a clear() or a newer entry may have replaced this one while
      // the request was in flight, and we must not resurrect it.
      if (store.get(key) === entry) {
        entry.expiresAt = ttlMs === SESSION ? SESSION : Date.now() + ttlMs;
      }
    },
    () => {
      if (store.get(key) === entry) store.delete(key);
    },
  );

  return entry.value;
}

/** Drops everything, or everything under one prefix. */
export function clearCache(prefix?: string): void {
  if (prefix === undefined) {
    store.clear();
    return;
  }
  for (const key of store.keys()) {
    if (key.startsWith(prefix)) store.delete(key);
  }
}

/** Snaps a viewport onto a fixed grid, rounding **outward** so the snapped box
 *  is always a superset of what is on screen.
 *
 *  Outward matters. Rounding to the nearest cell would produce a key for a box
 *  we never actually requested, and a later view landing on the same key would
 *  read data that does not reach its edges — missing markers, intermittently,
 *  which is the worst kind of bug to chase. Fetching the snapped box instead
 *  means the cached answer covers every view that snaps to it, and the margin
 *  is free prefetch.
 *
 *  0.01° is roughly 1.1km, so the key survives a pan of about half a screen at
 *  city zoom. */
export function snapBBox<T extends { min_lon: number; min_lat: number; max_lon: number; max_lat: number }>(
  bbox: T,
  step = 0.01,
): { min_lon: number; min_lat: number; max_lon: number; max_lat: number } {
  const floor = (v: number) => Math.floor(v / step) * step;
  const ceil = (v: number) => Math.ceil(v / step) * step;
  return {
    min_lon: floor(bbox.min_lon),
    min_lat: floor(bbox.min_lat),
    max_lon: ceil(bbox.max_lon),
    max_lat: ceil(bbox.max_lat),
  };
}

/** Stable, short key for a snapped box. */
export const bboxKey = (b: { min_lon: number; min_lat: number; max_lon: number; max_lat: number }): string =>
  [b.min_lon, b.min_lat, b.max_lon, b.max_lat].map((v) => v.toFixed(2)).join(",");
