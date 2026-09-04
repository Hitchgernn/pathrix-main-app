# PATHRIX

A WebGIS AI agent for multimodal mobility in Yogyakarta. Ask it where you want to
go, in plain Indonesian or English, and it plans a door-to-door trip across
TransJogja buses, KRL commuter rail, the YIA airport line, and the andong and
becak that cover the first and last mile.

Built for the MAPID WebGIS Competition 2026.

<!-- Screens: mobile Beranda, the map with a place open, and the desktop shell. -->

---

## Why it exists

Yogyakarta's public transport is genuinely usable, and almost nobody outside the
city can work out how. Trip planners either do not know TransJogja exists or
model it as if it ran to a timetable it does not have, and none of them will
route you through a becak.

The interesting part is not the map. It is that **the agent orchestrates and
never computes**: it decides which tool to call, and a real routing engine
answers with real numbers. An LLM that invents a fare is worse than no answer,
so it is never in a position to.

---

## What is actually built

| Area | State |
|---|---|
| Routing engine | Working. One graph, three objectives, real geometry out. |
| Agent tool surface | Working. Five tools, typed results, wired to the engine. |
| LLM provider | **Not chosen.** Deliberately open, see below. |
| Map, search, place detail | Working, against live data. |
| Transit and survey data | Schema and ETL ready; the field survey has not landed. |

**No LLM provider is configured, on purpose** (`ARCHITECTURE.md` §15.1). `/ws`
answers a structured `llm_unavailable`, and the client falls back to a scripted
agent that walks the steps a real answer would take. The sheet says
"mode contoh" the whole time it does this. Wiring a provider is one branch in
`app/agent/llm.py`; nothing upstream should need to change.

The same honesty rule runs through the product. Carbon figures always carry
their source. A layer the backend cannot serve yet says so rather than
rendering empty. Place photographs are real and credited, or absent.

---

## Running it

```sh
docker compose up -d db cache          # PostGIS + Redis

cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload   # :8000

cd ../frontend
cp .env.example .env                   # set VITE_MAPID_BASEMAP_KEY
npm install
npm run dev                            # :5173, proxies /api and /ws
```

`npm run build` **fails without `VITE_MAPID_BASEMAP_KEY`**, and that guard is
deliberate: Vite inlines `import.meta.env` at build time, so a keyless build
folds away the guard in `MapCanvas` and Rollup drops the whole MapLibre chunk.
You would ship a working-looking app with no map in it.

### Tests

```sh
cd backend
uv run pytest -q                       # 72 tests
uv run ruff check . && uv run ruff format app tests

cd ../frontend
npx tsc -b --noEmit                    # the gate; there is no test suite yet
```

Most backend tests need Postgres and Redis and will `skip` rather than fail if
they are unreachable. `routing/` is pure and always runs.

---

## Architecture in one screen

```
backend/app/
  api/       HTTP + WebSocket surface, no business logic
  agent/     LangGraph plan -> tools -> respond; never computes a number
  routing/   graph build, Dijkstra variants, isochrones (pure, no I/O)
  data/      PostGIS repositories, MAPID adapter, geocoding, ETL
  models/    Pydantic schemas, the shared contract
```

**Dependency rule:** `api → agent → {routing, data} → models`. Nothing depends
upward. A DB query inside `routing/` means the code landed in the wrong module.

Two decisions worth knowing before reading further:

- **Prose and map commands travel on separate channels.** `/ws` sends `token`
  for language and `ui_command` for map manipulation, never mixed, so the client
  never parses instructions out of chat text.
- **Time-independent routing.** No GTFS feed exists for TransJogja, so service
  is modelled by headway rather than timetable, which makes plain Dijkstra
  correct here instead of a time-expanded graph.

The frontend is five destinations behind one layout switch: below 900px a
floating tab bar over the map, above it a sidebar and a context panel beside a
map that stays in frame. Same components either way. State is Zustand; anything
that outlives the tab is in one `localStorage` key. There is no auth and no user
table, so the UI says "kept on this device" rather than implying an account.

---

## Documentation

| File | What it owns |
|---|---|
| `docs/ARCHITECTURE.md` | The full system design, and the authority on contracts |
| `docs/DESIGN.md` | The visual system, and the source of truth for it |
| `docs/PLAN.md` | Build plan, schedule, stack rationale |
| `CLAUDE.md` | Orientation for agents working in this repo |
| `CONTRIBUTION.md` | Module boundaries and review expectations |
| `TEAM_WORKFLOW.md` | Who owns which lane |

**When the docs and the code disagree, the code is right** — update the doc in
the same change that invalidated it (`ARCHITECTURE.md` §16).

---

## Data and credits

- **MAPID** — basemaps, mission data (Menu Go, Properti Go, Struk Go,
  Activities), and Nominatim geocoding.
- **OpenStreetMap** contributors — the pedestrian network, via OSMnx.
- **Wikimedia Commons** — place photographs, credited in the app where shown.
- **KLHK (2023)** and **IPCC 2006 Tier 1** — emission factors.
- Andong and becak stands come from field survey, not from any public dataset.

Mission data is mirrored into Postgres on a schedule and never proxied live.
