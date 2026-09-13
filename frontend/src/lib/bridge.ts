import type { GeoJSONSource, Map as MapLibreMap } from "maplibre-gl";
import type { Feature, FeatureCollection, GeoJSON, LineString, Point } from "geojson";
import { goToPlace } from "./actions";
import { placeFromRouteStop } from "./places";
import type { MapPalette } from "./tokens";
import { MODE_KEY } from "./tokens";
import type { Route, RouteLeg, ServerMessage, UICommandAction } from "./types";

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
const ROUTE_STOPS_SOURCE = "pathrix-agent-route-stops";
const ROUTE_STOPS_LAYER = "pathrix-agent-route-stops-circle";
const HIGHLIGHT_SOURCE = "pathrix-agent-highlight";
const HIGHLIGHT_LAYER = "pathrix-agent-highlight-circle";

type Command = Extract<ServerMessage, { type: "ui_command" }>;

/** setStyle drops everything the bridge added, so the last route is kept here
 *  and re-applied when the new style finishes loading. */
let lastRoute: Route | null = null;
const routeStopHandlers = new WeakSet<MapLibreMap>();

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
      properties: {
        mode: leg.mode,
        transit_mode: leg.transit_mode,
        service_name: leg.service_name,
        operator: leg.operator,
        source: leg.source,
        family: routeFamily(leg),
        index,
      },
      geometry: { type: "LineString", coordinates: leg.coordinates },
    }));
  return { type: "FeatureCollection", features };
}

function routeStopsToGeoJson(route: Route): FeatureCollection<Point> {
  const features: Feature<Point>[] = (route.stops ?? []).flatMap((stop, index) => {
    const coordinate = stop.coord ?? stop.coordinate;
    if (
      !coordinate ||
      coordinate.length < 2 ||
      !Number.isFinite(coordinate[0]) ||
      !Number.isFinite(coordinate[1])
    ) {
      return [];
    }
    const service = stop.routes?.[0];
    return [
      {
        type: "Feature",
        properties: {
          stop_index: index,
          stop_id: String(stop.external_id ?? stop.id),
          name: stop.name ?? "",
          family: MODE_KEY[service?.mode ?? "bus"] ?? "blue",
        },
        geometry: { type: "Point", coordinates: [coordinate[0], coordinate[1]] },
      },
    ];
  });
  return { type: "FeatureCollection", features };
}

const routeFamily = (leg: RouteLeg): keyof MapPalette =>
  MODE_KEY[leg.transit_mode ?? leg.mode] ?? "blue";

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
  const stops = routeStopsToGeoJson(route);
  lastRoute = route;

  // Clear prior data before returning: an empty new result must not leave an
  // old itinerary visible as if it were still selected.
  if (data.features.length > 0 || map.getSource(ROUTE_SOURCE)) {
    setGeoJson(map, ROUTE_SOURCE, data);
  }
  if (stops.features.length > 0 || map.getSource(ROUTE_STOPS_SOURCE)) {
    setGeoJson(map, ROUTE_STOPS_SOURCE, stops);
  }

  // The backend sends coordinates only for legs whose endpoints are pinned on
  // the graph. Nothing pinned means both prior sources have now been cleared.
  if (data.features.length === 0 && stops.features.length === 0) return;

  if (data.features.length > 0 && !map.getLayer(ROUTE_CASING)) {
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
  } else if (data.features.length > 0) {
    map.setPaintProperty(ROUTE_CASING, "line-color", palette.halo);
    map.setPaintProperty(ROUTE_LINE, "line-color", familyColor(palette) as never);
    map.setPaintProperty(ROUTE_WALK, "line-color", palette.walk);
  }

  if (stops.features.length > 0 && !map.getLayer(ROUTE_STOPS_LAYER)) {
    map.addLayer({
      id: ROUTE_STOPS_LAYER,
      type: "circle",
      source: ROUTE_STOPS_SOURCE,
      paint: {
        "circle-radius": 5,
        "circle-color": familyColor(palette) as never,
        "circle-stroke-width": 2,
        "circle-stroke-color": palette.halo,
      },
    });
  } else if (stops.features.length > 0) {
    map.setPaintProperty(ROUTE_STOPS_LAYER, "circle-color", familyColor(palette) as never);
    map.setPaintProperty(ROUTE_STOPS_LAYER, "circle-stroke-color", palette.halo);
  }

  if (stops.features.length > 0 && !routeStopHandlers.has(map)) {
    routeStopHandlers.add(map);
    map.on("mouseenter", ROUTE_STOPS_LAYER, () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", ROUTE_STOPS_LAYER, () => {
      map.getCanvas().style.cursor = "";
    });
    map.on("click", ROUTE_STOPS_LAYER, (event) => {
      const index = Number(event.features?.[0]?.properties?.stop_index);
      const stop = Number.isInteger(index) ? lastRoute?.stops?.[index] : null;
      if (!stop) return;
      const place = placeFromRouteStop(stop);
      if (place) goToPlace(place);
    });
  }
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

/** Great-circle initial bearing from A to B, in degrees, 0 = north. */
function bearingBetween([lon1, lat1]: [number, number], [lon2, lat2]: [number, number]): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const phi1 = toRad(lat1);
  const phi2 = toRad(lat2);
  const deltaLambda = toRad(lon2 - lon1);
  const y = Math.sin(deltaLambda) * Math.cos(phi2);
  const x = Math.cos(phi1) * Math.sin(phi2) - Math.sin(phi1) * Math.cos(phi2) * Math.cos(deltaLambda);
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

/** Overall direction of travel: first leg-polyline point to the last one, so
 *  a nav-style focus can orient the camera with the destination "ahead"
 *  instead of always north-up. `null` when the endpoints coincide (too short
 *  or a loop) — nothing sensible to orient to. */
export function routeBearing(route: Route): number | null {
  const points = route.legs.flatMap((leg) => leg.coordinates);
  if (points.length < 2) return null;
  const first = points[0];
  const last = points[points.length - 1];
  if (Math.abs(first[0] - last[0]) < 1e-5 && Math.abs(first[1] - last[1]) < 1e-5) return null;
  return bearingBetween(first, last);
}

/** Fits the camera to a drawn route, optionally rotated to a bearing so a
 *  direction of travel reads as "up". Returns whether it actually moved the
 *  camera — false (no points) means no `moveend` will follow. */
export function fitRoute(map: MapLibreMap, route: Route, bearing?: number): boolean {
  const stopPoints = (route.stops ?? []).flatMap((stop) => {
    const coordinate = stop.coord ?? stop.coordinate;
    return coordinate && coordinate.length >= 2 ? [[coordinate[0], coordinate[1]] as [number, number]] : [];
  });
  const points = [...route.legs.flatMap((leg) => leg.coordinates), ...stopPoints];
  if (points.length === 0) return false;
  const lons = points.map((p) => p[0]);
  const lats = points.map((p) => p[1]);
  map.fitBounds(
    [
      [Math.min(...lons), Math.min(...lats)],
      [Math.max(...lons), Math.max(...lats)],
    ],
    { padding: 72, duration: 900, ...(bearing !== undefined ? { bearing } : {}) },
  );
  return true;
}
