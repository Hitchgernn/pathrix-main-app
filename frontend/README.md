# PATHRIX frontend

The WebGIS client: a full-bleed MAPID basemap with the agent in a bottom sheet.
Vite + React 18 + TypeScript + Tailwind CSS 4 + Zustand + MapLibre GL JS, per
`docs/PLAN.md` §3.2 and `docs/ARCHITECTURE.md` §10.

## Source of truth for the visual design

Every screen here is a transcription of the Claude Design canvas
`Pathrix App.dc.html` (project `a632566d-7c80-48f4-a429-67aa8da1eba8`). Colours,
type ramp, spacing, shadows, and snap points are the canvas's own values —
change the canvas and re-transcribe rather than tuning them here, so the design
and the build cannot drift apart. One exception: the canvas's SVG route
schematic (`RouteOverlay`) was deleted — it drew a fixed diagonal line with no
relationship to the real MAPID basemap underneath it, which reads as broken
rather than as a placeholder once the map actually renders.

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

## Drawing a route

`RouteLeg.coordinates` carries each leg's `[lon, lat]` polyline. `lib/bridge.ts`
turns the legs into a `FeatureCollection`, tags each with its visual mode family,
and paints three layers in the canvas's grammar: a halo casing under everything,
coloured strokes weighted by mode, and walk legs dashed and thin. Colour and
weight are MapLibre `match` expressions rather than a layer per mode.

Rendering is deliberately a client concern — the backend emits coordinates, not
styling. A leg whose endpoints are unpinned on the routing graph comes back with
an empty list, and the map just shows nothing extra rather than a half-drawn
line or a fake placeholder. `setStyle` discards everything the bridge added, so
`MapCanvas` re-applies the drawn route on `styledata` in the incoming palette.

## Mission layers

`poi` and `properti` — the two `/api/layers` ids the backend actually serves a
`GET /api/layers/{id}/features` for (`transit`/`pangkalan` are still a 501) —
render as real markers on the map, fetched live rather than baked into the
toggle list. `MapCanvas` watches the Zustand `active` set, the current
viewport, and the fetched catalogue's `queryable` flags; whenever a queryable
layer is toggled on, it debounces (400ms, against the `moveend` flood) a call
to `lib/api.ts::fetchLayerFeatures(layerId, bbox)` and hands the result to
`lib/missionLayers.ts::syncMissionLayer`, which adds/updates a
`pathrix-mission-{id}` GeoJSON source and a matching `-circle` layer — the same
naming convention `lib/bridge.ts` uses for the route and highlight layers.
Toggling off removes the source/layer immediately; a basemap `setStyle` wipes
and `reapplyMissionLayers` redraws every currently-on layer from its own small
cache, same pattern as the route's `reapplyRoute`. A failed or empty fetch is
swallowed — a missing mission layer degrades to "nothing drawn," never an error.

## Where the design and the live backend still differ

**No LLM provider is wired** (`ARCHITECTURE.md` §15.1). `/ws` answers
`llm_unavailable`, and the store falls back to the canvas's scripted replies so
every screen stays inspectable. Live replies take over the moment a provider is
configured; nothing here needs to change.

Field survey data has not landed either, so the ETL that would populate `poi`/
`properti` hasn't run — mission layers are wired end-to-end but will render
empty until it does. Layer counts, the POI card, and the carbon figures still
render the canvas's sample content for the same reason. `lib/sample.ts` holds
all of it in one place, clearly labelled.
