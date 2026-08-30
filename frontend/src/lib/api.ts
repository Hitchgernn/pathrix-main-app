import type { BBox, LayerMeta, MissionFeature } from "./types";

const base = import.meta.env.VITE_API_BASE ?? "";

/** The layer catalogue is served from the backend, but the design's row
 *  presentation (name, swatch, meta line) is the visual contract — see
 *  lib/sample.ts LAYER_ROWS. This only tells us which rows are actually live. */
export async function fetchLayers(): Promise<LayerMeta[]> {
  const response = await fetch(`${base}/api/layers`);
  if (!response.ok) throw new Error(`GET /api/layers → ${response.status}`);
  return (await response.json()) as LayerMeta[];
}

/** Bbox-scoped features for one layer — 501s for a layer id with no query
 *  wired yet (`app/api/layers.py`), which the caller treats the same as a
 *  network failure: skip it, never break the map over it. */
export async function fetchLayerFeatures(
  layerId: string,
  bbox: BBox,
  limit = 200,
): Promise<MissionFeature[]> {
  const params = new URLSearchParams({
    min_lon: String(bbox.min_lon),
    min_lat: String(bbox.min_lat),
    max_lon: String(bbox.max_lon),
    max_lat: String(bbox.max_lat),
    limit: String(limit),
  });
  const response = await fetch(`${base}/api/layers/${layerId}/features?${params}`);
  if (!response.ok) throw new Error(`GET /api/layers/${layerId}/features → ${response.status}`);
  return (await response.json()) as MissionFeature[];
}
