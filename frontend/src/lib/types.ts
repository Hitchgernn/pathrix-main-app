/** Mirrors backend/app/models/. Kept hand-written rather than generated so the
 *  contract break is a TypeScript error, not a silent runtime shape change.
 *  ARCHITECTURE.md §9.1 is the authority for the WebSocket envelope. */

import type { Geometry } from "geojson";

export interface BBox {
  min_lon: number;
  min_lat: number;
  max_lon: number;
  max_lat: number;
}

export type EdgeType =
  | "walk"
  | "board"
  | "ride"
  | "alight"
  | "transfer"
  | "andong"
  | "becak";

export type Optimize = "tercepat" | "termurah" | "termudah";

export interface RouteLeg {
  mode: EdgeType;
  from_node: string;
  to_node: string;
  time_s: number;
  fare_idr: number;
  distance_m: number;
  /** [lon, lat] pairs. Empty when either endpoint is unpinned on the graph. */
  coordinates: [number, number][];
}

export interface Route {
  legs: RouteLeg[];
  total_time_s: number;
  total_fare_idr: number;
  total_distance_m: number;
  transfers: number;
}

export interface CarbonResult {
  saved_g_co2: number;
  mode: string;
  distance_km: number;
  source_citation: string;
}

export interface LayerMeta {
  id: string;
  name: string;
  queryable: boolean;
  description: string;
}

/** Mirrors models/mapid.py's Feature — a mission-derived row (poi/properti),
 *  read back from Postgres via /api/layers/{id}/features. geometry is
 *  whatever GeoJSON geometry ST_AsGeoJSON produced, almost always a Point. */
export interface MissionFeature {
  external_id: string;
  properties: Record<string, unknown>;
  geometry: Geometry;
}

/** The closed action set. Adding one means changing models/agent.py and this
 *  union deliberately — ARCHITECTURE.md §10.2. */
export type UICommandAction = "toggle_layer" | "fly_to" | "draw_route" | "highlight";

export interface ViewportPayload {
  bbox: BBox;
  zoom: number;
}

export type ClientMessage =
  | { type: "user_message"; text: string; viewport: ViewportPayload }
  | { type: "viewport_changed"; bbox: BBox; zoom: number };

export type ServerMessage =
  | { type: "token"; delta: string }
  | { type: "ui_command"; action: UICommandAction; payload: Record<string, unknown> }
  | { type: "done"; route: Route | null; carbon: CarbonResult | null }
  | { type: "error"; code: string; message: string };

export interface ChatMessage {
  who: "user" | "agent";
  text: string;
  /** Route attached to this reply — renders the inline RouteCard affordance. */
  route?: Route | null;
}
