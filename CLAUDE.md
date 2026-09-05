# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

PATHRIX — a WebGIS AI agent for multimodal mobility navigation in Yogyakarta (TransJogja bus, KRL rail, YIA airport rail, plus andong/becak first/last-mile), built for the MAPID WebGIS Competition 2026. `docs/ARCHITECTURE.md` is the full system design; `docs/PLAN.md` has the build plan, schedule, and stack rationale. **When the docs and the code disagree, the code is right — update the relevant doc in the same change that invalidates it** (`docs/ARCHITECTURE.md` §16).

`backend/` (FastAPI + LangGraph + PostGIS) and `frontend/` (Vite + React + MapLibre) both have code. Frontend implementation is nominally the other person's lane (see Team workflow below) — don't extend it unless explicitly asked.

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
npm run preview  # the only way to exercise the service worker; it is off in dev
```

`npm run build` **fails without `VITE_MAPID_BASEMAP_KEY`** and that guard is deliberate: Vite inlines `import.meta.env` at build time, so a keyless build folds away the guard in `MapCanvas` and Rollup drops the whole MapLibre chunk — you'd ship a working-looking app with no map in it. There is no test suite here yet; `tsc` is the gate, and it covers more than types: `src/i18n/en.ts` is typed against `id.ts`, so a missing or misnamed translation key is a compile error rather than a string that renders as its own name.

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

`app/api/search.py` serves `GET /api/geocode?q=&limit=` — the search box behind
Home and Explore. It reuses `data/repository.search_places` (an `ILIKE` sweep
over `transit_stops`, `pangkalan`, `poi`, `properti`, transit-first) and
`GeocodeResolver.search`, which is Nominatim bounded to `YOGYA_VIEWBOX` because
answering "Malioboro" with a street in Surabaya is a wrong answer, not a broader
one. `app/api/layers.py` serves `/api/layers` (a static catalogue grounded in what `data/schema.py` actually has tables for — `proposal_pathrix.md`/the PRD aren't in this repo, so it's not a literal transcription of an external doc), `/api/layers/{id}/features` (bbox query, 501 for layers with no repository query wired yet rather than a fake empty response), and `/api/isochrone/{stop_id}` (404 until something's been precomputed). `app/api/ratelimit.py` is a fixed-window Redis `INCR`/`EXPIRE` limiter applied as global middleware — it fails open on a Redis error (`ARCHITECTURE.md` §13: Redis down means slower/uncached, never a hard failure), so don't reintroduce a bare `await cache.incr(...)` without the `RedisError` guard around it.

### Data layer

`app/data/schema.py` mirrors `ARCHITECTURE.md` §5.1's DDL via SQLAlchemy + GeoAlchemy2. `app/data/mapid.py` normalizes MAPID's two different mission-API response shapes (`menugo`/`propertigo`/`struckgo` vs `activities`) into one `MissionPage` — the mission endpoint is spelled **`struckgo`**, not `strukgo`. `FakeMapidClient` in the same file is the fixture-backed double for offline dev/tests. Mission data is mirrored into Postgres on a schedule (`app/data/etl.py`), never proxied live (`ARCHITECTURE.md` §6.3).

### The frontend

`frontend/` is a five-destination map app on the stack `PLAN.md` §3.2 committed
to: Vite + React 18 + TS + Tailwind 4 + Zustand + MapLibre GL JS, plus
`lucide-react` for iconography and a handful of Radix primitives vendored
shadcn-style into `src/components/ui/` (tabs, switch, avatar) with `cmdk` behind
the search palette. It began as a transcription of the Claude Design canvas
`Pathrix App.dc.html`; **that canvas is no longer the visual source of truth** —
`docs/DESIGN.md` is, and `src/styles/index.css` is its implementation.

**Surfaces:** `home` (greeting, search, quick actions, saved strip, recents),
`explore` (the map plus its floating chrome), `agent`, `saved`, `profile`, plus
a one-time location-permission screen and a place-detail sheet. One definition
list (`components/nav/tabs.ts`) drives both the mobile tab bar and the desktop
sidebar so they cannot drift.

**The layout switch is `components/AppShell.tsx` and there is only one.** Below
900px the active screen stacks over the map with a floating `TabBar`; at or
above it the nav promotes to `NavSidebar` (248px, collapsible to 76px) and the
screen to a 384px context panel beside a map that stays in frame. Both branches
render the same components — desktop is the mobile design promoted, not a second
product. The map mounts once (first Explore visit, or on idle when wide) and is
then only hidden, never unmounted: MapLibre stays out of the first paint per
`ARCHITECTURE.md` §14, but tearing down a GL context per tab switch costs far
more than keeping it.

**Colour:** `docs/DESIGN.md` is the visual source of truth and
`src/styles/index.css` is its implementation. White ground, frosted chrome over
the map, **near-black as the action colour** so every filled control is the same
ink the body text is set in, and one gold accent doing exactly one job per
screen. There is no blue in the chrome and no coloured button anywhere: a
saturated primary competes with route lines on the one screen where route lines
are the product.

The ground is white, so a card does not separate from the page by fill — the
hairline is the edge, which is why `--color-line` is heavier than a hairline
normally needs to be. The two inset steps are neutral rather than warm; against
pure white a warm tint reads as a stain rather than as a plane.

Every ink step is a measured composite, recorded with its ratio in
`styles/index.css` — `--color-ink-3` is the smallest step still AA for text and
`--color-ink-4` is non-text only. `lib/tokens.ts` mirrors what JS needs and must
move with the CSS. The **map category palette in `tokens.ts` is inherited
unchanged** and is the only place `instrument-blue` still appears: those hexes
were verified against MAPID's real `street-v2.0`/`dark-v2.0` paint, and
repainting the chrome did not change the basemap under a route line.

Archivo carries every label in sentence case; **IBM Plex Mono is reserved for
figures** (fares, durations, distances, coordinates, counts) and is loaded at
400/500 only, so a figure never goes above `font-medium`. No uppercase
tracked-out eyebrows above headings — that was most of what made the earlier
build read as an instrument panel rather than an app.

**Anything global belongs inside `@layer base`.** An unlayered rule outranks
every layered Tailwind utility, and this has now caused two separate bugs: an
unlayered `button { background: none }` silently turned each button-shaped
floating control transparent over the map, and an unlayered `:focus-visible`
rule stopped the search pill suppressing the second focus box its inner input
was drawing. Both live in `@layer base` now; put the next one there too.

**Photographs are real or absent.** `lib/photos.ts` resolves named Yogyakarta
landmarks against Wikipedia's REST summary endpoint (keyless, cached a week,
credited in the place sheet) via a hand-curated article map, because a fuzzy
title search always returns a photograph of *something*. Anything it cannot
honestly identify renders the drawn placeholder instead. Only a real answer is
cached: a 200 with no thumbnail counts, a 429 or a network failure does not.

**Persistence is localStorage only** (`store/persist.ts`, one `pathrix.v1` key):
profile, saved places, saved routes, recents, location permission, onboarding.
There is no auth and no user table, so the UI says "tersimpan di perangkat ini"
rather than implying an account. Every read tolerates a missing or corrupt value.

`src/lib/bridge.ts` is the map ↔ agent bridge (`ARCHITECTURE.md` §10.2): a pure
switch over the closed `UICommandAction` set. `toggle_layer` is store state and
deliberately falls through to Zustand; the other three are imperative MapLibre
calls. `src/lib/mapHandle.ts` holds the live map outside React, and
`src/lib/actions.ts` holds the gestures that touch both (go to a place, ask from
anywhere, recentre) so no component reaches for a GL context itself.

`draw_route` draws real geometry: `RouteLeg.coordinates` carries the leg's
`[lon, lat]` polyline, pinned onto graph nodes by `routing/build.py` and read
back in `shortest_path.calculate_route`. A leg with an unpinned endpoint yields
an empty list rather than half a line.

Mission-derived layers (`poi`, `properti` — the two `/api/layers` ids the backend
actually serves; `transit`/`pangkalan` still 501) render as real map markers:
`MapCanvas` watches the Zustand `active` set, the viewport, and the catalogue's
`queryable` flags, and fetches `/api/layers/{id}/features` (debounced against
`moveend`), drawing them via `lib/missionLayers.ts`. Tapping one opens the place
sheet. Filter chips and the layer panel write to the same `active` set — one
source of truth at two densities. A failed fetch is swallowed: a missing or slow
mission layer must never break the map.

Search is real: `GET /api/geocode` (`backend/app/api/search.py`) returns mirrored
halte/pangkalan/mission rows first, then Nominatim addresses biased to the
Yogyakarta viewbox, and a Nominatim failure degrades to DB-only results.

`components/search/SearchPanel.tsx` is the **only** search implementation, and it
is anchored rather than modal: the bar stays put, results drop beneath it, the
map never leaves, and nothing navigates until a result is chosen. Both Beranda
and the map chrome mount it, and only one is ever mounted at a time, so the
query is component-local; `searchOpen` is in the store because the filter chips
step aside for the panel. cmdk supplies the listbox behaviour — note that its
`label` prop drives the input's accessible name and overrides any `aria-label`
you add.

**Two device-local systems and one simulation** round out the frontend:

- `src/i18n/` is a typed catalogue with no dependency. `id.ts` defines the key
  set and `en.ts` is typed against it. Place names, `TransJogja`, `KRL`,
  `andong`, `becak`, `halte` and `pangkalan` are never translated in either
  catalogue; both files say so. `format.ts` and `lib/actions.ts` read the locale
  straight off the store, which is the pattern for module-level code.
- `src/lib/cache.ts` memoises API responses in memory with in-flight dedupe.
  Mission-feature keys snap the viewport outward and the request is issued at
  the snapped extent — key on a box you did not fetch and a later view will read
  data that does not reach its edges. A service worker (`vite-plugin-pwa`)
  precaches the shell and runtime-caches the basemap, fonts, photographs and
  avatars; `/api` is deliberately absent from it.
- `store/persist.ts` also holds `locale` and the profile picture. Avatars are a
  DiceBear URL or an uploaded photo downscaled to a 256px JPEG — the one write
  in the app that can realistically hit quota, so it reports failure instead of
  swallowing it.

One contract gap remains, visible in the UI rather than papered over: with no
LLM provider wired, `/ws` replies `llm_unavailable` and `lib/demoAgent.ts` walks
a script whose steps name what the real agent will actually do, so a provider
turns them into reported progress rather than lines a timer prints. The agent
header says "Mode contoh, agen belum terpasang" the entire time, **including
while the script runs** — do not let that banner disappear during streaming; it
is the whole reason the simulation is honest. All sample content lives in
`src/lib/sample.ts` and the `demo.*` catalogue keys, labelled.

## Team workflow

Two-person team; see `TEAM_WORKFLOW.md` for the full split. This side of the repo (`agent/`, `api/`, `routing/`, `data/`, DevOps) is one person's lane — frontend, field survey/digitization, and routing *accuracy* tuning are the other person's. Own-lane changes: self-review, merge when green. Cross-review required for changes touching `models/` after the API contract freeze (~27 Aug 2026) or anything promised in the competition proposal/PRD. Conventional Commits (`<type>(<scope>): <summary>`, scopes: `agent`, `routing`, `data`, `api`, `frontend`, `etl`, `docs`).
