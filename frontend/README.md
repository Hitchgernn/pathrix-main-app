# PATHRIX frontend

The WebGIS client: a full-bleed MAPID basemap with the agent in a bottom sheet.
Vite + React 18 + TypeScript + Tailwind CSS 4 + Zustand + MapLibre GL JS, per
`docs/PLAN.md` §3.2 and `docs/ARCHITECTURE.md` §10.

## Source of truth for the visual design

Every screen here is a transcription of the Claude Design canvas
`Pathrix App.dc.html` (project `a632566d-7c80-48f4-a429-67aa8da1eba8`). Colours,
type ramp, spacing, shadows, snap points, and the SVG route schematic are the
canvas's own values — change the canvas and re-transcribe rather than tuning
them here, so the design and the build cannot drift apart.

Component names match the handoff convention in `TEAM_WORKFLOW.md` §4:
`AgentSheet`, `RouteCard`, `RouteDetail`, `LayerToggleList`,
`SustainabilityStat`, `BasemapSwitcher`, `RecenterFab`.

## Commands

```sh
npm install
npm run dev      # dev server on :5173, proxying /api and /ws to :8000
npm run lint     # tsc --noEmit
npm run build    # typecheck + production build
```

Run the backend alongside it:

```sh
cd ../backend && uv run uvicorn app.main:app --reload
```

## Environment

Copy `.env.example` to `.env`. `VITE_MAPID_BASEMAP_KEY` is **required for
`npm run build`** — Vite inlines `import.meta.env` at build time, so a build
made without it would fold away the guard in `MapCanvas` and drop MapLibre from
the bundle entirely. `vite.config.ts` fails the build rather than let that ship.

The basemap key necessarily reaches the browser (MapLibre fetches the style URL
directly). The mission key is server-only and must never appear here —
`ARCHITECTURE.md` §13.2.

## Where the design and the live backend still differ

Both are real gaps, not shortcuts, and both are visible in the UI rather than
papered over:

- **`draw_route` carries no geometry.** The backend's `draw_route` payload is a
  `Route` (`models/routing.py`): legs have node ids and costs, not coordinates.
  `lib/bridge.ts` draws a line when the payload has a `geometry` field and
  otherwise leaves the map alone. The schematic in `RouteOverlay` is the
  canvas's authored itinerary, not live geometry.
- **No LLM provider is wired** (`ARCHITECTURE.md` §15.1). `/ws` answers
  `llm_unavailable`, and the store falls back to the canvas's scripted replies
  so every screen stays inspectable. Live replies take over the moment a
  provider is configured; nothing here needs to change.

Field survey data has not landed either, so layer counts, the POI card, and the
carbon figures render the canvas's sample content. `lib/sample.ts` holds all of
it in one place, clearly labelled.
