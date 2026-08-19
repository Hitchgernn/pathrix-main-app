# PATHRIX — Claude Design canvas prompt

Paste this together with `docs/DESIGN.md` in the same Claude Design session.

---

Design the app screens for **PATHRIX** — working name for this surface is "The Instrument, Live." It's a WebGIS AI agent for multimodal mobility in Yogyakarta (TransJogja bus, KRL rail, YIA airport rail, plus andong/becak first/last-mile). I'm pasting `DESIGN.md` alongside this prompt — treat it as the **binding design system**, not a starting point to riff on. Colors, type scale, the surface elevation ramp, the map category palette, and the shadow vocabulary are all already finalized with documented rationale (including verified WCAG contrast against the real MAPID basemap tiles). Reuse them exactly; don't invent new ones.

## Screens to produce

1. **Dashboard** — the entry point. Loads *before* the complex map, so a first-time visitor doesn't land in a layer-dense interface. Simple, calm, gets the user into the map.
2. **Map + Agent** — the core screen. Full-bleed map as the base layer, `AgentSheet` (bottom sheet, three snap points: peek/half/full) for the AI agent, and a second independent sheet for layer controls (`LayerToggleList`). The two sheets never occupy the same snap-point space — opening one at "full" collapses the other to "peek."
3. **Route detail** — a staged itinerary: walk → halte → transit → andong/becak → destination, shown as a vertical timeline (`RouteCard` / Itinerary Timeline component). Mode-coded per leg.
4. **Sustainability** — carbon saved (`SustainabilityStat`), with the calculation basis and source citation visible directly beneath the figure, never omitted.

## Layout rules

- Mobile-first. No fixed shell width — full-viewport, map-first, not a centered content column.
- **The map is always the base layer.** Every other surface (agent sheet, layer sheet, route detail) stacks above it as a sheet or overlay — never a full-screen replacement of it. Navigating to "route detail" pushes a sheet higher; it doesn't navigate away from the map.
- Bottom sheets rise from the screen edge, `surface-1` background, sheet-lift shadow, top-rounded corners only.
- **Breakpoint: 900px.** Below it, agent and layer panels are bottom sheets. At or above it, both promote to a left rail — same component tree, just repositioned, not rebuilt.

## Component naming

Name canvas layers exactly like this — these names carry through the handoff to the frontend build:

- `AgentSheet`
- `RouteCard` (Itinerary Timeline)
- `LayerToggleList`
- `SustainabilityStat`
- `BasemapSwitcher`
- Map floating action button (locate-me / recenter)

## Do / Don't (carried from `DESIGN.md`)

- **Don't** use a bordered-card dashboard aesthetic — hairline separators, not cards with shadows, for flat content inside a sheet.
- **Don't** add a spinner, skeleton shimmer, or animated loading icon anywhere — state pending/absent status in mono `LABEL` text instead (e.g. `THINKING…`).
- **Don't** invent an icon system — mode indicators are colored verticals from the map category palette, not icons.
- **Don't** give agent chat messages a filled bubble background — only the user's own messages get a fill; the agent speaks directly on the sheet surface.
- **Do** keep IBM Plex Mono reserved for metadata only (labels, mode tags, index numbers) — never chat body text or descriptions.
- **Do** treat gold (`tugu-gold*`) as the one warm accent, used only where `DESIGN.md` already specifies (sustainability figures, andong/becak markers) — never as general decoration.

## Basemap contrast check

Wherever UI sits directly over the map (markers, route lines, the basemap switcher, the floating action button), verify contrast against **both** `street-v2.0` and `dark-v2.0` basemap styles before finalizing — a value that reads on one can disappear on the other. `DESIGN.md`'s map category palette already did this verification; carry the same discipline through to any new map-adjacent chrome.
