# PATHRIX — Architecture & Build Plan

**Main application: WebGIS AI Agent for multimodal mobility in Yogyakarta**

**Version:** 1.1
**Date:** 18 August 2026
**Competition:** MAPID WebGIS Competition 2026 — Mass Transportation Edition
**Companion documents:** `proposal_pathrix.md` (submitted to judges), `PRD_AI_TOD_Navigator_Yogyakarta.md` (internal spec)

---

## 1. Context and constraints

The landing page (`pathrix-landingpage`) is complete and pitches a product that does not exist yet. This document specifies the product itself.

### 1.1 The timeline is the dominant constraint

| Date | Milestone | Status |
|---|---|---|
| 5 Aug 2026 | Top 50 announced | ✅ passed — we are in |
| 7–20 Aug | Data collection window | 🔄 closes in 2 days |
| 21 Aug – 3 Sep | Engine and tools | upcoming |
| 4–10 Sep | Integration | upcoming |
| 11–14 Sep | **Final submission 14 Sep** | upcoming |
| 18–23 Sep | Presentation and final showcase | upcoming |

**As of 18 August 2026 there are 26 days until submission — roughly three and a half weeks, not six.** Access to the MAPID mission API documentation confirms selection into the Top 50.

Every decision in this document is sized for that remaining window with a small team, not for an ideal architecture. Where a more capable option exists but costs more time, the cheaper option is chosen and the tradeoff is recorded. The build order in §11 reflects the compressed schedule.

### 1.2 Hard targets

Committed in the proposal and PRD. These are not aspirations — they are scored.

| Target | Value | Source |
|---|---|---|
| Initial load on 4G | < 5 seconds | Proposal, PRD §9.2 |
| AI Agent response latency | < 8 seconds | Proposal, PRD §9.2 |
| Intent → tool/layer precision | ≥ 80% over ≥ 30 test prompts | PRD §10 |
| Routing accuracy | ≤ 15% deviation vs manual, 10–15 sample routes | PRD §10 |
| Uptime during judging | 100% | PRD §10 |
| Usability testing | ≥ 3 representative users, documented | PRD §10 |

### 1.3 Explicit non-goals for v1

From PRD §4.3. Recorded here so scope creep has a document to lose an argument with.

- Ticket booking or payment processing. The system guides; it is not a payment gateway.
- Per-minute real-time schedules. Headway and frequency estimates are used where precise open data does not exist.
- Native mobile application. Mobile-first responsive WebGIS only.
- Any statistic or numeric claim not computed from real data or cited to a source.

---

## 2. Repository and deployment topology

### 2.1 Two repositories

```
pathrix-landingpage   (exists)   →  pathrix.id          static build, Vercel/Netlify
pathrix-app           (new)      →  app.pathrix.id      Docker Compose
```

The two are separated deliberately. The landing page is a static prerendered site with three runtime dependencies; the app is a Python geospatial stack with PostGIS, a routing graph, and an LLM. Coupling them would force the marketing site's CI to carry GeoPandas and OSMnx for no benefit, and would tie a five-section brochure's deploy cadence to a research-grade backend's dependency churn.

**The landing page needs no code change to link to the app.** `src/content/site.ts` already reads `VITE_MAP_URL` from the environment with a `#fitur` placeholder fallback. Setting `VITE_MAP_URL=https://app.pathrix.id` points both the hero "Jelajahi Peta" CTA and the Fitur "Buka peta" CTA at the app.

### 2.2 Proposed structure for `pathrix-app`

```
backend/
  app/
    api/          HTTP routes, WebSocket endpoint, dependency wiring
    agent/        LangGraph graph, tool definitions, prompts, LLM adapter
    routing/      graph construction, Dijkstra variants, isochrones, TSP
    data/         MAPID adapter, PostGIS repositories, ETL entrypoints
    models/       Pydantic schemas — the API contract
  tests/
  pyproject.toml
frontend/
  src/
    components/   map, agent sheet, layer panel, itinerary
    lib/          websocket client, map state bridge, API client
    styles/       Tailwind theme (tokens inherited from landing page)
  package.json
data/
  digitization/   TransJogja / KRL route digitization notebooks
  survey/         MAPID Apps survey exports and QC scripts
  fixtures/       sample payloads for offline development
docker-compose.yml
```

### 2.3 Containers

| Service | Image | Role |
|---|---|---|
| `db` | `postgis/postgis:16-3.4` | Spatial database, persistent volume |
| `cache` | `redis:7-alpine` | Precomputed routes, viewport query cache, rate limiting |
| `api` | built from `backend/` | FastAPI + Uvicorn + routing engine + agent |
| `web` | built from `frontend/` | Static build served by the proxy |
| `proxy` | `caddy:2` | TLS termination, reverse proxy, static serving |

**The host is deliberately undecided.** The competition promises finalists a subdomain, so MAPID may host or proxy the finalist applications. The Compose file is written to be host-agnostic — it runs identically on a self-managed Ubuntu VPS, on a container host, or on whatever MAPID provides. This decision is deferred until their requirements are known (see §12).

---

## 3. Technology stack

### 3.1 A tension worth naming

The backend is **Python**, and this differs from the Node/TypeScript backend used in the sibling `heatmap-web-app` project. The divergence is deliberate, for two reasons:

1. **No real Node equivalent exists.** GeoPandas, OSMnx, Shapely, and NetworkX have no Node counterpart with comparable maturity for network analysis and spatial operations. Reimplementing multimodal graph routing in TypeScript would consume the schedule.
2. **The submitted proposal commits to it.** `proposal_pathrix.md` names GeoPandas, OSMnx, PostGIS, and LangChain to the judges. Deviating from a submitted technical proposal is a scoring risk with no compensating benefit.

### 3.2 The stack

| Layer | Choice | Rationale |
|---|---|---|
| API framework | FastAPI + Uvicorn | Async, native WebSocket support, Pydantic schemas double as the API contract |
| Agent orchestration | LangGraph (`langgraph`, `langchain-core`) | See §3.3 |
| Spatial database | PostgreSQL 16 + PostGIS 3.4 | Committed in the proposal; the standard for this work |
| Spatial analysis | GeoPandas, Shapely, OSMnx, NetworkX | Committed in the proposal; graph construction and routing |
| Cache | Redis 7 | Precomputed routes, viewport query results, rate-limit counters |
| Frontend build | Vite + React 18 + TypeScript | Matches existing project conventions |
| Mapping | MapLibre GL JS | Committed in the proposal; WebGL rendering, mobile-capable |
| Basemap | MAPID MAPS | Competition requirement. **Verified** as a plain MapLibre style-spec v8 document — no SDK involved (§5.2) |
| Client state | Zustand | Lightweight; the map ↔ agent bridge does not need Redux |
| Styling | Tailwind CSS 4 | Pragmatic for a dashboard; matches `heatmap-web-app` |

Three additions are not named in the proposal and should be understood as implementation detail rather than architectural change: **Redis** (a caching layer — the proposal already commits to "sistem penyimpanan memori sementara"), **Zustand**, and **Tailwind**.

> **Note on Tailwind.** The landing page deliberately uses no CSS framework. That was the right call for a five-section marketing page with a bespoke visual identity. It does not transfer to a dashboard with sheets, panels, forms, and dense data display. Use Tailwind here.

### 3.3 LangGraph, and why it still satisfies the proposal

The proposal names **LangChain** as the AI Agent framework. LangGraph is part of the LangChain ecosystem and is the current recommended path for tool-calling agents — the classic `AgentExecutor` is effectively superseded. The claim made to the judges remains accurate.

The technical reason to prefer it: this agent must carry **map state** across turns — the current viewport, which layers are active, and the last route computed. A prompt like *"cari rute yang lebih murah dari yang tadi"* only works if the previous route is in state. LangGraph models that explicitly as a typed state object; a classic agent would require bolting it onto conversation memory.

---

## 4. System architecture

```
┌──────────────────────────────────────────────────────────┐
│  Client — React + MapLibre GL JS                         │
│  map viewport, layer state, agent bottom sheet           │
└───────────────┬──────────────────────────────────────────┘
                │  WebSocket: prompt + viewport
                ▼
┌──────────────────────────────────────────────────────────┐
│  FastAPI gateway                                         │
│  rate limiting · bbox validation · schema enforcement    │
└───────────────┬──────────────────────────────────────────┘
                ▼
┌──────────────────────────────────────────────────────────┐
│  LangGraph orchestrator                                  │
│  intent detection → tool calls → narration               │
└──┬────────────────┬───────────────────┬──────────────────┘
   │                │                   │
   ▼                ▼                   ▼
┌────────────┐  ┌──────────────┐  ┌─────────────────┐
│ Routing    │  │ Spatial      │  │ Carbon          │
│ engine     │  │ queries      │  │ calculator      │
│ (NetworkX) │  │ (PostGIS)    │  │ (pure function) │
└─────┬──────┘  └──────┬───────┘  └─────────────────┘
      │                │
      ▼                ▼
┌──────────────────────────────────────────────────────────┐
│  PostgreSQL + PostGIS                                    │
└───────────────▲──────────────────────────────────────────┘
                │  ETL
   ┌────────────┴────────────┬──────────────────┐
   │                         │                  │
GEO MAPID API          OpenStreetMap      Field survey
(Menu Go, Struk Go,    (roads, pedestrian  (andong/becak
 Properti Go)           network)            pangkalan)
```

### 4.1 The two-channel principle

**This is the most important design decision in the system.**

The agent returns **two separate channels** on the same socket:

1. **Prose** — streamed text tokens, shown in the chat sheet.
2. **UI commands** — structured instructions the map executes: toggle a layer, fly to a bounding box, draw a route.

They are never mixed. The LLM does not emit map instructions inside its prose for the client to parse out; it emits tool calls, and the tool layer produces typed UI commands. This is what makes the proposal's central claim — *"AI Agent yang memanipulasi antarmuka peta secara otonom"* — an implementable contract rather than an aspiration.

---

## 5. Data layer

### 5.1 Schema sketch

```sql
transit_stops      id, name, mode, operator, geom(Point), source, updated_at
transit_routes     id, name, operator, mode, headway_min, fare_idr, geom(LineString)
route_stops        route_id, stop_id, seq, travel_time_from_prev_s
pangkalan          id, type(andong|becak), operating_hours, fare_base, fare_per_km,
                   photo_url, geom(Point), surveyor, surveyed_at
poi                id, source(menugo|struckgo|activities), nama_tempat, kategori,
                   jam_buka, jam_tutup, harga_rata_rata, foto_url, raw jsonb,
                   geom(Point), fetched_at
properti           id, kategori_properti, jenis_properti, alamat, foto_url,
                   raw jsonb, geom(Point), fetched_at
buildings          id, category, name, geom(Polygon)
walk_nodes         id, geom(Point)
walk_edges         u, v, length_m, geom(LineString)
isochrones         stop_id, minutes, geom(Polygon), computed_at
emission_factors   mode, g_co2_per_km, source_citation
```

Two conventions, applied everywhere:

- **`source` and `updated_at` on every table.** The competition requires metadata and processing method for each dataset (Deliverable 3). Recording provenance at write time is trivial; reconstructing it in week six is not.
- **`emission_factors` stores its own citation.** The carbon figures must be traceable to KLHK/IPCC. Storing the citation next to the number makes it impossible for the two to drift apart.

MAPID mission fields worth promoting out of `raw` into real columns, because the agent queries them directly: `jam_buka` / `jam_tutup` (Menu Go — "is it open now?") and `harga_rata_rata` (Struck Go — price range).

### 5.2 MAPID integration — resolved

This was previously the largest external unknown in the project. It is now documented and verified against live endpoints.

**There is no MAPID SDK.** MAPID MAPS is a keyed tile service plus a REST API, consumed through plain `maplibre-gl`. No npm package, no wrapper, no framework binding.

#### Basemap

```
https://v2.basemap.mapid.io/styles/{style-name}/style.json?key={MAPID_BASEMAP_KEY}
```

Styles: `street-v2.0` · `satellite-v2.0` · `dark-v2.0` · `light-v2.0`.
Raster preview tiles: `/styles/{style}/tiles/256/{z}/{x}/{y}.png?key=`.

Verified: **HTTP 200 with a key, 401 without.** The document is MapLibre **style spec version 8** with 253 layers. Sources are `mapidtiles`, `indonesiatiles`, and `ocean` (vector) plus a Natural Earth raster relief; `glyphs` and `sprite` are keyed endpoints on the same host.

The dedicated `indonesiatiles` vector source matters — Yogyakarta detail comes from MAPID's own tileset rather than a global fallback. Integration is a drop-in:

```ts
new maplibregl.Map({ style: `https://v2.basemap.mapid.io/styles/street-v2.0/style.json?key=${KEY}` })
```

#### Competition mission datasets

All four share one request envelope:

```http
POST https://server.mapid.io/web/competition/{menugo|propertigo|struckgo|activities}
Content-Type: application/json
x-api-key: {MAPID_MISSION_API_KEY}
```

```jsonc
{
  "feature": { "type": "Polygon", "coordinates": [[[110.30,-7.85],[110.45,-7.85],[110.45,-7.72],[110.30,-7.72],[110.30,-7.85]]] },
  "start_date": "2026-01-01",   // optional, YYYY-MM-DD
  "end_date":   "2026-12-31",   // optional
  "hashtag":    ["kuliner"],    // optional, case-insensitive partial match on description
  "author":     "budi"          // optional, matches user name / full_name
}
```

> The endpoint is spelled **`struckgo`**, not `strukgo`.

**Responses.** Mission endpoints return `{ success, message, features: [...], pagination: { total, limit, offset, hasMore } }` with `limit` defaulting to 100. The `activities` endpoint differs — it returns `{ success, message, data: { activities: [...] } }` with `_id`, `title`, `description`, `geometry`, `medias[]`, `user_name`, `user_full_name`, `community_name`. **Do not write one parser for both.**

Errors: `{"success": false, "message": "feature is required in body"}`; an out-of-range `offset` returns HTTP 400 naming the valid bound.

**Documented server behaviour:** polygon queries use a spatial index, and only missions with status `"Diterima"` are returned — hardcoded server-side, not overridable.

| Dataset | Properties |
|---|---|
| `menugo` | `nama_tempat`, `jenis_tempat`, `tanggal`, `waktu`, `jam_buka`, `jam_tutup`, `foto_tempat`, `foto_menu_1`, `foto_menu_2`, `link_menu` |
| `struckgo` | `nama_tempat`, `kategori_tempat`, `tanggal`, `waktu`, `metode_pembayaran`, `harga_rata_rata`, `foto_struk`, `catatan` |
| `propertigo` | `kategori_properti`, `jenis_properti`, `tanggal`, `alamat`, `foto_tampak_depan`, `foto_spanduk`, `catatan` |
| `activities` | Community posts — title, description, photos, author, location |

#### Geocoding — available and unauthenticated

`https://nominatim.mapid.io` serves standard Nominatim, forward and reverse, with **no key required**. Verified against Yogyakarta:

```
/search?q=Malioboro%20Yogyakarta&format=json   → -7.7952921, 110.3657274
/reverse?lat=-7.7956&lon=110.3695&format=json  → highway/footway, OSM way 1124284588
```

This closes a real gap: `calculate_route` takes coordinates, but users type *"rute ke Malioboro"*. See §7.3.

#### Two keys, two scopes

| Key | Scope | Transport |
|---|---|---|
| `MAPID_BASEMAP_KEY` | Basemap styles, tiles, glyphs, sprite | `?key=` query parameter |
| `MAPID_MISSION_API_KEY` | Competition mission datasets | `x-api-key` request header |

**These have different exposure profiles and must not be conflated.** The basemap key necessarily reaches the browser — MapLibre fetches the style URL directly. The mission key must never leave the server.

The adapter boundary at `app/data/mapid.py` stays exactly as designed. It now has a real implementation instead of a fixture-backed fake, and fixtures remain useful for offline development and tests.

### 5.3 Mirror the mission data, do not proxy it

The mission API is itself a polygon query, which maps almost 1:1 onto the agent's `get_data_in_viewport`. That invites calling it live on every request. **Don't.**

ETL the mission datasets into PostGIS on a schedule and serve viewport queries from the local mirror:

- **Latency budget.** A remote POST with a documented 30-second timeout ceiling sits inside the < 8s agent budget. A local PostGIS query does not.
- **Judging-day uptime.** The 100% uptime target should not depend on a third party being available during the window.
- **Spatial joins need the data locally anyway.** Intersecting POIs with transit isochrones — the proposal's *Spatial Intersection* commitment — cannot be done against a remote paginated endpoint.
- **The data is stable.** Only `"Diterima"` records are returned, so a scheduled refresh suffices; there is nothing real-time to miss.

Fetch strategy: one polygon covering the study area, paginate to exhaustion, upsert by `_id`, stamp `fetched_at`. Re-run nightly and once immediately before judging.

---

## 6. Routing engine

This is the technical core and the highest-risk component. It is specified in detail here so it can be built without re-deriving the design.

### 6.1 Approach: a time-independent frequency graph

One merged directed multigraph, built at startup, held in memory, rebuilt by a scheduled job when source data changes.

**The justification, which should be stated in the final documentation:** no GTFS feed or public API exists for TransJogja (confirmed in PRD §5.2). Service must therefore be modelled by **headway** rather than timetable — and the PRD explicitly sanctions this (§4.3, §5.2). Because headway-based service has no departure times to simulate, the cost of every edge is **independent of when the traveller arrives at it**. That is precisely the condition under which plain Dijkstra is correct and a time-dependent routing engine is unnecessary.

This is why the system does not need OpenTripPlanner, a JVM service, or timetable simulation. It is a real simplification with a sound basis, not a shortcut.

### 6.2 Graph construction

**Nodes**

| Type | Source |
|---|---|
| Walk nodes | OSMnx `graph_from_place(..., network_type="walk")` over the study area |
| Transit stops | Digitized Dishub DIY route maps + OSM + field validation |
| Pangkalan | Field survey via MAPID Apps |

**Edges**

| Edge type | Cost (seconds) | Fare (IDR) |
|---|---|---|
| `walk` | `length_m / 1.33` (≈ 4.8 km/h) | 0 |
| `board` | `headway_min × 30` (expected wait = headway/2) + boarding penalty | route flat fare |
| `ride` | estimated in-vehicle time between consecutive stops | 0 (paid at boarding) |
| `alight` | small fixed penalty | 0 |
| `transfer` | inter-stop walk time + `headway_min × 30` of the next route | flat, unless within a free-transfer window |
| `andong` / `becak` | `distance_m / mode_speed` + negotiation constant | `fare_base + distance_km × fare_per_km` |

Andong and becak edges connect a pangkalan to any node within a radius, reflecting that they are on-demand point-to-point services rather than fixed routes. This is what makes them first/last-mile *connectors* in the graph rather than decorative markers on the map — the differentiator the whole product rests on.

### 6.3 Three options, one graph, three weight functions

The PRD's *termudah / tercepat / termurah* filter is not three algorithms. It is one graph traversed with three different edge-weight functions:

| Option | Objective |
|---|---|
| `tercepat` | minimize `Σ time_s` |
| `termurah` | minimize `Σ fare_idr` |
| `termudah` | minimize `transfers × w₁ + walking_metres × w₂` |

This is cheap to implement, easy to explain to judges, and genuinely correct. Weights `w₁` and `w₂` are tunable constants, documented with their chosen values.

### 6.4 Derived analyses

**Isochrones.** Dijkstra from a transit stop with a time cutoff; take all reachable nodes; compute a concave hull; store the polygon in PostGIS. Precompute for major transit nodes so the map can display service catchment instantly. This satisfies the proposal's *Isochrone Mapping & Spatial Intersection* commitment.

**Multi-stop itineraries.** Compute the pairwise cost matrix between requested stops using the routing engine, then apply nearest-neighbour construction followed by 2-opt improvement — the PRD's "heuristik TSP ringan" (§6). Bias the ordering toward legs that stay near transit nodes.

**Carbon savings.**

```
saved_g_co2 = (distance_km × factor[private_vehicle])
            − (distance_km × factor[chosen_mode])
```

Factors come from `emission_factors` with their citations. The UI displays the source and the assumption alongside the figure — the PRD names unsourced carbon numbers as a credibility risk (§13).

---

## 7. The AI Agent — Spatial Orchestrator

### 7.1 State

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    viewport: Viewport             # bbox, zoom, centre — pushed by client each turn
    active_layers: set[str]
    last_route: Route | None       # enables "yang lebih murah dari tadi"
    ui_commands: list[UICommand]   # drained after each turn, sent to client
```

`viewport` is what makes viewport-awareness work: the client sends its current bounding box with every message, so *"ada kuliner apa di area ini?"* resolves against what the user is actually looking at.

`last_route` is what makes conversational follow-up work. It is the difference between a chatbot and an agent with memory.

### 7.2 Graph topology

```
        ┌──────────┐
  ──────▶   plan   │  LLM with tools bound
        └────┬─────┘
             │ tool_calls?
        ┌────▼─────┐
        │  tools   │  ToolNode — executes, appends results
        └────┬─────┘
             │ loop back to plan
        ┌────▼─────┐
        │ respond  │  final narration, drain ui_commands
        └──────────┘
```

### 7.3 Tools

Exactly the five named in PRD §9.1, so the submitted document and the implementation agree.

| Tool | Signature | Returns |
|---|---|---|
| `toggle_layer` | `(layer_id: str, on: bool)` | confirmation + `UICommand` |
| `get_data_in_viewport` | `(bbox: BBox, data_type: str, limit: int)` | features from PostGIS |
| `calculate_route` | `(start, end, modes, optimize)` | `Route` with legs, time, fare |
| `plan_multistop` | `(stops: list, optimize)` | ordered `Itinerary` |
| `calculate_carbon_savings` | `(route: Route)` | grams CO₂ + source citation |

**Place-name resolution is an internal helper, not a sixth tool.** `app/data/geocode.py` wraps `nominatim.mapid.io` (§5.2) and is called *inside* `calculate_route` and `plan_multistop` so their `start` / `end` / `stops` arguments accept either coordinates or a place string. Keeping it internal preserves the exact five-tool surface the PRD commits to — worth protecting, since the PRD is itself a graded deliverable. Promote it to a tool later only if the agent needs standalone place search.

### 7.4 Guardrail — the anti-hallucination contract

**The LLM orchestrates and narrates. It never produces a number.**

Every distance, duration, fare, and CO₂ figure originates from a tool return and is interpolated into the response. This is the proposal's central technical claim (*"Pemisahan komputasi ini memastikan sistem sepenuhnya terhindar dari risiko tebakan palsu (halusinasi) model bahasa"*) and it must be enforced structurally — by assembling responses from typed tool output — not by asking the model nicely in a system prompt.

Additional guardrails, each addressing a named risk in PRD §13:

- **Bounding box area cap** on `get_data_in_viewport`. Unbounded viewport queries are named as a performance risk; reject or clamp bboxes above a threshold.
- **Parameter validation before execution.** Tool arguments are validated against Pydantic schemas; invalid calls return a structured error the agent can recover from, not an exception.
- **Fallback message** when intent is unrecognised, rather than a guessed tool call.
- **Tool call budget** per turn, to bound latency.

---

## 8. Frontend and design

### 8.1 Layout — mobile-first, map-dominant

The map is full-bleed. The agent lives in a **bottom sheet with three snap points**: peek (input only), half (conversation + input), full (conversation history).

The layer panel is a **second sheet**, not a desktop sidebar. A sidebar on a 390px screen is exactly how the existing WebGIS tools lose the users this product exists for — the proposal's own problem statement says so. On desktop the sheet is promoted to a left rail; the component tree does not change.

### 8.2 Screens

| Screen | Purpose |
|---|---|
| Dashboard | Entry point. PRD §8.2 requires a dashboard *before* the complex map — a first-time visitor should not land in a layer-dense interface. |
| Map + Agent | The core. Full-bleed map, agent sheet, layer sheet. |
| Route detail | Staged itinerary: walk → halte → transit → andong/becak → destination. Mode-coded timeline. |
| Sustainability | Carbon saved, with the calculation basis and source visible. |

### 8.3 Visual language

**Inherit the landing page's design tokens** for brand continuity. Copy the values from `src/styles/tokens.css` into the app's Tailwind theme rather than importing across repositories.

```
--sky-0 #eff5fa   --sky-1 #dfeaf3   --sky-2 #c6d9e8
--ink #101e2a     --ink-soft #17293a
--blue #1f6592    --blue-lift #5aa9dd
--warm #d9a521    --warm-text #f2c94c
--paper #e7f0f7
```

Two rules carry over from the landing page:

- **The WCAG-corrected token values stay corrected.** `--on-dark-meta`, `--on-light-meta`, and `--warm-text` deviate from the original prototype specifically to meet AA contrast. Do not "fix" them back.
- **Gold is a functional accent, not decoration.** It marks the sustainability dimension and active state, consistent with the landing page's usage.

One rule does **not** carry over: the landing page's two-background-colour restriction. A dashboard legitimately needs surface elevation — sheets, cards, and overlays require more than two surface values.

### 8.4 Map styling

**Basemap style.** `street-v2.0` is the default — its palette sits closest to the landing page's `--sky-*` family. `dark-v2.0` backs the dark treatment. Both are fetched with `MAPID_BASEMAP_KEY` (§5.2). Check route and marker contrast against *both* styles before fixing a palette: a line colour that reads cleanly on street will disappear on satellite.

| Layer | Treatment |
|---|---|
| TransJogja / KRL / YIA | Distinct line colour per operator, weight by mode |
| Halte / stasiun | Circle markers, size by interchange importance |
| Andong / becak pangkalan | Custom icons; popup carries the field survey photo and fare range |
| Properti Go | **Server-side clustering** — committed in the proposal for mobile performance |
| Menu Go / Struck Go | Category-coloured markers; popup carries `foto_tempat`, opening hours (`jam_buka`/`jam_tutup`), and `harga_rata_rata` where present |
| Buildings | Polygon fill with low opacity |
| Active route | Mode-coloured line with transfer markers at each mode change |

---

## 9. Real-time contract

WebSocket, as committed in the proposal. Message shapes:

```
client → server
  { type: "user_message",     text: string, viewport: Viewport }
  { type: "viewport_changed", bbox: BBox, zoom: number }

server → client
  { type: "token",      delta: string }                        streaming prose
  { type: "ui_command", action: "toggle_layer" | "fly_to"
                              | "draw_route" | "highlight",
                        payload: object }
  { type: "done",       route?: Route, carbon?: CarbonResult }
  { type: "error",      message: string }
```

**Streaming is a latency requirement, not a nicety.** The < 8s budget is about *perceived* responsiveness, and perceived latency is time-to-first-token, not time-to-complete. A response that begins rendering at 1.2s and finishes at 7s feels fast. The same response delivered whole at 7s does not.

---

## 10. Non-functional requirements

### 10.1 Meeting < 5s load on 4G

- Code-split MapLibre GL JS out of the entry bundle.
- Lazy-load layer data on activation, never all layers at once.
- Vector tiles rather than raw GeoJSON for any layer above a few thousand features.
- Server-side clustering for Properti Go.
- Compress and cache aggressively; fingerprinted assets get long TTLs.

### 10.2 Meeting < 8s agent response

- Stream tokens over the WebSocket.
- Precompute routes for popular origin-destination pairs into Redis (committed in the proposal).
- Cache viewport query results keyed by rounded bbox.
- Keep the typical turn to ≤ 3 tool calls; bound with a per-turn budget.
- Hold the routing graph in memory — never rebuild per request.

### 10.3 Security

- **Rate limiting at the API gateway** — committed in the proposal, addressing request-flood risk.
- Bounding box size caps on spatial queries.
- No secrets in client code; the LLM API key never leaves the backend.
- **Two MAPID keys with different exposure.** `MAPID_BASEMAP_KEY` necessarily reaches the browser — MapLibre fetches the style URL directly — so scope it to basemap access only. `MAPID_MISSION_API_KEY` is server-only and must never appear in a client bundle or a proxied response. Both live in environment variables, never in source.
- CORS pinned to the app origin.
- Pydantic validation on every inbound payload.

---

## 11. Build order

Follows PRD §11, **compressed to the 26 days that actually remain** as of 18 August 2026.

| Window | Focus | Deliverable |
|---|---|---|
| **Now – 20 Aug** (3 days) | Finish field survey of andong/becak pangkalan · digitize TransJogja and KRL routes · stand up PostGIS schema · run the MAPID mission ETL (§5.3) — **the contract is known, so this is execution, not discovery** | Populated database |
| **21 Aug – 3 Sep** (2 weeks) | Build the routing graph · implement the five backend tools · thematic layers · **freeze the API contract by ~27 Aug** | Working routing engine, documented API |
| **4–10 Sep** (1 week) | LangGraph orchestration · WebSocket transport · frontend integration · sustainability tracker | End-to-end working application |
| **11–14 Sep** (4 days) | User testing (≥ 3 users) · precompute and caching · metadata documentation · **submission 14 Sep** | Submitted deliverables |

### 11.1 What the compressed schedule changes

Three consequences of having 26 days rather than six weeks, in priority order:

1. **Freeze the API contract by ~27 August.** Everything downstream is gated on it.
2. **Build the frontend against a mock from day one of the engine block.** Map interaction, the agent sheet, and layer controls depend only on the *shape* of responses, not on the routing engine working. Serialising frontend work behind the backend is the single most likely way to miss 14 Sep.
3. **The MAPID work is no longer research.** §5.2 documents the full contract, so write the ETL against the real endpoints immediately rather than against fixtures.

If the schedule slips, cut in this order: gamified sustainability extras → Urban Planning layer → multi-stop itineraries. Protect the core loop (prompt → layer toggle → route → carbon) — it is what every scored metric measures.

### 11.2 Competition deliverables checklist

From PRD §14:

1. Public WebGIS link — finalist subdomain, MAPID MAPS basemap, mobile-first
2. Final PRD (updated)
3. Metadata for all datasets + processing methodology
4. Survey activity documentation + budget usage
5. AI Agent explanation — input, process, output, validation per capability
6. Final presentation deck — 6 minutes + 4 minutes Q&A

---

## 12. Open decisions

Recorded rather than invented. Each needs a decision before or during the build.

### 12.1 LLM model — undecided

Not yet evaluated. Keep the provider behind a thin adapter at `app/agent/llm.py` so the choice is a late, cheap swap.

The tradeoff, stated honestly:

- The **≥ 80% intent-precision target** argues for a stronger model — tool-call accuracy on ambiguous Indonesian prompts is exactly what that metric measures.
- The **< 8s latency budget** and student-project cost constraints argue for a faster, cheaper one.
- A complexity-routed split (cheap model for simple layer toggles, strong model for multi-stop routing) gives the best cost/quality curve but adds a classifier to build, tune, and evaluate.

**Recommendation: decide after the first tool-calling prototype produces real latency and accuracy numbers**, not before. Build the adapter first.

### 12.2 Hosting — deferred

The competition promises finalists a subdomain, which may mean MAPID hosts or proxies the application. The Compose file is written host-agnostic. Decide once their requirements are published.

### 12.4 Sosial Budaya dimension — undecided

PRD §4.4 leaves this open. **Recommendation: fold it into the Pariwisata layer** rather than adding a sixth thematic layer. A half-defined layer is worse than a well-integrated one, and layer count is already a mobile-usability concern.

### 12.5 Status

Top 50 curation (announced 5 August 2026) has been passed — access to the MAPID mission API documentation confirms it. The remaining risk is schedule, not selection.

---

## 13. Verification

| What | How |
|---|---|
| Intent precision | Fixture set of ≥ 30 Indonesian prompts with expected tool calls; scored automatically |
| Routing accuracy | 10–15 sample routes compared against manual measurement; assert ≤ 15% deviation |
| Carbon figures | Cross-check computed values against the cited KLHK/IPCC source; sensitivity check across distances |
| Load performance | Lighthouse mobile against the deployed build; assert < 5s on throttled 4G |
| Agent latency | Instrument time-to-first-token and time-to-complete across the prompt fixture set |
| Viewport queries | Pan/zoom scenarios asserting returned features fall within the active bbox |
| Concurrency | Load test sized for judging-day traffic |
| Usability | ≥ 3 representative users (perantau students, tourists); findings documented |

---

## Appendix A — Traceability

Every technology named here appears in `proposal_pathrix.md`, or the deviation is justified above.

| Component | Proposal | Status |
|---|---|---|
| React | ✅ named | — |
| MapLibre GL JS | ✅ named | — |
| MAPID MAPS basemap | ✅ named | **Verified** — MapLibre style v8 via `?key=` (§5.2) |
| MAPID mission API | ✅ named | **Verified** — POST + `x-api-key`, polygon body (§5.2) |
| Nominatim geocoding | ➕ addition | MAPID-hosted, unauthenticated; internal resolver (§7.3) |
| PostgreSQL + PostGIS | ✅ named | — |
| GeoPandas, OSMnx | ✅ named | — |
| LangChain | ✅ named | LangGraph — same ecosystem, §3.3 |
| Docker, Linux | ✅ named | — |
| WebSocket | ✅ named | — |
| Rate limiting / API gateway | ✅ named | — |
| Precompute + caching | ✅ named | Implemented with Redis |
| Redis | ➕ addition | Implementation of the committed caching layer |
| FastAPI | ➕ addition | Proposal says "backend Python" without naming a framework |
| Zustand, Tailwind | ➕ addition | Frontend implementation detail |

## Appendix B — Terminology

| Term | Meaning |
|---|---|
| **Andong** | Horse-drawn carriage; traditional Yogyakarta transport, first/last-mile connector |
| **Becak** | Cycle rickshaw; same role |
| **Pangkalan** | Stand or base where andong/becak wait for passengers |
| **Halte** | Bus stop (TransJogja) |
| **Headway** | Interval between consecutive vehicles on a route |
| **Isochrone** | Polygon bounding everywhere reachable within a given travel time |
| **TOD** | Transit-Oriented Development (Permen ATR/BPN 16/2017) |
| **First/last mile** | Journey segment between a transit stop and the true origin or destination |
