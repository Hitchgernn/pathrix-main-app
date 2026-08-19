# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

PATHRIX — a WebGIS AI agent for multimodal mobility navigation in Yogyakarta (TransJogja bus, KRL rail, YIA airport rail, plus andong/becak first/last-mile), built for the MAPID WebGIS Competition 2026. `docs/ARCHITECTURE.md` is the full system design; `docs/PLAN.md` has the build plan, schedule, and stack rationale. **When the docs and the code disagree, the code is right — update the relevant doc in the same change that invalidates it** (`docs/ARCHITECTURE.md` §16).

`backend/` (FastAPI + LangGraph + PostGIS) is the only part of this repo with code so far. `frontend/` does not exist yet and is out of scope for this side of the team (see Team workflow below) — do not build it unless explicitly asked.

## Commands

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

CI (`.github/workflows/backend-ci.yml`) runs `ruff check` + `pytest` with a `postgis/postgis` service container on every push/PR touching `backend/`.

No LLM provider is configured by default (`LLM_PROVIDER` unset) — this is deliberate (see Agent below), not a setup step you're missing.

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

`app/routing/build.py` connects route stops via board→ride→alight chains and pangkalan (andong/becak) to any stop within a fixed radius — there's no pedestrian (OSMnx) walk-node network wired in yet, that's a separate unstarted task.

### The agent

`app/agent/graph.py` is a hand-rolled LangGraph `plan → tools → respond` loop (not the prebuilt `ToolNode`, so tool results stay typed Pydantic objects instead of stringified content) with a per-turn tool-call round budget. The five tools (`app/agent/tools.py`) are exactly the ones named in the competition PRD — don't add a sixth without checking `ARCHITECTURE.md` §8.3 first — and are real callables wired to `routing/`/`data/` via injected dependencies (graph provider, coords provider, geocode resolver, DB session factory), not stubs.

`app/agent/llm.py` is a thin factory seam: **no LLM provider is chosen yet** (`ARCHITECTURE.md` §15.1, open on purpose). `get_llm()` raises `UnsupportedLLMProviderError` until `LLM_PROVIDER` is set, and `AgentRuntime` catches that and leaves `.graph = None` rather than crashing app startup — the `/ws` endpoint then replies with a structured `llm_unavailable` error instead of failing the connection. Wiring a real provider means adding one branch in `llm.py` plus its client dependency; nothing upstream should need to change.

### Two-channel WebSocket contract

`/ws` (`app/api/ws.py`) follows `ARCHITECTURE.md` §9.1 exactly: `user_message`/`viewport_changed` in, `token`/`ui_command`/`done`/`error` out. Prose and map-manipulation commands are never mixed in one message — `app/agent/ui_commands.py` derives a `UICommand` from a tool call's typed result, so the client never has to parse instructions out of chat text.

### Data layer

`app/data/schema.py` mirrors `ARCHITECTURE.md` §5.1's DDL via SQLAlchemy + GeoAlchemy2. `app/data/mapid.py` normalizes MAPID's two different mission-API response shapes (`menugo`/`propertigo`/`struckgo` vs `activities`) into one `MissionPage` — the mission endpoint is spelled **`struckgo`**, not `strukgo`. `FakeMapidClient` in the same file is the fixture-backed double for offline dev/tests. Mission data is mirrored into Postgres on a schedule (`app/data/etl.py`), never proxied live (`ARCHITECTURE.md` §6.3).

## Team workflow

Two-person team; see `TEAM_WORKFLOW.md` for the full split. This side of the repo (`agent/`, `api/`, `routing/`, `data/`, DevOps) is one person's lane — frontend, field survey/digitization, and routing *accuracy* tuning are the other person's. Own-lane changes: self-review, merge when green. Cross-review required for changes touching `models/` after the API contract freeze (~27 Aug 2026) or anything promised in the competition proposal/PRD. Conventional Commits (`<type>(<scope>): <summary>`, scopes: `agent`, `routing`, `data`, `api`, `frontend`, `etl`, `docs`).
