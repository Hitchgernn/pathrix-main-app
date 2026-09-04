import { bboxKey, memo, SESSION, snapBBox } from "./cache";
import type { Place, PlaceHit } from "./places";
import { placeFromHit } from "./places";
import type { BBox, LayerMeta, MissionFeature } from "./types";

const base = import.meta.env.VITE_API_BASE ?? "";

const FEATURES_TTL_MS = 2 * 60_000;
const SEARCH_TTL_MS = 5 * 60_000;

/** The layer catalogue is served from the backend, but the design's row
 *  presentation (name, swatch, meta line) is the visual contract — see
 *  lib/sample.ts LAYER_ROWS. This only tells us which rows are actually live. */
export function fetchLayers(): Promise<LayerMeta[]> {
  // A static catalogue in the backend; once per session is plenty.
  return memo("layers", SESSION, async () => {
    const response = await fetch(`${base}/api/layers`);
    if (!response.ok) throw new Error(`GET /api/layers → ${response.status}`);
    return (await response.json()) as LayerMeta[];
  });
}

/** Bbox-scoped features for one layer — 501s for a layer id with no query
 *  wired yet (`app/api/layers.py`), which the caller treats the same as a
 *  network failure: skip it, never break the map over it. */
export function fetchLayerFeatures(
  layerId: string,
  bbox: BBox,
  limit = 200,
): Promise<MissionFeature[]> {
  // Snapped outward and fetched at the snapped extent, so the cached answer
  // covers every viewport that lands in the same cell. Panning within a cell
  // costs nothing; the debounce in MapCanvas never could have removed those
  // repeats, because each settle produced a genuinely different bbox.
  const area = snapBBox(bbox);
  return memo(`features:${layerId}:${limit}:${bboxKey(area)}`, FEATURES_TTL_MS, async () => {
    const params = new URLSearchParams({
      min_lon: String(area.min_lon),
      min_lat: String(area.min_lat),
      max_lon: String(area.max_lon),
      max_lat: String(area.max_lat),
      limit: String(limit),
    });
    const response = await fetch(`${base}/api/layers/${layerId}/features?${params}`);
    if (!response.ok) throw new Error(`GET /api/layers/${layerId}/features → ${response.status}`);
    return (await response.json()) as MissionFeature[];
  });
}

/** Location search — mirrored halte/pangkalan/mission rows first, then geocoded
 *  addresses (`backend/app/api/search.py`). Same error discipline as the layer
 *  calls: a failure surfaces as no results, never as a broken screen. */
export function searchPlaces(query: string, limit = 8): Promise<Place[]> {
  const trimmed = query.trim();
  if (!trimmed) return Promise.resolve([]);
  // Backspacing to a query already typed is the common case, so it should not
  // cost a round trip.
  return memo(`geocode:${trimmed.toLowerCase()}:${limit}`, SEARCH_TTL_MS, async () => {
    const params = new URLSearchParams({ q: trimmed, limit: String(limit) });
    const response = await fetch(`${base}/api/geocode?${params}`);
    if (!response.ok) throw new Error(`GET /api/geocode → ${response.status}`);
    return ((await response.json()) as PlaceHit[]).map(placeFromHit);
  });
}
