# MAPID Routing + PATHRIX Transit Handoff

## Objective

Combine a verified MAPID Routing API with PATHRIX's LLM and transit graph.

Resulting itinerary ownership:

```text
User intent / place names
        │
        ▼
LLM + PATHRIX transit graph ── choose stops, bus/rail, fares, transfers
        │
        ├── MAPID Routing ── road-following walk/drive geometry, distance, duration
        └── local OSM graph ── fallback road topology when MAPID is unavailable
```

MAPID must own only road-leg geometry/distance/duration. PATHRIX must remain
the source of truth for TransJogja/KRL/YIA service topology, schedule metadata,
fare, and transfers. Do not invent a transit timetable from a road route.

## Current verified state

- App is running locally: frontend `http://localhost:5173`, API
  `http://localhost:8000`.
- Redis and Postgres are running via `docker compose up -d db cache`.
- Local OSM pedestrian graph has been ingested only for UGM corridor
  `110.369,-7.7795 → 110.381,-7.759`: **953 nodes, 2,480 directed edges**.
- `Halte RS Sardjito Timur` (database id `234`) to `Halte Kopma UGM` (id
  `471`) now computes as walk-only: **1,195.8 m**, **899.1 s**, Rp0.
- A safety cap now snaps a transit stop/pangkalan to local walk graph only
  within 500 m. Never remove this cap when importing a partial OSM area.
- `transportation-data/normalized/osm-road-segments.geojson` contains 312
  OSM drive LineStrings for reviewed adjacent bus-stop pairs. They are map
  geometry, not proof a whole bus route is attachable.
- 84 target stop positions on routes 12/3A/3B/4A/4B remain unresolved. MAPID
  road routing cannot fix missing transit topology.

## Hard constraints

1. Do **not** assume `MAPID_MISSION_API_KEY`, GeoServer key, or basemap key
   authorizes routing. They are separate products/contracts.
2. Do **not** guess a MAPID routing URL, authorization header, request shape,
   profiles, pricing, quota, or response fields.
3. Do **not** replace current local OSM routing until a real MAPID response is
   validated. MAPID failure must not make existing walk/transit routes fail.
4. Do **not** use MAPID road distance/duration to change a bus schedule,
   transit fare, or transfer count.
5. Never call a road API once per OSM graph edge. Coalesce a contiguous walk
   corridor first, then make at most one routing request per corridor.
6. Never log API keys or commit them. Add only `.env.example` placeholders.
7. Preserve user/Claude changes outside this scope. Do not reset the worktree.

## Required input before implementation

Obtain all of this from the MAPID owner/dashboard/documentation:

- Routing base URL and API version.
- Auth method and a dedicated routing key.
- Supported profiles: minimum `foot`/walking; record drive/bike only if truly
  supported.
- Request contract: coordinates order, waypoints limit, optional language/
  unit/avoid parameters.
- Response contract: distance units, duration units, GeoJSON/polyline format,
  error body, rate-limit headers.
- Plan/quota and permitted caching duration.
- A working Yogyakarta request/response fixture with secrets removed.

Stop and ask for this input if unavailable. Do not infer it from basemap URLs.

## Phase 0 — contract spike

Create no production behavior yet.

1. Add `backend/app/data/mapid_routing.py`.
2. Define a narrow protocol, e.g. `MapidRoutingClient.route(profile, points)`.
3. Add typed internal result carrying:
   - `coordinates: list[list[float]]` in `[lon, lat]` order;
   - `distance_m: float`;
   - `duration_s: float`;
   - `provider: "mapid_routing"`;
   - provider response metadata safe for display.
4. Implement `HttpMapidRoutingClient` only from verified contract.
5. Implement `FakeMapidRoutingClient` for all automated tests.
6. Add `MAPID_ROUTING_BASE_URL`, `MAPID_ROUTING_API_KEY`,
   `MAPID_ROUTING_ENABLED`, `MAPID_ROUTING_TIMEOUT_S` to settings and
   `.env.example`. Defaults must leave current behavior unchanged.
7. Run exactly one manually authorized live request against known UGM points.
   Validate first/last coordinates, metre/second units, and a non-empty
   road-following geometry. Keep only sanitized fixture data in repository.

Exit condition: verified response contract exists and tests never call MAPID.

## Phase 1 — resilient road-leg service

Implement a service in `backend/app/routing/road_legs.py`.

Inputs:

- profile (`foot` initially);
- ordered origin/destination coordinates;
- local fallback geometry/distance/time.

Rules:

1. Request MAPID only when `MAPID_ROUTING_ENABLED=true` and client is
   configured.
2. Validate every response: at least two finite coordinates, start/end within
   a documented tolerance of requested points, non-negative distance/duration.
3. Cache successful responses in Redis using a versioned key with profile and
   rounded coordinates. TTL must match MAPID permission/quota. Cache only
   sanitized response data.
4. Apply short timeout and bounded retry policy. Do not block an itinerary for
   repeated provider failure.
5. On timeout, 429, invalid body, or provider 5xx: retain local OSM values and
   stamp provider source `osm_fallback`. Route calculation still succeeds.
6. Do not fall back to straight-line geometry when either MAPID and OSM lack a
   route. Return normal `NoRouteFoundError`.

Add health/metrics counters: MAPID success, cache hit, provider failure,
fallback used, invalid response. Never include coordinates-plus-key or secrets
in error logs.

## Phase 2 — integrate without weakening transit routing

Current seams:

- Core shortest path: `backend/app/routing/shortest_path.py:calculate_route`.
- Graph assembly: `backend/app/routing/build.py:build_graph_from_network`.
- Agent route tool: `backend/app/agent/tools.py:make_calculate_route_tool`.
- Runtime dependency wiring: `backend/app/agent/runtime.py:AgentRuntime.create`.
- Backend DTO: `backend/app/models/routing.py:RouteLeg`.
- Frontend DTO: `frontend/src/lib/types.ts:RouteLeg`.
- Route rendering: `frontend/src/lib/bridge.ts`.
- Route timeline: `frontend/src/components/RouteDetail.tsx`.

Implementation order:

1. Keep `calculate_route` deterministic and graph-only. It selects modal
   topology, fares, and transit legs exactly as today.
2. Add a post-routing async enrichment stage in the agent tool/service layer,
   not inside NetworkX weight computation.
3. Coalesce each maximal run of `walk` legs into one corridor. Preserve the
   original graph legs internally for topology/accounting; return one enriched
   display walk leg only if totals and endpoint order remain consistent.
4. Send the corridor's first/last real coordinates to MAPID `foot` routing.
5. Replace only that display corridor's `coordinates`, `distance_m`, and
   `time_s` with verified MAPID result. Set `source="mapid_routing"`.
6. If fallback occurs, retain local values and use `source="osm_fallback"`.
7. Never modify `ride`, `board`, `alight`, `transfer`, `andong`, or `becak`
   legs with MAPID result.
8. Recompute route totals from returned display legs exactly once. Fare and
   transfer count must remain from graph topology.
9. Keep existing `RouteLeg.coordinates` contract (`[lon, lat]` pairs), so
   MapLibre route drawing needs no geometry-format adapter.

First release supports only `foot`. Add driving/bike only after product owner
defines when they are valid for PATHRIX users.

## Phase 3 — LLM behavior

LLM does not call MAPID directly. It calls existing `calculate_route` tool;
backend performs enrichment.

Update tool descriptions/system prompt only to state:

- road portions may be MAPID-calculated or OSM fallback;
- transit fare/schedule remain sourced from PATHRIX normalized data;
- `source` metadata must be disclosed when presenting a route;
- provider failure is not a reason to invent a route, duration, fare, or
  transfer.

Do not ask LLM to choose raw API profiles or construct coordinate requests.

## Phase 4 — UI provenance

1. `RouteDetail.tsx` must show a small factual source label for each road leg:
   `MAPID road route` or `OSM fallback`.
2. Keep current source/effective/freshness labels for transit legs.
3. `bridge.ts` already renders `RouteLeg.coordinates`; MAPID LineStrings must
   replace direct endpoint lines automatically.
4. Do not draw a solid route across unresolved transit gaps. Existing map
   segment style remains estimated/dashed for OSM review artifacts.
5. No new map hue. Follow `docs/DESIGN.md` palette rules.

## Tests and acceptance

Backend unit tests:

- MAPID client request/auth/response parsing using mocked HTTP transport.
- Invalid geometry, wrong coordinate order, 429, timeout, and 5xx all fall
  back to OSM without breaking route calculation.
- Redis cache hit avoids second client request.
- Adjacent walk edges are coalesced to one provider call.
- Transit ride time/fare/transfer totals remain unchanged by enrichment.
- MapID geometry appears in returned `RouteLeg.coordinates`.
- Existing local OSM route works when routing API is disabled.

Focused real verification after credentials are available:

1. `Halte RS Sardjito Timur` → `Halte Kopma UGM`, `walk + bus`, `tercepat`.
2. Confirm a route exists even when no bus ride is selected.
3. Confirm walk geometry follows roads, not a direct line.
4. Confirm API response shows provider source and no fabricated transit data.
5. Disable MAPID routing; repeat and confirm OSM fallback returns a route.
6. Screenshot route on Peta and inspect source labels.

Suggested checks:

```bash
cd backend
uv run rtk pytest tests/routing tests/agent -q
uv run rtk ruff check app tests
cd ../frontend
npm run lint
npm run build
```

## Existing operational commands

```bash
docker compose up -d db cache

cd backend
uv run python -m app.data.ingest walk-network \
  --bbox 110.369 -7.7795 110.381 -7.759
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

cd ../frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

Restart API after a walk-network import: `AgentRuntime.create` builds graph
once at startup.

## Explicit non-goals

- Do not claim MAPID Routing supplies official TransJogja shape, timetable,
  fare, or transfer data.
- Do not use road routing to bypass the 84 unresolved transit stops.
- Do not import all DIY OSM data by default. Use scoped bbox and 500 m snap
  cap; expand area deliberately and verify no long-distance synthetic snaps.
- Do not remove OSM fallback until MAPID availability, quota, and contract are
  proven in production.
