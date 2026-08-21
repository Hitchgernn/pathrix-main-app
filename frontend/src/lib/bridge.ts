import type { GeoJSONSource, Map as MapLibreMap } from "maplibre-gl";
import type { GeoJSON } from "geojson";
import type { ServerMessage, UICommandAction } from "./types";

/** The map ↔ agent bridge — ARCHITECTURE.md §10.2.
 *
 *  `ui_command` handling is a pure switch over a closed action set. Adding an
 *  action means changing models/agent.py and the UICommandAction union
 *  deliberately, not sending a new string and hoping.
 */

const ROUTE_SOURCE = "pathrix-agent-route";
const ROUTE_LAYER = "pathrix-agent-route-line";
const HIGHLIGHT_SOURCE = "pathrix-agent-highlight";
const HIGHLIGHT_LAYER = "pathrix-agent-highlight-circle";

type Command = Extract<ServerMessage, { type: "ui_command" }>;

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

function setGeoJson(map: MapLibreMap, id: string, data: GeoJSON): void {
  const existing = map.getSource(id);
  if (existing && "setData" in existing) {
    (existing as GeoJSONSource).setData(data);
    return;
  }
  map.addSource(id, { type: "geojson", data });
}

function drawRoute(map: MapLibreMap, payload: Record<string, unknown>, color: string): void {
  // The backend's draw_route payload is a Route (models/routing.py): legs carry
  // node ids and costs, not coordinates. Until route geometry is part of that
  // contract there is nothing to draw, so leave the map alone rather than
  // inventing a line.
  const geometry = payload.geometry as GeoJSON | undefined;
  if (!geometry) return;

  setGeoJson(map, ROUTE_SOURCE, geometry);
  if (!map.getLayer(ROUTE_LAYER)) {
    map.addLayer({
      id: ROUTE_LAYER,
      type: "line",
      source: ROUTE_SOURCE,
      layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": color, "line-width": 5 },
    });
  } else {
    map.setPaintProperty(ROUTE_LAYER, "line-color", color);
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
  colors: { route: string; highlight: string },
): boolean {
  const action: UICommandAction = command.action;
  switch (action) {
    case "fly_to":
      flyTo(map, command.payload);
      return true;
    case "draw_route":
      drawRoute(map, command.payload, colors.route);
      return true;
    case "highlight":
      highlight(map, command.payload, colors.highlight);
      return true;
    case "toggle_layer":
      return false;
  }
}

export const ROUTE_LAYER_ID = ROUTE_LAYER;
