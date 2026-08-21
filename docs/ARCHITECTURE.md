# PATHRIX — System Architecture

**WebGIS AI Agent for multimodal mobility in Yogyakarta**

**Version:** 0.1 (draft)
**Date:** 18 August 2026
**Status:** 🚧 **PROVISIONAL — subject to change**

---

> ## ⚠️ This document is temporary and will change
>
> This architecture is a **working draft written before implementation begins**. It is the current best understanding of how the system should be built, not a record of how it was built.
>
> **Expect it to change** as:
>
> - Implementation surfaces constraints that design did not anticipate.
> - The MAPID mission API is exercised with a real key rather than read from documentation.
> - Field survey data arrives and reveals its actual shape, density, and quality.
> - Performance measurement replaces performance estimation.
> - Deferred decisions are made — LLM model, hosting, and the Sosial Budaya layer are all still open (§15).
>
> Sections are marked with a confidence tag:
>
> | Tag | Meaning |
> |---|---|
> | **`[VERIFIED]`** | Confirmed against a live endpoint or a working build |
> | **`[DESIGNED]`** | Deliberate decision with stated rationale; not yet implemented |
> | **`[PROVISIONAL]`** | Best current guess; expected to change on contact with reality |
>
> **When this document and the code disagree, the code is right and this document is stale.** Update it in the same change that invalidates it — see §16.

---

## 1. Purpose and relationship to other documents

| Document | Role | Authority |
|---|---|---|
| `proposal_pathrix.md` | Submitted to competition judges | **Binding commitment.** Deviations need justification |
| `PRD_AI_TOD_Navigator_Yogyakarta.md` | Product requirements | Binding on scope, features, metrics |
| `PLAN.md` | Build plan — stack, schedule, decisions | Current |
| **`ARCHITECTURE.md`** (this) | **How the system is put together** | **Provisional** |

`PLAN.md` answers *what we are building and when*. This document answers *how the pieces fit and what the contracts between them are*. Where they overlap, `PLAN.md` is the summary and this is the detail; where they conflict, this document is probably the more recently reasoned but `PLAN.md` carries the schedule commitments.

---

## 2. Architectural principles

Five decisions that everything else follows from. Changing any of these is a re-architecture, not a refactor.

### 2.1 The LLM orchestrates; it never computes `[DESIGNED]`

Every number the user sees — distance, duration, fare, CO₂ — originates from a deterministic function and is interpolated into the response. The model chooses *which* function to call and narrates the result. It never produces a figure of its own.

This is the proposal's central anti-hallucination claim and it must be enforced structurally: responses are assembled from typed tool returns, not extracted from model prose. A system prompt asking the model to be truthful is not an implementation of this principle.

### 2.2 Prose and map commands travel on separate channels `[DESIGNED]`

The agent emits two independent output streams over one socket: streamed text for the chat surface, and structured `UICommand` objects for the map. The client never parses instructions out of prose.

This is what makes "the AI manipulates the map" a contract with a schema rather than a demo that works on rehearsed inputs.

### 2.3 Time-independent routing `[DESIGNED]`

No GTFS feed exists for TransJogja. Service is therefore modelled by **headway**, not timetable — which means edge cost does not depend on when the traveller arrives at that edge. That condition is exactly what makes plain Dijkstra correct.

The consequence: no timetable simulation, no time-expanded graph, no JVM routing service. This is a real simplification with a sound basis, not a shortcut, and the reasoning belongs in the final documentation.

### 2.4 Mirror external data; do not proxy it `[DESIGNED]`

MAPID mission data is ETL'd into PostGIS on a schedule. Viewport queries hit the local mirror. Rationale in §6.3.

### 2.5 Degrade, don't fail `[DESIGNED]`

Every external dependency has a defined behaviour when absent (§13). The map renders without the agent; the agent answers without the LLM being able to route; routes compute without carbon figures. A judging session must never see a blank screen because one subsystem is unavailable.

---

## 3. Component map

```
┌────────────────────────────────────────────────────────────────┐
│  BROWSER                                                       │
│                                                                │
│  ┌──────────────┐   viewport    ┌────────────────────────┐     │
│  │  MapLibre    │◄──────────────│  Zustand store         │     │
│  │  GL JS       │   UICommand   │  map · layers · agent  │     │
│  └──────┬───────┘──────────────►└───────────┬────────────┘     │
│         │ style.json?key=                   │                  │
│         ▼                                   │ WebSocket        │
│  v2.basemap.mapid.io                        │                  │
└─────────────────────────────────────────────┼──────────────────┘
                                              │
┌─────────────────────────────────────────────┼──────────────────┐
│  BACKEND (FastAPI)                          ▼                  │
│                                    ┌──────────────────┐        │
│                                    │  /ws  gateway    │        │
│                                    │  ratelimit·valid │        │
│                                    └────────┬─────────┘        │
│                                             ▼                  │
│                                    ┌──────────────────┐        │
│                                    │ LangGraph agent  │        │
│                                    │ plan→tools→resp  │        │
│                                    └────────┬─────────┘        │
│              ┌──────────────────────────────┼──────────┐       │
│              ▼                ▼              ▼          ▼      │
│      ┌────────────┐  ┌──────────────┐ ┌──────────┐ ┌────────┐  │
│      │  routing   │  │   spatial    │ │  carbon  │ │geocode │  │
│      │  engine    │  │  repository  │ │   calc   │ │resolver│  │
│      │ (NetworkX) │  │  (PostGIS)   │ │  (pure)  │ │        │  │
│      └─────┬──────┘  └──────┬───────┘ └──────────┘ └───┬────┘  │
│            │                │                          │       │
│            └────────┬───────┘                          │       │
│                     ▼                                  ▼       │
│            ┌─────────────────┐              nominatim.mapid.io │
│            │ PostgreSQL+     │                                 │
│            │ PostGIS · Redis │                                 │
│            └────────▲────────┘                                 │
│                     │ scheduled ETL                            │
│            ┌────────┴────────┐                                 │
│            │  MAPID adapter  │──► server.mapid.io/web/competition│
│            └────────▲────────┘                                 │
│                     │                                          │
│            OSM (OSMnx) · digitized routes · field survey        │
└────────────────────────────────────────────────────────────────┘
```

### 3.1 Module responsibilities `[DESIGNED]`

| Module | Owns | Must not |
|---|---|---|
| `api/` | HTTP + WebSocket surface, auth, rate limiting, payload validation | Contain business logic |
| `agent/` | LangGraph graph, tool bindings, prompts, LLM adapter | Compute numbers; touch the database directly |
| `routing/` | Graph build, shortest paths, isochrones, TSP | Know about HTTP, the LLM, or MAPID |
| `data/` | PostGIS repositories, MAPID adapter, geocode resolver, ETL | Contain routing algorithms |
| `models/` | Pydantic schemas — the shared contract | Import from any other layer |

The dependency rule: `api → agent → {routing, data} → models`. Nothing depends upward. `routing/` in particular must be importable and testable with no network and no LLM.

---

## 4. Runtime topology `[DESIGNED]`

### 4.1 Processes

| Container | Process | Notes |
|---|---|---|
| `proxy` | Caddy | TLS, static assets, `/api` + `/ws` upstream |
| `web` | (build artifact) | Static Vite output, served by proxy |
| `api` | Uvicorn → FastAPI | **Single worker initially** — see §4.2 |
| `worker` | APScheduler or cron | ETL refresh, isochrone precompute |
| `db` | PostgreSQL 16 + PostGIS 3.4 | Persistent volume |
| `cache` | Redis 7 | Routes, viewport results, rate limits |

### 4.2 The routing graph is process-local state `[PROVISIONAL]`

The NetworkX graph lives in the `api` process memory, built at startup. This has a consequence that must be understood before scaling:

**Multiple Uvicorn workers each hold a full copy of the graph.** For a study-area-sized walk network this is plausibly 200–600 MB per worker — an estimate, not a measurement.

Options, in order of preference:
1. **Single worker + async I/O.** Routing is CPU-bound but short; the event loop handles concurrency during database and LLM waits. Sufficient for judging-day traffic. **Start here.**
2. Shared read-only graph via `multiprocessing.shared_memory` — meaningful work, only if needed.
3. Extract routing into its own service — full re-architecture, out of scope for the remaining schedule.

**Measure actual graph memory before choosing.** If option 1 is inadequate the honest fix is a bigger box, not a bigger design.

---

## 5. Data architecture

### 5.1 Schema `[PROVISIONAL]`

Indicative DDL. Column names are near-final where they mirror MAPID's documented properties; types and indexes will move.

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

-- ---------- transit network ----------
CREATE TABLE transit_stops (
  id            bigserial PRIMARY KEY,
  external_id   text,
  name          text NOT NULL,
  mode          text NOT NULL CHECK (mode IN ('bus','rail','airport_rail')),
  operator      text NOT NULL,              -- TransJogja | KAI Commuter | KA Bandara YIA
  geom          geometry(Point,4326) NOT NULL,
  source        text NOT NULL,              -- provenance, required
  updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON transit_stops USING GIST (geom);

CREATE TABLE transit_routes (
  id            bigserial PRIMARY KEY,
  name          text NOT NULL,
  operator      text NOT NULL,
  mode          text NOT NULL,
  headway_min   numeric NOT NULL,           -- drives expected wait = headway/2
  fare_idr      integer NOT NULL,
  geom          geometry(LineString,4326),
  source        text NOT NULL,
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE route_stops (
  route_id                bigint REFERENCES transit_routes(id),
  stop_id                 bigint REFERENCES transit_stops(id),
  seq                     integer NOT NULL,
  travel_time_from_prev_s integer,          -- NULL on first stop
  PRIMARY KEY (route_id, seq)
);

-- ---------- first/last mile ----------
CREATE TABLE pangkalan (
  id            bigserial PRIMARY KEY,
  type          text NOT NULL CHECK (type IN ('andong','becak')),
  name          text,
  operating_hours text,
  fare_base     integer,
  fare_per_km   integer,
  photo_url     text,
  geom          geometry(Point,4326) NOT NULL,
  surveyor      text,
  surveyed_at   timestamptz,
  source        text NOT NULL DEFAULT 'field_survey',
  updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON pangkalan USING GIST (geom);

-- ---------- MAPID mission mirror ----------
CREATE TABLE poi (
  id               bigserial PRIMARY KEY,
  external_id      text UNIQUE NOT NULL,    -- MAPID _id, upsert key
  source           text NOT NULL CHECK (source IN ('menugo','struckgo','activities')),
  nama_tempat      text,
  kategori         text,
  jam_buka         text,                    -- promoted: agent answers "is it open?"
  jam_tutup        text,
  harga_rata_rata  integer,                 -- promoted: agent answers "how much?"
  foto_url         text,
  raw              jsonb NOT NULL,          -- everything else, losslessly
  geom             geometry(Point,4326) NOT NULL,
  fetched_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON poi USING GIST (geom);
CREATE INDEX ON poi (source);

CREATE TABLE properti (
  id                bigserial PRIMARY KEY,
  external_id       text UNIQUE NOT NULL,
  kategori_properti text,
  jenis_properti    text,
  alamat            text,
  foto_url          text,
  raw               jsonb NOT NULL,
  geom              geometry(Point,4326) NOT NULL,
  fetched_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON properti USING GIST (geom);

-- ---------- pedestrian network ----------
CREATE TABLE walk_nodes (
  id    bigint PRIMARY KEY,                 -- OSM node id
  geom  geometry(Point,4326) NOT NULL
);
CREATE INDEX ON walk_nodes USING GIST (geom);

CREATE TABLE walk_edges (
  u          bigint NOT NULL,
  v          bigint NOT NULL,
  length_m   double precision NOT NULL,
  geom       geometry(LineString,4326),
  PRIMARY KEY (u, v)
);

-- ---------- derived ----------
CREATE TABLE isochrones (
  stop_id      bigint REFERENCES transit_stops(id),
  minutes      integer NOT NULL,
  geom         geometry(Polygon,4326) NOT NULL,
  computed_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (stop_id, minutes)
);

CREATE TABLE emission_factors (
  mode             text PRIMARY KEY,
  g_co2_per_km     numeric NOT NULL,
  source_citation  text NOT NULL           -- never nullable: the number is worthless without it
);
```

### 5.2 Two schema conventions `[DESIGNED]`

**Provenance is not optional.** Every table carries `source` and a timestamp. Competition Deliverable 3 requires dataset metadata and processing methodology; recording it at write time costs nothing, reconstructing it in the final week costs a day.

**`emission_factors.source_citation` is `NOT NULL` on purpose.** An uncited carbon figure is a credibility risk the PRD explicitly names (§13). The schema makes the number and its provenance inseparable.

### 5.3 `raw jsonb` alongside promoted columns `[DESIGNED]`

MAPID mission records are stored twice: the full payload in `raw`, plus a handful of promoted columns the agent filters on. This is deliberate redundancy — promoting every field guesses at a schema we do not control, while storing only `raw` makes `WHERE jam_buka <= now()` unusable.

Promote a field when the agent needs to *filter or sort* by it. Leave it in `raw` when it is only ever *displayed*.

---

## 6. MAPID integration layer

### 6.1 Basemap `[VERIFIED]`

```
https://v2.basemap.mapid.io/styles/{style}/style.json?key={MAPID_BASEMAP_KEY}
```

Styles: `street-v2.0`, `satellite-v2.0`, `dark-v2.0`, `light-v2.0`. Verified: **200 with key, 401 without.** MapLibre style spec **version 8**, 253 layers; vector sources `mapidtiles`, `indonesiatiles`, `ocean`, plus Natural Earth raster relief. `glyphs` and `sprite` are keyed endpoints on the same host.

There is **no MAPID SDK**. Integration is a style URL passed to MapLibre.

### 6.2 Mission data contract `[VERIFIED from documentation]`

Endpoint shape and auth confirmed from published docs; **not yet exercised with a real mission key.**

```http
POST https://server.mapid.io/web/competition/{menugo|propertigo|struckgo|activities}
Content-Type: application/json
x-api-key: {MAPID_MISSION_API_KEY}
```

```jsonc
{
  "feature": { "type": "Polygon", "coordinates": [[[lng,lat], ...]] },  // required
  "start_date": "2026-01-01",   // optional
  "end_date":   "2026-12-31",   // optional
  "hashtag":    ["kuliner"],    // optional, case-insensitive partial on description
  "author":     "budi"          // optional, matches name / full_name
}
```

Endpoint is spelled **`struckgo`**.

**Two response shapes — do not write one parser.**

```jsonc
// menugo | propertigo | struckgo
{ "success": true, "message": "...", "features": [ ... ],
  "pagination": { "total": 0, "limit": 100, "offset": 0, "hasMore": false } }

// activities
{ "success": true, "message": "...",
  "data": { "activities": [ { "_id", "title", "description",
                              "geometry", "medias": [], "user_name",
                              "user_full_name", "community_name" } ] } }
```

Server behaviour: polygon queries use a spatial index; only missions with status `"Diterima"` are returned (hardcoded, not overridable).

### 6.3 Why mirror rather than proxy `[DESIGNED]`

The mission API is itself a polygon query, which maps almost 1:1 onto `get_data_in_viewport` and invites calling it live. Four reasons not to:

- **Latency.** A remote POST with a documented 30-second timeout ceiling sits inside an 8-second agent budget.
- **Uptime.** A 100% judging-day target should not depend on a third party being up.
- **Spatial joins need local data.** Intersecting POIs with transit isochrones — the proposal's *Spatial Intersection* commitment — cannot be done against a remote paginated endpoint.
- **Nothing is real-time.** Only accepted missions are returned; a scheduled refresh loses nothing.

ETL: one polygon over the study area → paginate to exhaustion → upsert on `external_id` → stamp `fetched_at`. Nightly, plus one manual run immediately before judging.

### 6.4 Adapter interface `[DESIGNED]`

```python
# app/data/mapid.py
class MapidClient(Protocol):
    def fetch_missions(
        self,
        dataset: Literal["menugo", "propertigo", "struckgo", "activities"],
        polygon: Polygon,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        hashtag: list[str] | None = None,
        author: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> MissionPage: ...

    @staticmethod
    def basemap_style_url(style: str, key: str) -> str: ...
```

`MissionPage` normalises both response shapes into `features: list[Feature]` plus `has_more: bool`, so callers never branch on dataset. A `FakeMapidClient` backed by fixtures implements the same protocol for tests and offline work.

### 6.5 Geocoding `[VERIFIED]`

`https://nominatim.mapid.io` — standard Nominatim, forward and reverse, **no key required**. Verified on Yogyakarta (`Malioboro` → `-7.7952921, 110.3657274`; reverse at Tugu returns an OSM way).

**Deliberately not an agent tool.** It is an internal resolver in `app/data/geocode.py`, called inside `calculate_route` and `plan_multistop` so their arguments accept a coordinate *or* a place string. This preserves the exact five-tool surface the PRD commits to (§8.3). Promote it only if standalone place search becomes necessary.

Cache resolutions in Redis keyed by normalised query string — place names repeat heavily and this is free latency.

---

## 7. Routing engine

### 7.1 Graph model `[DESIGNED]`

One directed multigraph, built at startup, held in memory.

**Nodes:** walk nodes (OSMnx `network_type="walk"`), transit stops, pangkalan.

**Edges:**

| Type | Cost (seconds) | Fare (IDR) |
|---|---|---|
| `walk` | `length_m / 1.33` | 0 |
| `board` | `headway_min * 30 + BOARD_PENALTY` | route fare |
| `ride` | `travel_time_from_prev_s` | 0 |
| `alight` | `ALIGHT_PENALTY` | 0 |
| `transfer` | walk time + `headway_min * 30` of next route | fare unless free-transfer window |
| `andong` / `becak` | `distance / speed + NEGOTIATION_S` | `fare_base + km * fare_per_km` |

`1.33 m·s⁻¹` ≈ 4.8 km/h walking. `headway_min * 30` is expected wait (headway/2, in seconds).

Andong and becak edges connect a pangkalan to any node within a radius, modelling on-demand point-to-point service. This is what makes them *connectors* in the graph rather than markers on a map — the product's differentiator.

### 7.2 Three objectives, one graph `[DESIGNED]`

Not three algorithms — one graph traversed with three weight functions.

```python
WEIGHTS = {
    "tercepat": lambda e: e.time_s,
    "termurah": lambda e: e.fare_idr,
    "termudah": lambda e: e.transfers * W_TRANSFER + e.walk_m * W_WALK,
}
```

`W_TRANSFER` and `W_WALK` are tunable constants that **must be documented with their chosen values** — they encode a subjective definition of "easiest" and a judge may reasonably ask. Current placeholders (`app/routing/constants.py`): `W_TRANSFER = 300.0`, `W_WALK = 1.0` — untuned against real routes yet, see open question 8 below.

### 7.3 Derived analyses `[DESIGNED]`

**Isochrones.** Dijkstra from a stop with a time cutoff → reachable node set → concave hull → PostGIS polygon. Precomputed for major nodes.

**Multi-stop.** Pairwise cost matrix from the engine → nearest-neighbour construction → 2-opt improvement. The PRD's "heuristik TSP ringan" (§6). Cap the stop count — 2-opt is O(n²) per pass and the UI should refuse absurd inputs rather than hang.

**Carbon.**

```
saved_g = distance_km * factor[private_vehicle] - distance_km * factor[mode]
```

Factors and citations from `emission_factors`. The UI shows the source and the assumption alongside the figure.

### 7.4 Graph rebuild `[PROVISIONAL]`

Rebuild is a worker job writing a serialised graph; the API loads it at startup and on a reload signal. Rebuild cadence follows source data change, not a clock.

**Open:** whether rebuild can happen without an API restart. Simplest correct answer for the schedule is *restart the container* — a few seconds of downtime outside judging is acceptable. Revisit only if it becomes a problem.

---

## 8. Agent subsystem

### 8.1 State `[DESIGNED]`

```python
class AgentState(TypedDict):
    messages:      Annotated[list, add_messages]
    viewport:      Viewport             # bbox, zoom, centre — pushed by client each turn
    active_layers: set[str]
    last_route:    Route | None         # enables "yang lebih murah dari tadi"
    last_carbon:   CarbonResult | None
    ui_commands:   list[UICommand]      # drained after each turn
    locale:        str                  # "id" | "en"
```

`viewport` makes viewport-awareness work — *"ada kuliner apa di area ini?"* resolves against what the user is actually looking at. `last_route`/`last_carbon` are what separate an agent with memory from a stateless chatbot — the most recent route and carbon-savings tool results, carried forward and sent on the `done` event.

### 8.2 Graph `[DESIGNED]`

```
        ┌──────────┐
   ─────►   plan   │  LLM, tools bound
        └────┬─────┘
             │ has tool_calls?
        ┌────▼─────┐
        │  tools   │  ToolNode — execute, append results
        └────┬─────┘
             │ loop
        ┌────▼─────┐
        │ respond  │  narrate from tool output, drain ui_commands
        └──────────┘
```

Loop bounded by a per-turn tool-call budget (§12).

### 8.3 Tool contracts `[DESIGNED]`

Exactly the five tools named in PRD §9.1 — the PRD is a graded deliverable and the surfaces must match.

```python
def toggle_layer(layer_id: str, on: bool) -> LayerResult
def get_data_in_viewport(bbox: BBox, data_type: str, limit: int = 50) -> FeatureList
def calculate_route(start: str | Coord, end: str | Coord,
                    modes: list[str], optimize: Literal["termudah","tercepat","termurah"]) -> Route
def plan_multistop(stops: list[str | Coord], optimize: str) -> Itinerary
def calculate_carbon_savings(route: Route) -> CarbonResult
```

`start`, `end`, and `stops` accept a place string; the geocode resolver (§6.5) converts it internally.

Every tool returns a Pydantic model. The `respond` node formats those models into prose — it does not invent values.

### 8.4 Guardrails `[DESIGNED]`

| Guard | Mechanism | Risk addressed |
|---|---|---|
| No fabricated numbers | Response assembled from typed tool returns | Proposal's core claim |
| Bounded viewport queries | Reject or clamp bbox above an area threshold | PRD §13 performance risk |
| Parameter validation | Pydantic validates before execution; invalid calls return a structured error the agent can recover from | PRD §13 tool-call error |
| Unknown intent | Explicit fallback message, not a guessed tool call | PRD §13 |
| Latency | Per-turn tool-call budget | < 8s target |

### 8.5 LLM adapter `[PROVISIONAL]`

The model is **not chosen** (§15). `app/agent/llm.py` exposes a single factory returning a bound chat model, so the choice is a late, cheap swap.

Requirements the adapter must satisfy regardless of model: streaming, tool calling, and a configurable latency ceiling. Decide after the first prototype yields real latency and intent-precision numbers — not before.

---

## 9. Transport contracts

### 9.1 WebSocket `[DESIGNED]`

```jsonc
// client → server
{ "type": "user_message",     "text": "...", "viewport": { "bbox": [...], "zoom": 14 } }
{ "type": "viewport_changed", "bbox": [...], "zoom": 14 }

// server → client
{ "type": "token",      "delta": "..." }
{ "type": "ui_command", "action": "toggle_layer" | "fly_to" | "draw_route" | "highlight",
                        "payload": { } }
{ "type": "done",       "route": { }, "carbon": { } }
{ "type": "error",      "code": "...", "message": "..." }
```

Streaming is a **latency requirement**, not polish: the 8-second budget is about perceived responsiveness, and perceived latency is time-to-first-token. A reply that starts rendering at 1.2s and completes at 7s feels fast; the same reply delivered whole at 7s does not.

### 9.2 REST `[PROVISIONAL]`

WebSocket carries the conversation. REST carries everything else:

```
GET  /api/layers                 layer catalogue + metadata
GET  /api/layers/{id}/features   bbox-filtered features (also feeds vector tiles)
GET  /api/isochrone/{stop_id}    precomputed polygon
GET  /api/health                 db · redis · graph-loaded
```

`/api/health` reporting graph state matters — an API that is up but has no routing graph is worse than one that is down, because it fails silently.

---

## 10. Frontend architecture

### 10.1 State `[DESIGNED]`

Three Zustand slices with one rule: **the map is the source of truth for viewport; the store mirrors it.** MapLibre owns camera state, the store subscribes. Two-way binding on a camera is how you get feedback loops and jitter.

```ts
interface MapSlice    { bbox: BBox; zoom: number; center: LngLat }
interface LayerSlice  { active: Set<string>; catalogue: LayerMeta[] }
interface AgentSlice  { messages: Message[]; streaming: boolean; lastRoute: Route | null }
```

### 10.2 The map ↔ agent bridge `[DESIGNED]`

The single most integration-sensitive piece. One module, `lib/bridge.ts`:

- Outbound: debounced `viewport_changed`, and current viewport attached to every `user_message`.
- Inbound: `ui_command` → an imperative MapLibre call (`setLayoutProperty`, `fitBounds`, `addSource`/`addLayer`).

`ui_command` handling is a **pure switch over a closed action set**. Adding an action means changing the schema in `models/` and both ends deliberately — not sending a new string and hoping.

### 10.3 Layout `[DESIGNED]`

Full-bleed map. Agent in a bottom sheet with three snap points (peek / half / full). Layer panel is a second sheet, not a sidebar — a sidebar at 390px is precisely how existing WebGIS tools lose the users this product exists for. Desktop promotes the sheet to a left rail without changing the component tree.

### 10.4 Basemap and tokens `[DESIGNED]`

`street-v2.0` default, `dark-v2.0` for the dark treatment. Design tokens are copied from the landing page's `src/styles/tokens.css` into the Tailwind theme (copied, not cross-imported).

Verify route and marker contrast against **both** basemap styles — a line colour that reads on street disappears on satellite.

---

## 11. Cross-cutting concerns

### 11.1 Configuration `[DESIGNED]`

```
DATABASE_URL
REDIS_URL
MAPID_BASEMAP_KEY          # reaches the browser — basemap scope only
MAPID_MISSION_API_KEY      # server-only, never in a client bundle
LLM_PROVIDER / LLM_MODEL / LLM_API_KEY
STUDY_AREA_POLYGON
```

**The two MAPID keys have different exposure profiles and must never be conflated.** MapLibre fetches the style URL directly from the browser, so the basemap key is necessarily public and must be scoped accordingly. The mission key must not appear in a bundle, a proxied response, or a log line.

### 11.2 Caching `[PROVISIONAL]`

| Key | TTL | Rationale |
|---|---|---|
| `route:{hash}` | hours | Popular OD pairs; precomputed for known corridors |
| `viewport:{rounded_bbox}:{type}` | minutes | Rounded so near-identical pans hit |
| `geocode:{normalised}` | days | Place names are stable |
| `ratelimit:{ip}` | window | Gateway limiting |

Round bbox keys deliberately — an unrounded bbox is unique on every pixel of pan and caches nothing.

### 11.3 Observability `[PROVISIONAL]`

Structured logs. Minimum useful signal for the scored metrics:

- Per turn: tool calls made, time-to-first-token, total duration.
- Per tool: duration, cache hit/miss.
- ETL: records fetched, upserted, duration, failures.

Instrument time-to-first-token from day one — it is the number the 8-second target actually depends on, and retrofitting it later means re-running the whole evaluation set.

### 11.4 Security `[DESIGNED]`

Gateway rate limiting (proposal commitment) · bbox area caps · Pydantic validation on every inbound payload · CORS pinned to the app origin · no secrets client-side beyond the basemap key · mission and LLM keys server-only.

---

## 12. Performance budget `[PROVISIONAL]`

An allocation, not a measurement. Every number below is a target to be validated.

**Agent turn — 8000 ms ceiling**

| Stage | Budget |
|---|---|
| Gateway + validation | 50 ms |
| LLM first token | 1200 ms |
| Tool execution (≤ 3 calls) | 2500 ms |
| LLM narration | 2000 ms |
| Transport + render | 250 ms |
| **Headroom** | **~2000 ms** |

**Initial load — 5000 ms on 4G**

| Asset | Budget |
|---|---|
| HTML + critical CSS | 300 ms |
| JS entry (MapLibre code-split out) | 1200 ms |
| MapLibre chunk | 1500 ms |
| Basemap style + first tiles | 1500 ms |
| **Headroom** | **~500 ms** |

The load budget is the tighter of the two. MapLibre plus vector tiles is most of it, which is why layers lazy-load on activation rather than at boot.

---

## 13. Failure modes `[DESIGNED]`

| Failure | Behaviour | User sees |
|---|---|---|
| LLM unavailable | Tools remain reachable via UI controls | Map works; chat reports unavailable |
| Routing graph not loaded | Route tools return a typed error; `/api/health` fails | Layers work; routing declines clearly |
| MAPID mission API down | Mirror serves last successful ETL | Nothing — staleness only |
| Basemap 401 / down | Fall back to a plain OSM raster style | Degraded basemap, app functional |
| Nominatim down | Coordinate input still works | Place-name lookup declines |
| Redis down | Recompute uncached | Slower, correct |
| PostGIS down | Hard failure | Honest error page |

Only PostGIS is unsurvivable. Everything else degrades — which is the point of §2.5.

---

## 14. Testing strategy `[PROVISIONAL]`

| Layer | Approach |
|---|---|
| `routing/` | Pure unit tests on synthetic graphs with known shortest paths. No network, no LLM. |
| `data/` | `FakeMapidClient` fixtures; PostGIS integration tests against a throwaway container |
| `agent/` | ≥ 30 Indonesian prompts scored against expected tool calls — this **is** the ≥ 80% metric, not a proxy for it |
| Routing accuracy | 10–15 routes vs manual measurement; assert ≤ 15% deviation |
| Carbon | Assert computed values against cited factors; sensitivity across distances |
| Frontend | Bridge unit tests over `ui_command` actions; Playwright smoke on mobile viewport |
| Performance | Lighthouse mobile on throttled 4G; instrumented agent latency across the prompt set |

The intent-precision fixture set is the highest-value test in the project — it is a scored metric, it catches prompt regressions, and it is cheap to run. Build it early.

---

## 15. Open questions

Tracked, not resolved. Each will change part of this document.

| # | Question | Blocks | Status |
|---|---|---|---|
| 1 | **LLM model** | §8.5, §12 | Deferred by decision. Adapter first; choose on measured latency + precision |
| 2 | **Hosting** | §4.1 | Deferred pending MAPID finalist-subdomain requirements |
| 3 | **Sosial Budaya layer** | §5.1 | Undecided (PRD §4.4). Recommend folding into Pariwisata rather than a sixth layer |
| 4 | Graph memory footprint | §4.2 | Unmeasured — estimate only |
| 5 | Mission API real-key behaviour | §6.2 | Contract read from docs, not yet exercised |
| 6 | Field survey density | §7.1 | Unknown until survey completes; affects connector radius |
| 7 | Free-transfer window between TransJogja routes | §7.1 | Fare rule unconfirmed |
| 8 | `W_TRANSFER` / `W_WALK` values | §7.2 | Placeholders in code (300.0 / 1.0) — to be tuned against sample routes |
| 9 | Graph reload without restart | §7.4 | Deferred; restart is acceptable initially |

---

## 16. Revision protocol

This document goes stale by default. Two rules keep it honest:

1. **Update it in the same change that invalidates it.** A PR that changes a contract, a schema, or a component boundary updates the relevant section. A PR that only changes an implementation detail does not.
2. **Move tags in the correct direction.** `[PROVISIONAL]` → `[DESIGNED]` when a decision is made and written down; `[DESIGNED]` → `[VERIFIED]` when confirmed against a running system. A tag that never moves is a section nobody is exercising.

When §15 empties out and the tags are mostly `[VERIFIED]`, drop the provisional banner and cut version 1.0.

---

## Appendix — Terminology

| Term | Meaning |
|---|---|
| **Andong** | Horse-drawn carriage; traditional Yogyakarta transport, first/last-mile connector |
| **Becak** | Cycle rickshaw; same role |
| **Pangkalan** | Stand where andong/becak wait for passengers |
| **Halte** | Bus stop (TransJogja) |
| **Headway** | Interval between consecutive vehicles on a route |
| **Isochrone** | Polygon bounding everywhere reachable within a given travel time |
| **TOD** | Transit-Oriented Development (Permen ATR/BPN 16/2017) |
| **First/last mile** | Journey segment between a transit stop and the true origin or destination |
| **Diterima** | "Accepted" — the only MAPID mission status returned by the API |
