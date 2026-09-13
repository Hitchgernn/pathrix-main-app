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

**Tests own their own database, `pathrix_test`** (`TEST_DATABASE_URL`, created on demand by `tests/conftest.py` and overridable by env var). The `db_session` fixture `TRUNCATE`s every table it touches, so sharing a database with the running app means a `pytest` run silently wipes whatever was last ETL'd in — it did exactly that once. `tests/api/conftest.py` therefore also overrides the app's `get_session` dependency, because `main.lifespan` otherwise builds its engine from `settings.database_url` and an API test would read a different Postgres than it seeded.

CI (`.github/workflows/backend-ci.yml`) runs `ruff check` + `pytest` with `postgis/postgis` and `redis:7-alpine` service containers on every push/PR touching `backend/` — both are required, since the rate-limit middleware and several fixtures hit Redis with no skip-if-unreachable path (unlike the DB-dependent tests).

Filling a fresh database is `app/data/ingest.py`: `uv run python -m app.data.ingest layers` lists a MAPID project's survey layers, `... stops` mirrors one into `transit_stops`, `... missions` mirrors the four mission datasets into `poi`/`properti`, and `... survey` files halte/becak/andong out of the `activities` feed into `transit_stops`/`pangkalan` (`ARCHITECTURE.md` §6.3 — that feed carries directional A/B halte, regional stops, and the only andong/becak data the project has). **`activities` answers at most 60 posts, newest first, ignores `offset`, and never says it truncated**, so it is harvested by quartering the study area until each tile comes back under the cap (`fetch_activities_in_full`, depth 8, ~77 requests, 963 posts for DIY). Both ETL entry points return the number of tiles still at the cap and `ingest` prints it — never let that signal be dropped, since silent truncation is exactly the bug the tiling exists to fix. **The two MAPID credentials are not interchangeable** — `MAPID_MISSION_API_KEY` is a 24-char ObjectId, `MAPID_GEOSERVER_API_KEY` a 32-char hex string, and each host answers a wrong key with a bare 500/404 that looks like an outage rather than an auth failure (`ARCHITECTURE.md` §6.2).

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

`app/data/mapid_routing.py` is a thin factory seam for road-leg display
geometry — **no provider is wired yet** (`docs/CLAUDE_TRANSIT_HANDOFF.md`,
Phase 0, open on purpose): it holds the `MapidRoutingClient` protocol, the
`RoadLegResult` typed result, and `FakeMapidRoutingClient` (the test double),
but deliberately no `HttpMapidRoutingClient` — that needs a real base URL,
auth method, and request/response contract from the MAPID owner first (a
separate product from the basemap/mission/geoserver keys), never guessed.
`MAPID_ROUTING_ENABLED` defaults to `false`, leaving today's local-OSM-only
road geometry (`app/data/transport_geometry.py`) unchanged. Wiring a real
provider means adding one client class here plus its settings; nothing in
`routing/`/`agent/` should need to change.

### The agent

`app/agent/graph.py` is a hand-rolled LangGraph `plan → tools → respond` loop (not the prebuilt `ToolNode`, so tool results stay typed Pydantic objects instead of stringified content) with a per-turn tool-call round budget. The five tools (`app/agent/tools.py`) are exactly the ones named in the competition PRD — don't add a sixth without checking `ARCHITECTURE.md` §8.3 first — and are real callables wired to `routing/`/`data/` via injected dependencies (graph provider, coords provider, geocode resolver, DB session factory), not stubs.

`app/agent/demo_route.py` swaps `calculate_route` for a hand-authored `Route` fixture when `settings.demo_mock_route` is set (`DEMO_MOCK_ROUTE` env var, default off) — real bus topology (`route_stops`) is empty across the whole dataset today, so this exists purely to have something to show in a recording; the LLM still plans/narrates/calls tools normally, only this one tool's data is pre-authored. Never enable it outside recording a demo.

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

`app/data/schema.py` mirrors `ARCHITECTURE.md` §5.1's DDL via SQLAlchemy + GeoAlchemy2. `app/data/mapid.py` normalizes MAPID's two different mission-API response shapes (`menugo`/`propertigo`/`struckgo` vs `activities`) into one `MissionPage` — the mission endpoint is spelled **`struckgo`**, not `strukgo`. The same client also reads MAPID's *other* API, `geoserver.mapid.io` (`fetch_layer` / `fetch_layer_list`, `ARCHITECTURE.md` §6.6): a project's uploaded **survey** layers — ours, another team's, or a previous competition period's — returned whole with no pagination and with the feature id spelled `id` rather than `_id`. `app/data/ingest.py` is the CLI over both: `ingest layers` lists what a project holds, `ingest stops --layer-id ...` mirrors a point layer into `transit_stops`. That is where the 73 Kota Yogyakarta halte come from; the mapping derives `operator` from the name (the layer has no operator column) and keeps every upstream attribute in `transit_stops.raw`. **Pick the layer deliberately** — the project carries a 2024 and a 2025 edition of the same 73 shelters with no feature id in common, so ingesting both doubles them; `source` is stamped `mapid_geoserver:{layer_id}` so which edition landed stays answerable. Stops only: `transit_routes`/`route_stops` still await the field survey, so this fills the map and the search box without making the graph routable. `FakeMapidClient` in the same file is the fixture-backed double for offline dev/tests. Mission data is mirrored into Postgres on a schedule (`app/data/etl.py`), never proxied live (`ARCHITECTURE.md` §6.3).

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

**Dark is a token swap and nothing more.** `--color-ink` is both the text colour
and the primary fill, so flipping ink light and surface dark turns every
`bg-ink text-surface` button into a light button with dark text; no component
knows a theme exists, and none should learn. `--color-ink-4` is held at the same
non-text contract in both themes even though dark has room to spare, so a
component legal in one is legal in the other. **Appearance also drives the
basemap** — light chrome over a dark map is a bug, not a preference — and
`data-theme` is stamped pre-paint by a script in `index.html` reading the same
`pathrix.v1` key, so there is no flash and no media query competing with the
store.

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

**The Bakpia mascot sprites are the only bundled images.**
`src/assets/bakpia-mascot.png` (116×160, five clips of a 29×32 sprite) and
`bakpia-earth.png` (136×184, four clips of a 34×46 mascot-on-a-globe) are the
only files in `src/assets/` and the only images the app ships rather than
fetches — everything else is remote (Wikipedia, DiceBear). Both sit under Vite's
4KB inline threshold, so they land in the JS bundle as data URIs rather than as
emitted assets; `png` is nonetheless in the VitePWA `globPatterns` so a redraw
that crosses that line does not silently fall out of the precache.
`tools/mascot/extract.py` regenerates both from the delivered contact sheets,
whose cell geometry is not recoverable by eye and is therefore pinned and
asserted per sheet in that script — including that the downscale is lossless and
that the white key is found by reach from the frame edge, so the highlights
*inside* the Earth are not punched out with the background.

`components/Sprite.tsx` plays either sheet as a CSS `steps()` walk over a
background image — no canvas, no rAF, nothing running per frame — and is the
only thing that knows the mechanics. `MascotThinking` uses it beside the agent's
streaming status (beside, never instead of, the words) and `PermissionScreen`'s
`EarthMark` uses it in place of the drawn pin that screen used to open with.
`docs/DESIGN.md` §Mascot is the rule; the ban there on animated loading chrome
still stands for everything else.

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

A tapped marker's sheet renders **whatever the row actually carries**, and for
an activity-derived halte or becak stand that is a real survey record: the
surveyor's prose (shelter type, roof, ramp, guiding block, pavement), every
photograph the post carried, the surveyor, their community, and the date.
`Place.description`/`.survey`/`.photos` are optional so places persisted before
those fields existed still load (`store/persist.ts` validates only `id`). The
gold pill names whose survey it was — community where `survey.community` is
set, ours only otherwise — because the andong/becak stands now arrive from the
MAPID activity feed rather than from our own field survey. The same sheet opens from **search**: `PlaceHit.raw`
carries a mirrored row's attributes verbatim (null for a Nominatim address), so
`placeFromHit` and `placeFromFeature` build the same `Place` and share one
`factsOf` — a place found by typing cannot read thinner than the same place
tapped on the map. A row the survey pass filed into `transit_stops`/`pangkalan`
is **excluded from `poi`** in both `search_places` and
`query_features_in_viewport` (`_not_filed_as_infrastructure`), since the
original activity row stays in `poi` as the record of the post and would
otherwise be a second result and a second marker at one coordinate — under
"Pariwisata & Sosial Budaya", which is not what a halte is.

`draw_route` draws real geometry: `RouteLeg.coordinates` carries the leg's
`[lon, lat]` polyline, pinned onto graph nodes by `routing/build.py` and read
back in `shortest_path.calculate_route`. A leg with an unpinned endpoint yields
an empty list rather than half a line.

**3D view is a tilted camera plus extruded buildings, and nothing more.**
`lib/buildings3d.ts` adds one `fill-extrusion` layer per vector source off the
basemap's `building` source-layer and its real `render_height`, anchored above
the last road layer so rooftops sit under the type. It hides MAPID's own
`building-3d` layers, which live in `street-v2.0` only and ramp to royalblue —
one layer in both themes, neutral, so 3D is not a different feature per
appearance. There is **no terrain**: no MAPID style ships a `raster-dem`
(`ARCHITECTURE.md` §6.1), so `setTerrain` and a sky layer are both off the
table. `store.view3d` is the switch, deliberately session-only and separate from
`basemap` (which `applyTheme` derives from the theme); the `styledata` handler in
`MapCanvas` is what keeps the buildings alive across a `setStyle`, and it runs
before the route and mission layers so those draw above them. Rotate and pitch
gestures are disabled in 2D and enabled in 3D, so the toggle is the only door to
a tilted camera.

Mission-derived layers (`poi`, `properti`, `transit` and `pangkalan` — every
`/api/layers` id the backend serves; `jangkauan`/`bangunan` are client-side and
have no repository query) render as real map markers:
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
