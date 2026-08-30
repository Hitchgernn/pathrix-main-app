import type { GeoJSONSource, Map as MapLibreMap } from "maplibre-gl";
import type { Feature, FeatureCollection, GeoJSON, LineString } from "geojson";
import type { MapPalette } from "./tokens";
import { MODE_KEY } from "./tokens";
import type { Route, ServerMessage, UICommandAction } from "./types";

/** The map ↔ agent bridge — ARCHITECTURE.md §10.2.
 *
 *  `ui_command` handling is a pure switch over a closed action set. Adding an
 *  action means changing models/agent.py and the UICommandAction union
 *  deliberately, not sending a new string and hoping.
 */

const ROUTE_SOURCE = "pathrix-agent-route";
const ROUTE_CASING = "pathrix-agent-route-casing";
const ROUTE_LINE = "pathrix-agent-route-line";
const ROUTE_WALK = "pathrix-agent-route-walk";
const HIGHLIGHT_SOURCE = "pathrix-agent-highlight";
const HIGHLIGHT_LAYER = "pathrix-agent-highlight-circle";

type Command = Extract<ServerMessage, { type: "ui_command" }>;

/** setStyle drops everything the bridge added, so the last route is kept here
 *  and re-applied when the new style finishes loading. */
let lastRoute: Route | null = null;

function flyTo(map: MapLibreMap, payload: Record<string, unknown>): void {
  const { lon, lat, zoom, bbox } = payload as {
    lon?: number;
    lat?: number;
    zoom?: number;
    bbox?: { min_lon: number; min_lat: number; max_lon: number; max_lat: number };
  };
  if (bbox) {
    map.fitBounds(
      [
        [bbox.min_lon, bbox.min_lat],
        [bbox.max_lon, bbox.max_lat],
      ],
      { padding: 64, duration: 900 },
    );
    return;
  }
  if (typeof lon === "number" && typeof lat === "number") {
    map.flyTo({ center: [lon, lat], zoom: zoom ?? map.getZoom(), duration: 900 });
  }
}

/** Adds a GeoJSON source, or updates it in place if it already exists. Shared
 *  with `missionLayers.ts`, which is a separate viewport-driven REST sync, not
 *  an agent `ui_command` — the two never overlap in source ids. */
export function setGeoJson(map: MapLibreMap, id: string, data: GeoJSON): void {
  const existing = map.getSource(id);
  if (existing) {
    (existing as GeoJSONSource).setData(data);
    return;
  }
  map.addSource(id, { type: "geojson", data });
}

/** One LineString per leg, tagged with the design's visual mode family so the
 *  paint expressions can colour and weight each leg without a layer per mode. */
function routeToGeoJson(route: Route): FeatureCollection<LineString> {
  const features: Feature<LineString>[] = route.legs
    .filter((leg) => leg.coordinates.length >= 2)
    .map((leg, index) => ({
      type: "Feature",
      properties: { mode: leg.mode, family: MODE_KEY[leg.mode] ?? "blue", index },
      geometry: { type: "LineString", coordinates: leg.coordinates },
    }));
  return { type: "FeatureCollection", features };
}

const familyColor = (palette: MapPalette) => [
  "match",
  ["get", "family"],
  "walk",
  palette.walk,
  "gold",
  palette.gold,
  "krl",
  palette.krl,
  palette.blue,
];

const familyWidth = ["match", ["get", "family"], "walk", 3, "gold", 5, "krl", 7, 4];
const casingWidth = ["match", ["get", "family"], "walk", 9, "gold", 11, "krl", 13, 9];

/** Draws the itinerary in the design's grammar: a halo casing under every leg
 *  so the colours hold contrast on both basemaps, coloured strokes above it,
 *  and walk legs dashed and thin — walk is never the hero. */
function drawRoute(map: MapLibreMap, route: Route, palette: MapPalette): void {
  const data = routeToGeoJson(route);
  lastRoute = route;

  // The backend sends coordinates only for legs whose endpoints are pinned on
  // the graph. Nothing pinned means nothing to draw; leave the map alone.
  if (data.features.length === 0) return;

  setGeoJson(map, ROUTE_SOURCE, data);

  if (!map.getLayer(ROUTE_CASING)) {
    map.addLayer({
      id: ROUTE_CASING,
      type: "line",
      source: ROUTE_SOURCE,
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": palette.halo,
        "line-width": casingWidth as never,
        "line-opacity": ["match", ["get", "family"], "walk", 0.5, 1] as never,
      },
    });
    map.addLayer({
      id: ROUTE_LINE,
      type: "line",
      source: ROUTE_SOURCE,
      filter: ["!=", ["get", "family"], "walk"],
      layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": familyColor(palette) as never, "line-width": familyWidth as never },
    });
    map.addLayer({
      id: ROUTE_WALK,
      type: "line",
      source: ROUTE_SOURCE,
      filter: ["==", ["get", "family"], "walk"],
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": palette.walk,
        "line-width": 3,
        "line-dasharray": [0.5, 2],
      },
    });
    return;
  }

  map.setPaintProperty(ROUTE_CASING, "line-color", palette.halo);
  map.setPaintProperty(ROUTE_LINE, "line-color", familyColor(palette) as never);
  map.setPaintProperty(ROUTE_WALK, "line-color", palette.walk);
}

function highlight(map: MapLibreMap, payload: Record<string, unknown>, color: string): void {
  const geometry = payload.geometry as GeoJSON | undefined;
  if (!geometry) return;
  setGeoJson(map, HIGHLIGHT_SOURCE, geometry);
  if (!map.getLayer(HIGHLIGHT_LAYER)) {
    map.addLayer({
      id: HIGHLIGHT_LAYER,
      type: "circle",
      source: HIGHLIGHT_SOURCE,
      paint: {
        "circle-radius": 8,
        "circle-color": color,
        "circle-stroke-width": 2,
        "circle-stroke-color": "#e7f0f7",
      },
    });
  }
}

/** Returns true when the command was consumed by the map. `toggle_layer` is
 *  store state, so it is deliberately not handled here. */
export function applyUICommand(
  map: MapLibreMap,
  command: Command,
  palette: MapPalette,
): boolean {
  const action: UICommandAction = command.action;
  switch (action) {
    case "fly_to":
      flyTo(map, command.payload);
      return true;
    case "draw_route":
      drawRoute(map, command.payload as unknown as Route, palette);
      return true;
    case "highlight":
      highlight(map, command.payload, palette.blue);
      return true;
    case "toggle_layer":
      return false;
  }
}

/** Re-draws the last route after a basemap swap, in the new palette. */
export function reapplyRoute(map: MapLibreMap, palette: MapPalette): void {
  if (lastRoute) drawRoute(map, lastRoute, palette);
}

/** Fits the camera to a drawn route. */
export function fitRoute(map: MapLibreMap, route: Route): void {
  const points = route.legs.flatMap((leg) => leg.coordinates);
  if (points.length === 0) return;
  const lons = points.map((p) => p[0]);
  const lats = points.map((p) => p[1]);
  map.fitBounds(
    [
      [Math.min(...lons), Math.min(...lats)],
      [Math.max(...lons), Math.max(...lats)],
    ],
    { padding: 72, duration: 900 },
  );
}
