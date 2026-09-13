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
const pinLayerId = (layerId: string) => `pathrix-mission-${layerId}-pin`;
const pinImageId = (color: string) => `pathrix-pin-${color.replace("#", "")}`;

/** setStyle drops every source/layer the same way it does for the route —
 *  cached here so `reapplyMissionLayers` can redraw everything currently on
 *  once the incoming style finishes loading. */
const lastDrawn = new Map<
  string,
  { features: MissionFeature[]; color: string; reviewedIds: Set<string> }
>();

/** properties.geometry is already GeoJSON (models/mapid.py's Feature) — almost
 *  always a Point, since mission data is survey point data. A feature with any
 *  other geometry type is dropped rather than mis-rendered as a circle.
 *  manual_review is stamped client-side (from /api/layers/manual-reviews, a
 *  separate small fetch — reviewed status lives in its own DB table, never in
 *  a stop's raw, which upsert_transit_stops overwrites wholesale on re-ingest)
 *  so a reviewed stop's marker can be told apart from an auto-matched one's. */
function toFeatureCollection(
  features: MissionFeature[],
  reviewedIds: Set<string>,
): FeatureCollection<Point> {
  return {
    type: "FeatureCollection",
    features: features
      .filter((f): f is MissionFeature & { geometry: Point } => f.geometry.type === "Point")
      .map((f) => ({
        type: "Feature",
        properties: {
          external_id: f.external_id,
          ...f.properties,
          manual_review: f.external_id != null && reviewedIds.has(f.external_id),
        },
        geometry: f.geometry,
      })),
  };
}

function ensureCircleLayer(map: MapLibreMap, layerId: string, color: string): void {
  if (map.getLayer(circleLayerId(layerId))) return;
  map.addLayer({
    id: circleLayerId(layerId),
    type: "circle",
    // A manually-reviewed stop gets the pin layer below instead of the flat
    // dot — never both stacked on the same point.
    filter: ["!=", ["get", "manual_review"], true],
    source: sourceId(layerId),
    paint: {
      // Markers grow with zoom: at city scale they are dots in a field, at
      // street scale they are targets you can actually hit with a thumb.
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 11, 4, 14, 6, 17, 9],
      "circle-color": color,
      "circle-stroke-width": 1.6,
      "circle-stroke-color": "#ffffff",
      "circle-opacity": 0.92,
    },
  });

  // The markers are tappable (MapCanvas opens the place sheet), so they say so
  // on a pointer device.
  const id = circleLayerId(layerId);
  map.on("mouseenter", id, () => {
    map.getCanvas().style.cursor = "pointer";
  });
  map.on("mouseleave", id, () => {
    map.getCanvas().style.cursor = "";
  });
}

/** A filled teardrop pin (SelectedPin's shape, recolored per layer) rather than
 *  a new hue — docs/DESIGN.md licenses a solid-filled map-category colour as a
 *  pin shape, just never as a thin line or label. Cached per colour since
 *  there are only a handful of layer colours across the whole app. */
function loadPinImage(color: string): Promise<HTMLImageElement> {
  const svg =
    '<svg xmlns="http://www.w3.org/2000/svg" width="30" height="38" viewBox="0 0 30 38">' +
    '<ellipse cx="15" cy="35" rx="6" ry="2.2" fill="rgba(16,30,42,.22)"/>' +
    '<path d="M15 2c-6.1 0-11 4.9-11 11 0 8 9.9 18.4 10.3 18.8a1 1 0 0 0 1.4 0C16.1 31.4 26 21 26 13c0-6.1-4.9-11-11-11Z" ' +
    `fill="${color}" stroke="#fff" stroke-width="2.4"/>` +
    '<circle cx="15" cy="13" r="4" fill="#fff"/></svg>';
  const url = `data:image/svg+xml;base64,${btoa(svg)}`;
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("pin svg failed to load"));
    img.src = url;
  });
}

function ensurePinLayer(map: MapLibreMap, layerId: string, color: string): void {
  const id = pinLayerId(layerId);
  if (map.getLayer(id)) return;
  const imageId = pinImageId(color);
  const addLayer = () => {
    if (map.getLayer(id)) return;
    map.addLayer({
      id,
      type: "symbol",
      source: sourceId(layerId),
      filter: ["==", ["get", "manual_review"], true],
      layout: {
        "icon-image": imageId,
        "icon-size": 0.9,
        "icon-anchor": "bottom",
        "icon-allow-overlap": true,
      },
    });
    map.on("mouseenter", id, () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", id, () => {
      map.getCanvas().style.cursor = "";
    });
  };
  if (map.hasImage(imageId)) {
    addLayer();
    return;
  }
  void loadPinImage(color)
    .then((img) => {
      if (!map.hasImage(imageId)) map.addImage(imageId, img);
      addLayer();
    })
    .catch(() => undefined); // a failed pin icon must never break the map
}

export function syncMissionLayer(
  map: MapLibreMap,
  layerId: string,
  features: MissionFeature[],
  color: string,
  reviewedIds: Set<string> = new Set(),
): void {
  lastDrawn.set(layerId, { features, color, reviewedIds });
  setGeoJson(map, sourceId(layerId), toFeatureCollection(features, reviewedIds));
  ensureCircleLayer(map, layerId, color);
  ensurePinLayer(map, layerId, color);
}

export function removeMissionLayer(map: MapLibreMap, layerId: string): void {
  lastDrawn.delete(layerId);
  if (map.getLayer(pinLayerId(layerId))) map.removeLayer(pinLayerId(layerId));
  if (map.getLayer(circleLayerId(layerId))) map.removeLayer(circleLayerId(layerId));
  if (map.getSource(sourceId(layerId))) map.removeSource(sourceId(layerId));
}

/** Re-draws every currently-toggled-on mission layer after a basemap swap. */
export function reapplyMissionLayers(map: MapLibreMap): void {
  for (const [layerId, { features, color, reviewedIds }] of lastDrawn) {
    setGeoJson(map, sourceId(layerId), toFeatureCollection(features, reviewedIds));
    ensureCircleLayer(map, layerId, color);
    ensurePinLayer(map, layerId, color);
  }
}
