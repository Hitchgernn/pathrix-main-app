---
name: Pathrix App
description: Design system for the WebGIS AI Agent — dashboard, map, and agent UI (extends the marketing-site system, not a replacement for it)
colors:
  instrument-blue: "#1f6592"
  instrument-blue-lift: "#5aa9dd"
  tugu-gold: "#d9a521"
  tugu-gold-lit: "#f2c94c"
  tugu-gold-deep: "#7c5e13"
  sky-pale: "#eff5fa"
  sky: "#dfeaf3"
  sky-deep: "#c6d9e8"
  ink: "#101e2a"
  ink-deep: "#0c1822"
  ink-soft: "#17293a"
  paper: "#e7f0f7"
typography:
  headline:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "clamp(20px, 2.4vw, 28px)"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  bodySmall:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1.5
    letterSpacing: "0.16em"
rounded:
  control: "999px"
  panel: "16px"
  sheet: "20px 20px 0 0"
  focus-ring: "3px"
spacing:
  gutter: "16px"
  sheet-pad: "20px"
  list-gap: "1px"

# Design System: Pathrix App

**Status:** 🚧 provisional — same standing as `ARCHITECTURE.md`/`PLAN.md`. Nothing
below has been through the Claude Design canvas yet; treat this as the brief
that canvas works from, not a finished spec. Update it once real screens exist.

## Relationship to the marketing site's `DESIGN.md`

This is not a new brand — it's the same brand under load. The landing page's
`DESIGN.md` (`pathrix-landingpage/DESIGN.md`) is the source of truth for color,
type family, and the instrument philosophy; this document extends it into
surfaces the brochure never needed: a live map, a chat interface, stacked
sheets, data-dense lists. Where the two disagree, it's because a dashboard has
constraints a five-section poster doesn't — each divergence below says so
explicitly and says why.

**Inherited unchanged:** every color token, both type families, the mono-only
IBM Plex Mono discipline for metadata, the pill-radius rule for controls, the
warm accent's scarcity discipline.

**Deliberately diverges:** the Two-Background Rule (an app needs surface
elevation — sheets stack over a map, popups stack over sheets), the
Flat-Unless-Floating Rule (loosened, not dropped — see Elevation below), type
scale (UI density replaces editorial cinema-scale `clamp()`), and the
Hairline-Grid-not-Cards stance (loosened for list rows, held for anything that
would read as a bordered dashboard card).

**New, because the product needs it:** map/layer color coding, the bottom
sheet, agent chat bubbles, route/itinerary components, a basemap-aware
contrast discipline.

## Overview

**Working name for the app's version of the instrument idea: "The Instrument,
Live."** The landing page *describes* a field instrument; the app *is* one. The
same restraint applies — no bordered-card dashboard aesthetic, no ambient
shadow soup, mono labels for metadata only — but an instrument you operate
needs affordances a poster doesn't: something to press, something that floats
above the map to stay reachable, a place state changes read at a glance.

The map is the instrument face. Everything else — the agent, the layers, the
route — is a control surface laid over it, and control surfaces are allowed to
float where the page's sections were not.

## Colors

No new brand hues. Two additions, both scoped narrowly and explained below:
a **surface elevation ramp** (steps of the existing ink/sky families, not new
colors — same discipline as the Opacity-Not-New-Color Rule) and a **map
category palette** (a cartographic problem, not a brand-chrome one — see its
own section).

### Surface elevation ramp

Built from the existing ink family stepped by opacity/lightness, the same way
`on-dark-*` tokens step off `paper`:

| Token | Value | Use |
|---|---|---|
| `surface-0` | `--sky-1` `#dfeaf3` | The map's page-level backdrop when no basemap tile has painted yet |
| `surface-1` | `--paper` `#e7f0f7` at 96% | Bottom sheet, layer panel — the first thing that floats over the map |
| `surface-2` | `--paper` `#e7f0f7` at 100%, 1px `on-light-line` border | Cards *inside* a sheet — route cards, POI popups — one step up from the sheet they sit in |
| `surface-dark-1` | `--ink-soft` `#17293a` at 96% | Dark-mode sheet equivalent |
| `surface-dark-2` | `--ink` `#101e2a`, 1px `on-dark-line` border | Dark-mode card equivalent |

This is the direct app-shaped answer to the landing page's Two-Background
Rule not applying here (`PLAN.md` §8.3, `ARCHITECTURE.md` §10.4): a dashboard
needs to show what's stacked above what, so it earns a third *register*, not a
third brand *color* — every step above is still ink or sky, just lifted.

### Map category palette (cartographic, not brand) — verified against real basemap tiles

**This section was rewritten after checking the first draft against MAPID's
actual `style.json` paint colors (background, landuse, water, road, building
fills for both `street-v2.0` and `dark-v2.0`), not just eyeballed.** Method:
fetch each style, extract the dominant backdrop colors a map object actually
sits on at city zoom, compute WCAG relative-luminance contrast (the same
formula `tokens.css` already cites for text) against each candidate hex,
apply the 3:1 threshold WCAG 1.4.11 sets for non-text graphical objects.

**The first draft failed badly.** A single hex per mode, reused across both
basemap styles, is the same mistake `tokens.css` already solved once for text
— one hue cannot be both light enough to read on a dark backdrop and dark
enough to read on a light one. Measured failures: `instrument-blue-lift`
(KRL) scored **1.65–2.58:1** on `street-v2.0` — a light blue nearly invisible
on the basemap's light-grey/white land and road fills. `tugu-gold`
(andong/becak) scored **1.44–2.24:1** on street for the same reason. The
"active route" accent, `tugu-gold-lit`, scored **1.01–1.59:1** on street —
functionally invisible, a bright yellow on near-white. Flipping the check:
`instrument-blue` (TransJogja) scored **2.59–3.09:1** on `dark-v2.0`, and the
YIA violet scored **1.89–2.26:1** there — both too dark against the dark
style's near-black land/water/building fills (`#0d0d0d`–`#202020`).

**The fix is the same pattern `tokens.css` already established for
`--warm`/`--warm-text`/`--warm-deep`: each mode gets a light-basemap value and
a dark-basemap value, not one hex asked to do both jobs.** Where an existing
token already has a documented light/dark pairing, reuse it — don't invent a
new one to duplicate a solved problem.

| Layer | On `street-v2.0` | On `dark-v2.0` | Notes |
|---|---|---|---|
| TransJogja (bus) | `instrument-blue` `#1f6592` (4.03:1 worst-case) | `instrument-blue-lift` `#5aa9dd` (6.33:1) | Reuses the existing pair exactly as `DESIGN.md` (landing page) already documents it — `blue-lift` is defined there as "used wherever Primary would be too heavy against ink." This *is* that case. |
| KRL (commuter rail) | `#0f766e` (3.50:1) | `#2dd4bf` (8.75:1) | New — a single teal hue at two lightness steps, same pattern as blue/blue-lift. Chosen specifically to sit far from TransJogja's blue so the two rail-adjacent modes stay distinguishable at a glance. |
| KA Bandara YIA (airport rail) | `#5b3a8e` (5.50:1) | `#b399e0` (6.63:1) | Same violet hue, lightened for dark — the original draft only specified the street half and left dark unverified, which is exactly the value that failed (1.89:1). |
| Andong / becak (first/last-mile) | `tugu-gold-deep` `#7c5e13` (3.87:1) | `tugu-gold-lit` `#f2c94c` (10.27:1) | **Correction, not a new pair:** the landing page's own `DESIGN.md` already documents `tugu-gold` as *background-fill use only*, with `tugu-gold-deep`/`tugu-gold-lit` reserved for exactly this foreground/line job on light/dark respectively. The first draft violated that already-written rule by putting bare `tugu-gold` on a line. Bare `tugu-gold` is still valid here for a **filled marker icon shape** (a pin's solid background, large enough area, paired with `ink` glyph on top) — just never a thin line or text-scale mark. |
| Active / selected route | `ink-soft` halo (9.49:1) | `paper` halo (14.12:1) | **Redesigned, not just recolored.** A fifth hue (`tugu-gold-lit` reused as "emphasis") failed on street at 1.01:1 and would have collided with andong/becak's dark-mode color besides. Standard transit-map fix instead: draw the selected route as its own mode color with a dark (`ink-soft`, street) or light (`paper`, dark) casing stroke behind it — a halo, not a hue swap. Works for *any* mode's color, on both basemap styles, with tokens already in the system. |
| Buildings (Urban Planning) | `ink-soft` `#17293a` at 12% fill (1.24–1.26:1 vs. backdrop — intentionally subtle) | `paper` `#e7f0f7` at 16–20% fill (1.49–1.83:1 vs. backdrop) | **Correction.** The original single `ink-soft`-at-12%-on-everything fill composites to **1.01–1.02:1 against `dark-v2.0`** — dark ink over near-black backdrop is not "subtle," it's gone. This is a decorative backdrop layer, not a foreground signal, so it isn't held to the 3:1 threshold the way lines/markers are — but "quiet" and "absent" are different outcomes, and the original value produced the second one on dark. |

`#0f766e`/`#2dd4bf` (KRL) and the dark-mode half of YIA's violet (`#b399e0`)
are the only genuinely new hexes in this document. Everything else in the
table is an existing brand token, used in its already-documented role or in
the direct light/dark-pair pattern that role establishes.

## Typography

Same two families as the landing page, different job. There is no display-face
use in the app — Quarkiz was the wordmark's cinematic scale, and nothing in a
dashboard is a wordmark. Archivo carries every UI text role; IBM Plex Mono
stays exactly what the landing page decided: metadata only, never a sentence.

### Hierarchy
- **Headline** (600, `clamp(20px, 2.4vw, 28px)`): screen titles — "Rute", "Sustainability Tracker". Far below the landing page's headline scale on purpose; a dashboard headline is a label for what's on screen, not a persuasive statement.
- **Title** (600, 16px): route card titles, sheet section headers, POI names in a popup.
- **Body** (400, 15px, line-height 1.5): agent chat text, form fields, descriptive copy. Tighter line-height than the landing page's 1.6 — chat bubbles are read in short bursts, not as flowing prose.
- **Body, small** (400, 13px): secondary chat/card text — timestamps, distance/fare sub-lines under a route step.
- **Label** (500, 11px, 0.16em tracking, mono, uppercase): same role the landing page gives it — index numbers, field labels, layer-toggle names, mode tags (`TRANSJOGJA`, `ANDONG`).

### Named rule carried over
**The Mono-Is-Metadata Rule still holds, and matters more here than on the
landing page.** A chat-and-forms UI is exactly where it's tempting to reach for
mono as a "technical" voice for body text — resist it. Mono stays reserved for
labels and tags; agent responses and user messages are always Archivo body
text, full stop.

## Layout

No fixed shell width — the app is full-viewport, map-first, not a centered
content column. `gutter` (16px) replaces the landing page's fluid `clamp()`
gutter; a dashboard's chrome doesn't need to breathe at poster scale.

**The map is always the base layer.** Every other surface — agent sheet, layer
sheet, route detail — is a sheet or overlay stacked above it, never a
full-screen replacement of it. Navigating to "route detail" pushes a sheet
higher, it doesn't navigate away from the map.

**Breakpoint: 900px**, matching the landing page's nav breakpoint for
consistency. Below it, the agent and layer panels are bottom sheets (§Bottom
Sheet below); at or above it, both promote to a left rail — same component
tree, per `ARCHITECTURE.md` §10.3, just repositioned, not rebuilt.

## Elevation & Depth

The landing page's Flat-Unless-Floating Rule doesn't disappear here — it
generalizes. The rule was never "no shadows," it was "a shadow must be earned
by floating over something." The hero CTA earned one by floating over the
diorama; here, **the map is the diorama**, and everything stacked above it
earns the same right.

### Shadow vocabulary
- **Sheet lift** (`box-shadow: 0 -8px 24px -8px rgba(16, 30, 42, 0.28)`): the bottom sheet and left rail, floating over the map. The app's equivalent of the hero CTA's earned shadow — same justification, same restraint (one shadow value, not a ramp of them).
- **Card lift** (`box-shadow: 0 4px 12px -4px rgba(16, 30, 42, 0.18)`): route cards and POI popups floating over a sheet — one step lighter than the sheet's own shadow, so stacking order stays visually legible.

### Named rule
**The Earns-Its-Float Rule** (this document's restatement of Flat-Unless-Floating
for a UI that has to stack surfaces): a shadow is permitted only on something
genuinely floating over the map or over another surface — never applied to a
flat row inside a list, a button, or a static panel just for visual weight.
Two shadow values exist in the whole app (above); introducing a third needs the
same "what is this floating over" justification the landing page already
requires.

## Shapes

Unchanged from the landing page: pill radius (999px) for every interactive
control — buttons, layer toggles, mode filter chips. Sheets use a top-only
rounded corner (`20px 20px 0 0`) since they rise from the screen edge, not a
uniform panel radius. Cards inside a sheet use the landing page's softer
`16px` panel radius. Corners elsewhere square, same as the landing page.

## Components

### Bottom Sheet (signature component, new)
Three snap points per `ARCHITECTURE.md` §10.3 / `PLAN.md` §8.1:

- **Peek** — input field only, agent collapsed. The default resting state.
- **Half** — input + recent conversation, enough to read the last exchange.
- **Full** — full conversation history, scrollable.

`surface-1` background, sheet-lift shadow, top-rounded. A drag handle
(a short `on-light-line`/`on-dark-line` bar, not an icon) signals draggability
without adding an icon system the rest of the design deliberately avoids. The
layer panel is a second, independent sheet — the two never occupy the same
snap-point space; opening one at "full" should collapse the other to "peek."

### Agent Chat Bubble (new)
No bubble-with-tail cartoon chat aesthetic — stays instrument-flat. User
messages: right-aligned, `instrument-blue` background, `paper` text, pill-ish
corners (12px, not full pill — pill radius is reserved for controls, and a
chat bubble is content, not a control). Agent messages: left-aligned, no fill,
`ink-soft`/`on-light-body` text directly on the sheet's `surface-1` — the agent
"speaks as the instrument," not as a separate colored party. This is a direct
descendant of the landing page's "no bordered-card" instinct: only the user's
own input gets a filled background, because it's the one thing that needs to
visually separate from the instrument's own voice.

Streaming state: a low-opacity mono `LABEL` reading `THINKING…` (not a spinner
icon, not animated dots) — consistent with the Image Slot component's
philosophy on the landing page: state your own status in text, don't perform a
loading animation that implies a promise about timing.

### Route Card / Itinerary Timeline (new)
A staged vertical timeline: walk → halte → transit → andong/becak → destination
(`PLAN.md` §8.2). Each stage is a hairline-separated row (`surface-2`, no
individual card shadow — only the timeline as a whole, if presented inside a
sheet, inherits that sheet's lift). Mode icons are not icons but colored 4px
verticals in the map category palette above, keeping the "no icon system"
discipline the landing page already holds. Distance/time/fare per leg in
`bodySmall`; the leg's mode name in `label` (mono, uppercase — `TRANSJOGJA`,
`JALAN KAKI`).

### Layer Toggle List (new)
A hairline list, not a settings-app switch grid — continues the landing
page's "Hairline Grid, not cards" instinct directly. Each row: layer name
(`title`), a small color swatch matching the map category palette, and a pill
toggle (`999px` radius, `instrument-blue` when active, `on-light-line` fill
when off). No nested/collapsible categories in v1 — six thematic layers
(`PRD` §4.2) fit one flat list.

### Sustainability Stat (new)
The One Warm Rule's clearest expression in the app, mirroring the landing
page's Index Marker component: the carbon-saved figure is set in
`tugu-gold-deep` (light surfaces) / `tugu-gold-lit` (dark surfaces) on
`surface-1`/`surface-2` — the same verified light/dark gold pair the map uses
for andong/becak (§Map category palette above), reused here for the same
reason: it's gold appearing as text/foreground, which is exactly what
`tugu-gold-deep`/`tugu-gold-lit` are for. Bare `tugu-gold` never appears here —
consistent with it being fill-only everywhere in this system, chrome and map
alike. Source citation
(`ARCHITECTURE.md` §5.1's `emission_factors.source_citation`) renders directly
beneath it in `label` scale — never omitted, per the same non-negotiable the
landing page and PRD both hold on invented numbers.

### Buttons
Unchanged from the landing page: pill shape, `instrument-blue` primary fill /
`paper` text, hover swaps to `ink-soft`. The app adds one variant the landing
page didn't need — a **map floating action button** (locate-me, recenter):
circular (not pill-elongated, since it has no label, just centers a symbol),
`surface-1` fill, card-lift shadow, since it floats directly over the map like
every other elevated surface here.

### Basemap Switcher (new)
A small pill-radius segmented control (`street` / `dark`) in a map corner,
`surface-1` background, sheet-lift shadow (it floats over the map like
everything else). Not satellite/light in v1 UI — those two styles remain
available at the data layer (`ARCHITECTURE.md` §6.1) but the switcher only
exposes the two this document has verified contrast for (§Colors above);
add the rest once their contrast is checked the same way.

## Do's and Don'ts

### Do:
- **Do** treat every color in this document as either inherited from the
  landing page's `DESIGN.md` unchanged, or explicitly justified above — no
  color exists here "because it looked nice."
- **Do** check every map-layer and UI color against both `street-v2.0` and
  `dark-v2.0` basemap tiles before finalizing (`PLAN.md` §8.4) — done for the
  palette in §Map category palette above, against the styles' actual paint
  colors, not a screenshot; do the same for anything added later rather than
  eyeballing it against a preview thumbnail.
- **Do** keep IBM Plex Mono reserved for metadata — labels, mode tags, index
  numbers — never chat body text, never route descriptions.
- **Do** justify any new shadow by what it's floating over, same discipline as
  the landing page's hero CTA.
- **Do** keep the map as the one base layer everything else stacks above —
  never navigate away from it to a different full-screen view.

### Don't:
- **Don't** invent a UI hue outside the map category palette's four new
  values (`#5b3a8e`/`#b399e0` for YIA, `#0f766e`/`#2dd4bf` for KRL) — everything
  else in this document is an existing brand token, used in its documented
  role or in the light/dark-pair pattern that role already establishes.
- **Don't** assign a single hex to a map layer across both basemap styles —
  the §Map category palette rewrite exists because that mistake shipped once
  already; verify light and dark separately, every time.
- **Don't** give agent messages a filled chat-bubble background — only user
  messages get one; the agent speaks as the instrument itself.
- **Don't** add a spinner, skeleton shimmer, or animated loading icon anywhere
  — state absence/pending status in mono text, per the Image Slot precedent.
- **Don't** let a route card, POI popup, or layer row acquire its own
  individual shadow if it's sitting flat inside an already-elevated sheet —
  only the outermost floating surface earns the shadow.
- **Don't** treat this document as final before it's been through the Claude
  Design canvas and at least one real screen has been built against it — see
  the status line at the top.
