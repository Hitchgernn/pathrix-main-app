# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

PATHRIX — a WebGIS AI agent for multimodal mobility navigation in Yogyakarta (TransJogja bus, KRL rail, YIA airport rail, plus andong/becak first/last-mile), built for the MAPID WebGIS Competition 2026. `docs/ARCHITECTURE.md` is the full system design; `docs/PLAN.md` has the build plan, schedule, and stack rationale. **When the docs and the code disagree, the code is right — update the relevant doc in the same change that invalidates it** (`docs/ARCHITECTURE.md` §16).

`backend/` (FastAPI + LangGraph + PostGIS) and `frontend/` (Vite + React + MapLibre) both have code. Frontend implementation is the other person's lane (see Team workflow below) — don't extend it unless explicitly asked; what's there is a transcription of the Claude Design canvas, not an independent design.

## Commands

### Backend

All commands run from `backend/`, using `uv`:

```sh
uv sync --extra dev              # install deps (creates .venv)
uv run uvicorn app.main:app --reload   # run the API locally
uv run ruff format app tests     # format
uv run ruff check . --fix        # lint
uv run pytest -q                 # full test suite
uv run pytest tests/routing -q   # one directory
uv run pytest tests/routing/test_shortest_path.py::test_tercepat_picks_the_priced_fast_path  # one test
```

**Most of the test suite needs a live Postgres/Redis.** `data/`, `agent/`, and `api/` tests hit a real `postgis/postgis:16-3.4` + `redis:7-alpine` via the `db_session` fixture (`tests/conftest.py`) — they `pytest.skip` gracefully if unreachable rather than failing. Bring them up first:

```sh
docker compose up -d db cache    # from the repo root
```

`routing/` tests are pure — synthetic graphs, no network, no DB, no LLM — and always run.

CI (`.github/workflows/backend-ci.yml`) runs `ruff check` + `pytest` with `postgis/postgis` and `redis:7-alpine` service containers on every push/PR touching `backend/` — both are required, since the rate-limit middleware and several fixtures hit Redis with no skip-if-unreachable path (unlike the DB-dependent tests).

No LLM provider is configured by default (`LLM_PROVIDER` unset) — this is deliberate (see Agent below), not a setup step you're missing.

### Frontend

All commands run from `frontend/`:

```sh
npm install
npm run dev      # :5173, proxies /api and /ws to :8000
npm run lint     # tsc --noEmit
npm run build    # typecheck + production build
```

`npm run build` **fails without `VITE_MAPID_BASEMAP_KEY`** and that guard is deliberate: Vite inlines `import.meta.env` at build time, so a keyless build folds away the guard in `MapCanvas` and Rollup drops the whole MapLibre chunk — you'd ship a working-looking app with no map in it. There is no test suite here yet; `tsc` is the gate.

## Architecture

### Module layout and the dependency rule

```
backend/app/
  api/       HTTP + WebSocket surface — no business logic
  agent/     LangGraph graph, tool bindings, LLM adapter — never computes numbers, never touches DB directly
  routing/   graph construction, Dijkstra variants, isochrones, TSP — no HTTP, no LLM, no MAPID, no DB (pure, network-free)
  data/      PostGIS repositories, MAPID adapter, geocode resolver, ETL — no routing algorithms
  models/    Pydantic schemas — the shared contract; must not import from any other layer
```

**Dependency rule:** `api → agent → {routing, data} → models`. Nothing depends upward. Code that mixes concerns across this boundary (e.g. a DB query inside `routing/`) is a sign it landed in the wrong module — see `CONTRIBUTION.md`.

### The routing graph

One `networkx.MultiDiGraph`, built once at FastAPI startup from whatever's in Postgres (`app/routing/build.py` + `app/data/repository.fetch_network_data`, wired in `app/agent/runtime.py:AgentRuntime.create`) and held as process-local state — not rebuilt per request. An empty DB produces a valid empty graph (no stops/routes yet, since field survey data hasn't landed), so this degrades rather than failing.

Edge types (`app/routing/edges.py`) — `walk`, `board`, `ride`, `alight`, `transfer`, `andong`, `becak` — each computes `time_s`/`fare_idr`/`transfers`/`walk_m` from a headway/distance model (no GTFS feed exists for TransJogja, so service is frequency-based, not timetabled — see `ARCHITECTURE.md` §7.1 for why plain Dijkstra is correct here). One graph, three weight functions (`app/routing/weights.py`): `tercepat` (time), `termurah` (fare), `termudah` (transfers + walk distance, tunable weights still unpicked — `ARCHITECTURE.md` §15.8).

`app/routing/build.py` connects route stops via board→ride→alight chains, and snaps stops/pangkalan onto the nearest OSMnx pedestrian walk node (`app/data/osm.py` fetches the walk network — `OsmnxWalkNetworkFetcher` hits the real Overpass API, `FakeWalkNetworkFetcher` is the test double, same `Protocol` pattern as `MapidClient`). Pangkalan also keep a direct-to-stop radius fallback for when no walk network has been ETL'd yet (`PANGKALAN_CONNECT_RADIUS_M`). Live Overpass calls are deliberately excluded from the automated test suite (external API, would make CI flaky) — verify `OsmnxWalkNetworkFetcher` manually before relying on it in a new environment.

### The agent

`app/agent/graph.py` is a hand-rolled LangGraph `plan → tools → respond` loop (not the prebuilt `ToolNode`, so tool results stay typed Pydantic objects instead of stringified content) with a per-turn tool-call round budget. The five tools (`app/agent/tools.py`) are exactly the ones named in the competition PRD — don't add a sixth without checking `ARCHITECTURE.md` §8.3 first — and are real callables wired to `routing/`/`data/` via injected dependencies (graph provider, coords provider, geocode resolver, DB session factory), not stubs.

`app/agent/llm.py` is a thin factory seam: **no LLM provider is chosen yet** (`ARCHITECTURE.md` §15.1, open on purpose). `get_llm()` raises `UnsupportedLLMProviderError` until `LLM_PROVIDER` is set, and `AgentRuntime` catches that and leaves `.graph = None` rather than crashing app startup — the `/ws` endpoint then replies with a structured `llm_unavailable` error instead of failing the connection. Wiring a real provider means adding one branch in `llm.py` plus its client dependency; nothing upstream should need to change.

### Two-channel WebSocket contract

`/ws` (`app/api/ws.py`) follows `ARCHITECTURE.md` §9.1 exactly: `user_message`/`viewport_changed` in, `token`/`ui_command`/`done`/`error` out. Prose and map-manipulation commands are never mixed in one message — `app/agent/ui_commands.py` derives a `UICommand` from a tool call's typed result, so the client never has to parse instructions out of chat text.

### REST + gateway concerns

`app/api/layers.py` serves `/api/layers` (a static catalogue grounded in what `data/schema.py` actually has tables for — `proposal_pathrix.md`/the PRD aren't in this repo, so it's not a literal transcription of an external doc), `/api/layers/{id}/features` (bbox query, 501 for layers with no repository query wired yet rather than a fake empty response), and `/api/isochrone/{stop_id}` (404 until something's been precomputed). `app/api/ratelimit.py` is a fixed-window Redis `INCR`/`EXPIRE` limiter applied as global middleware — it fails open on a Redis error (`ARCHITECTURE.md` §13: Redis down means slower/uncached, never a hard failure), so don't reintroduce a bare `await cache.incr(...)` without the `RedisError` guard around it.

### Data layer

`app/data/schema.py` mirrors `ARCHITECTURE.md` §5.1's DDL via SQLAlchemy + GeoAlchemy2. `app/data/mapid.py` normalizes MAPID's two different mission-API response shapes (`menugo`/`propertigo`/`struckgo` vs `activities`) into one `MissionPage` — the mission endpoint is spelled **`struckgo`**, not `strukgo`. `FakeMapidClient` in the same file is the fixture-backed double for offline dev/tests. Mission data is mirrored into Postgres on a schedule (`app/data/etl.py`), never proxied live (`ARCHITECTURE.md` §6.3).

### The frontend

`frontend/` is a transcription of the Claude Design canvas `Pathrix App.dc.html` (project `a632566d-7c80-48f4-a429-67aa8da1eba8`) onto the stack `PLAN.md` §3.2 already committed to: Vite + React 18 + TS + Tailwind 4 + Zustand + MapLibre GL JS. **The canvas is the visual source of truth** — colours, type ramp, snap points, shadows, and the SVG itinerary schematic are its values, re-transcribed rather than tuned locally, so design and build can't drift. Component names follow the `TEAM_WORKFLOW.md` §4 handoff convention (`AgentSheet`, `RouteCard`, `LayerToggleList`, `SustainabilityStat`, `BasemapSwitcher`).

`src/lib/bridge.ts` is the map ↔ agent bridge (`ARCHITECTURE.md` §10.2): a pure switch over the closed `UICommandAction` set. `toggle_layer` is store state and deliberately falls through to the Zustand store instead; the other three are imperative MapLibre calls. `src/lib/mapHandle.ts` holds the live map outside React, since a GL context is not renderable state.

`draw_route` draws real geometry: `RouteLeg.coordinates` carries the leg's `[lon, lat]` polyline, pinned onto graph nodes by `routing/build.py` and read back in `shortest_path.calculate_route`. The bridge builds the GeoJSON client-side and paints it in the design's grammar (halo casing, colour and weight by mode, walk dashed) — rendering stays a client concern. A leg with an unpinned endpoint yields an empty list rather than half a line, and the map simply shows nothing extra while no route is drawable — the canvas's authored route schematic (`RouteOverlay`) was removed because it drew a fixed diagonal line unrelated to the real basemap underneath it, not a genuine fallback.

Mission-derived layers (`poi`, `properti` — the two `/api/layers` ids the backend actually serves; `transit`/`pangkalan` still 501) render as real map markers, not just a toggle-list row: `MapCanvas` watches the Zustand `active` set, the current viewport, and `/api/layers`' `queryable` flags, and fetches `/api/layers/{id}/features` (debounced against `moveend`) for whichever are both toggled on and queryable, drawing them via `lib/missionLayers.ts` (`pathrix-mission-{id}` source/circle-layer, mirroring `bridge.ts`'s naming). A failed fetch is swallowed the same way `fetchLayers` is — a missing/slow mission layer must never break the map.

One contract gap remains, visible in the UI rather than papered over: with no LLM provider wired, `/ws` replies `llm_unavailable` and the store falls back to the canvas's scripted replies so every screen stays inspectable. All sample content lives in `src/lib/sample.ts`, in one place, labelled.

## Team workflow

Two-person team; see `TEAM_WORKFLOW.md` for the full split. This side of the repo (`agent/`, `api/`, `routing/`, `data/`, DevOps) is one person's lane — frontend, field survey/digitization, and routing *accuracy* tuning are the other person's. Own-lane changes: self-review, merge when green. Cross-review required for changes touching `models/` after the API contract freeze (~27 Aug 2026) or anything promised in the competition proposal/PRD. Conventional Commits (`<type>(<scope>): <summary>`, scopes: `agent`, `routing`, `data`, `api`, `frontend`, `etl`, `docs`).
