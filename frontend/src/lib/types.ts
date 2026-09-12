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
export type TransitMode = "walk" | "bus" | "rail" | "airport_rail" | "andong" | "becak";

export interface RouteStopSurvey {
  by: string | null;
  community: string | null;
  at: string | null;
}

/** Schedule attached to one surveyed Activity stop. Fields stay optional so
 *  routes produced before timetable ingestion remain valid. */
export interface RouteStopService {
  route_id?: string | number | null;
  name?: string | null;
  operator?: string | null;
  mode?: TransitMode | string | null;
  headway_min?: number | null;
  fare_idr?: number | null;
  source?: string | null;
  effective_from?: string | null;
  effective_until?: string | null;
  freshness_status?: string | null;
  service_basis?: string | null;
  service_start_local?: string | null;
  service_end_local?: string | null;
  headway_min_minutes?: number | null;
  headway_max_minutes?: number | null;
  headway_is_approximate?: boolean | null;
  next_departures?: string[];
}

export interface StopDeparture {
  stop_id: string;
  route_id: number;
  service_name: string;
  trip_external_id: string;
  scheduled_time_local: string;
  day_offset: number;
  is_estimated: boolean;
  source: string;
  effective_from: string | null;
  effective_until: string | null;
  freshness_as_of: string | null;
  freshness_status: string;
}

export interface RouteStopSchedule {
  next_departures?: string[];
  headway_min?: number | null;
  source?: string | null;
  effective_from?: string | null;
  effective_until?: string | null;
  freshness_status?: string | null;
}

/** A deduplicated stop at route level. `coordinate` is the backend's current
 *  spelling; `coord` keeps the client compatible with the planned public DTO. */
export interface RichTransitStop {
  id: string | number;
  external_id?: string | null;
  name?: string | null;
  coordinate?: [number, number] | number[];
  coord?: [number, number] | number[];
  photo_url?: string | null;
  photos?: string[];
  description?: string | null;
  survey?: RouteStopSurvey | null;
  routes?: RouteStopService[];
  schedule?: RouteStopSchedule | null;
  source?: string | null;
  effective_from?: string | null;
  effective_until?: string | null;
  freshness_status?: string | null;
}

export interface RouteLeg {
  mode: EdgeType;
  from_node: string;
  to_node: string;
  time_s: number;
  fare_idr: number;
  distance_m: number;
  from_name?: string | null;
  to_name?: string | null;
  transit_mode?: TransitMode | null;
  service_name?: string | null;
  operator?: string | null;
  /** Includes effective dates/freshness inherited from normalized source data. */
  source?: string | null;
  /** [lon, lat] pairs. Empty when either endpoint is unpinned on the graph. */
  coordinates: [number, number][];
}

export interface Route {
  legs: RouteLeg[];
  /** Survey-rich stops are new; absent on cached and older backend payloads. */
  stops?: RichTransitStop[];
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
