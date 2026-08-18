# Contributing to PATHRIX

**Status:** 🚧 provisional, same as `ARCHITECTURE.md` — this describes
`pathrix-app`, which does not exist as a repo yet. Update this file the moment
tooling or structure diverges from what's written here.

Two contributors. See `TEAM_WORKFLOW.md` for who owns what and how we
coordinate — this file is the mechanical layer underneath: branches, commits,
review, and per-language conventions.

---

## Repository layout

```
backend/
  app/
    api/        HTTP routes, WebSocket endpoint, dependency wiring
    agent/      LangGraph graph, tool definitions, prompts, LLM adapter
    routing/    graph construction, Dijkstra variants, isochrones, TSP
    data/       MAPID adapter, PostGIS repositories, ETL entrypoints
    models/     Pydantic schemas — the API contract (ARCHITECTURE.md §3.1)
  tests/
frontend/
  src/
    components/ map, agent sheet, layer panel, itinerary
    lib/        websocket client, map ↔ agent bridge (ARCHITECTURE.md §10.2)
    styles/     Tailwind theme (tokens copied from the landing page)
data/
  digitization/ TransJogja / KRL route digitization notebooks
  survey/       MAPID Apps survey exports and QC scripts
  fixtures/     sample payloads for offline development
```

Full detail: `ARCHITECTURE.md` §3–§10.

**The dependency rule** (`ARCHITECTURE.md` §3.1): `api → agent → {routing, data}
→ models`. Nothing depends upward. `routing/` in particular must import and test
with no network and no LLM — if a routing test needs a mock HTTP client, that's
a sign the code drifted into the wrong module.

---

## Setup

```sh
git clone <repo>
cd pathrix-app

# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # fill in MAPID_BASEMAP_KEY, MAPID_MISSION_API_KEY, etc.
docker compose up -d db cache
uvicorn app.main:app --reload

# frontend
cd frontend
npm install
npm run dev
```

Both `MAPID_BASEMAP_KEY` and `MAPID_MISSION_API_KEY` are required for full
functionality but the app should still run without them — see
`ARCHITECTURE.md` §13 (failure modes). If it doesn't degrade gracefully when a
key is missing, that's a bug against §2.5's design principle, not expected
behavior.

---

## Branches

```
main                        always deployable
feat/<short-description>    new work
fix/<short-description>     bug fix
docs/<short-description>    docs-only
```

No `develop` branch, no long-lived feature branches. Two people and 26 days
means branches should live hours to a few days, not weeks — a branch that
outlives the day it was cut is a merge conflict waiting to happen.

---

## Commits

**Conventional Commits**, matching the convention already used in
`pathrix-landingpage`:

```
<type>(<scope>): <summary>

type  = feat | fix | docs | test | refactor | chore
scope = the module touched: agent, routing, data, api, frontend, etl, docs
```

Examples:

```
feat(routing): add termudah weight function
fix(agent): clamp viewport bbox before get_data_in_viewport
docs(architecture): mark §6.2 VERIFIED after real mission key test
test(routing): synthetic graph shortest-path fixtures
```

Keep the summary under ~70 characters. Body only when the *why* isn't obvious
from the diff — same rule the landing page repo already follows.

**Commit as you go, not in one block at the end of the day.** Small commits are
what make the async daily check-in (`TEAM_WORKFLOW.md` §3) legible without a
meeting — the other person can read `git log` and know what happened.

---

## Pull requests

Own-lane changes (`TEAM_WORKFLOW.md` §0): self-review, merge when green. A
two-person team waiting on cross-review for every commit inside your own domain
is process cost with no safety benefit at this scale.

**Requires the other person's look before merge:**

- Anything touching `models/` after the API contract freezes (`TEAM_WORKFLOW.md` §2)
- Anything changing what's promised in `proposal_pathrix.md` or the final PRD
- Anything touching the other person's lane

PR description only needs: what changed, why (if not obvious), and which
`ARCHITECTURE.md` section it moves the confidence tag on, if any
(`ARCHITECTURE.md` §16).

---

## Code conventions

### Python (`backend/`)

- Type hints everywhere; Pydantic models are the contract, not just validation —
  see `ARCHITECTURE.md` §8.3 for why tool return types matter (they're what
  keeps the agent from inventing numbers).
- `routing/` stays a pure library: no `import fastapi`, no `import httpx`. If it
  needs the network, it belongs in `data/`.
- Format/lint: `ruff format` + `ruff check` before commit. Wire as a pre-commit
  hook once the repo exists — don't rely on remembering.
- Tests live next to what they test in `tests/`, mirroring the `app/` layout.

### TypeScript (`frontend/`)

- Strict mode on. No `any` without a comment saying why.
- `lib/bridge.ts` (`ARCHITECTURE.md` §10.2) is the only place that translates a
  `ui_command` into a MapLibre call. Don't reach into MapLibre state from a
  component — go through the bridge, or the two-way-binding problem
  `ARCHITECTURE.md` §10.1 warns about creeps back in.
- Zustand slices stay flat and serializable — no class instances, no functions
  in state.

### Both

- No secrets in code, ever, including test fixtures. `MAPID_MISSION_API_KEY`
  especially — see `ARCHITECTURE.md` §11.1 on why the two MAPID keys have
  different exposure rules.
- If you're about to add a comment explaining *what* the code does, rename
  something instead. Comments earn their place only for the non-obvious *why*.

---

## Testing expectations

From `ARCHITECTURE.md` §14 — repeated here because it's the part most likely to
get skipped under schedule pressure:

- `routing/` changes: unit test against a synthetic graph with a known shortest
  path. No network, no LLM, no database.
- `agent/` changes touching a tool or a prompt: run against the intent-precision
  fixture set (`ARCHITECTURE.md` §14) before merging, not after. It's the
  ≥ 80% metric — a regression caught after merge is a regression that shipped.
- `data/` changes: test against `FakeMapidClient`, not the live API, unless
  specifically verifying the real contract.

---

## When you touch `ARCHITECTURE.md` or `PLAN.md`

These documents are load-bearing for the other person's work, not internal
notes. If your change:

- **Resolves an open question** in `ARCHITECTURE.md` §15 — update the table and
  move the section's confidence tag (§16).
- **Changes a contract** other code depends on — update the doc in the *same*
  commit, not a follow-up.
- **Just implements something already `[DESIGNED]`** — no doc change needed
  unless reality diverged from the design.

---

## Questions

If something in this file, `TEAM_WORKFLOW.md`, or `ARCHITECTURE.md` is wrong or
missing, fix the document — don't work around it silently and leave the other
person to find out later.
