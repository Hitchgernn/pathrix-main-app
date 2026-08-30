import type { FeatureCollection, Point } from "geojson";
import type { Map as MapLibreMap } from "maplibre-gl";
import { setGeoJson } from "./bridge";
import type { MissionFeature } from "./types";

/** Viewport-driven mission-data layers (poi/properti), fetched from
 *  /api/layers/{id}/features on toggle and on viewport change.
 *
 *  Kept separate from bridge.ts, which is specifically the agent ui_command
 *  switch — this is a REST-polled overlay, not something the agent drives.
 *  Source/layer ids follow the same pathrix-{concern}-{id} convention bridge.ts
 *  established for routes and highlights. */

const sourceId = (layerId: string) => `pathrix-mission-${layerId}`;
const circleLayerId = (layerId: string) => `pathrix-mission-${layerId}-circle`;

/** setStyle drops every source/layer the same way it does for the route —
 *  cached here so `reapplyMissionLayers` can redraw everything currently on
 *  once the incoming style finishes loading. */
const lastDrawn = new Map<string, { features: MissionFeature[]; color: string }>();

/** properties.geometry is already GeoJSON (models/mapid.py's Feature) — almost
 *  always a Point, since mission data is survey point data. A feature with any
 *  other geometry type is dropped rather than mis-rendered as a circle. */
function toFeatureCollection(features: MissionFeature[]): FeatureCollection<Point> {
  return {
    type: "FeatureCollection",
    features: features
      .filter((f): f is MissionFeature & { geometry: Point } => f.geometry.type === "Point")
      .map((f) => ({
        type: "Feature",
        properties: { external_id: f.external_id, ...f.properties },
        geometry: f.geometry,
      })),
  };
}

function ensureCircleLayer(map: MapLibreMap, layerId: string, color: string): void {
  if (map.getLayer(circleLayerId(layerId))) return;
  map.addLayer({
    id: circleLayerId(layerId),
    type: "circle",
    source: sourceId(layerId),
    paint: {
      "circle-radius": 6,
      "circle-color": color,
      "circle-stroke-width": 1.5,
      "circle-stroke-color": "#e7f0f7",
    },
  });
}

export function syncMissionLayer(
  map: MapLibreMap,
  layerId: string,
  features: MissionFeature[],
  color: string,
): void {
  lastDrawn.set(layerId, { features, color });
  setGeoJson(map, sourceId(layerId), toFeatureCollection(features));
  ensureCircleLayer(map, layerId, color);
}

export function removeMissionLayer(map: MapLibreMap, layerId: string): void {
  lastDrawn.delete(layerId);
  if (map.getLayer(circleLayerId(layerId))) map.removeLayer(circleLayerId(layerId));
  if (map.getSource(sourceId(layerId))) map.removeSource(sourceId(layerId));
}

/** Re-draws every currently-toggled-on mission layer after a basemap swap. */
export function reapplyMissionLayers(map: MapLibreMap): void {
  for (const [layerId, { features, color }] of lastDrawn) {
    setGeoJson(map, sourceId(layerId), toFeatureCollection(features));
    ensureCircleLayer(map, layerId, color);
  }
}
