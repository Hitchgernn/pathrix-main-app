import type { LayerMeta } from "./types";

const base = import.meta.env.VITE_API_BASE ?? "";

/** The layer catalogue is served from the backend, but the design's row
 *  presentation (name, swatch, meta line) is the visual contract — see
 *  lib/sample.ts LAYER_ROWS. This only tells us which rows are actually live. */
export async function fetchLayers(): Promise<LayerMeta[]> {
  const response = await fetch(`${base}/api/layers`);
  if (!response.ok) throw new Error(`GET /api/layers → ${response.status}`);
  return (await response.json()) as LayerMeta[];
}
