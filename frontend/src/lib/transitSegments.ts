import type { FeatureCollection, LineString } from "geojson";
import type { Map as MapLibreMap } from "maplibre-gl";
import { setGeoJson } from "./bridge";

const SOURCE_ID = "pathrix-transit-road-segments";
const LAYER_ID = "pathrix-transit-road-segments-line";
let lastDrawn: FeatureCollection<LineString> | null = null;

function ensureLayer(map: MapLibreMap): void {
  if (map.getLayer(LAYER_ID)) return;
  map.addLayer({
    id: LAYER_ID,
    type: "line",
    source: SOURCE_ID,
    paint: {
      "line-color": "#1f6592",
      "line-width": ["interpolate", ["linear"], ["zoom"], 11, 1.4, 15, 3],
      "line-opacity": 0.66,
      // Dashed geometry communicates estimated OSM road path, not operator
      // supplied bus shape, without introducing a second transit colour.
      "line-dasharray": [1.2, 1.2],
    },
  });
}

export function syncTransitEstimatedSegments(
  map: MapLibreMap,
  segments: FeatureCollection<LineString>,
): void {
  lastDrawn = segments;
  setGeoJson(map, SOURCE_ID, segments);
  ensureLayer(map);
}

export function removeTransitEstimatedSegments(map: MapLibreMap): void {
  lastDrawn = null;
  if (map.getLayer(LAYER_ID)) map.removeLayer(LAYER_ID);
  if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
}

export function reapplyTransitEstimatedSegments(map: MapLibreMap): void {
  if (lastDrawn) syncTransitEstimatedSegments(map, lastDrawn);
}
