---
name: Pathrix App
description: Design system for the WebGIS AI Agent — dashboard, map, and agent UI (extends the marketing-site system, not a replacement for it)
colors:
  ink: "#17171a"
  ink-2: "rgba(23,23,26,.74)"
  ink-3: "rgba(23,23,26,.64)"
  ink-4: "rgba(23,23,26,.56)"
  ground: "#f3f1ee"
  surface: "#ffffff"
  surface-2: "#faf8f6"
  surface-3: "#efece8"
  line: "rgba(23,23,26,.08)"
  line-strong: "rgba(23,23,26,.14)"
  tugu-gold: "#c08a2e"
  tugu-gold-deep: "#7c5e13"
  tugu-gold-tint: "#f7eedd"
  instrument-blue: "#1f6592"
  instrument-blue-lift: "#5aa9dd"
  krl-teal: "#0f766e"
  krl-teal-lift: "#2dd4bf"
  yia-violet: "#5b3a8e"
  yia-violet-lift: "#b399e0"
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

**Status:** ✅ implemented, light and dark. This document is the app's visual source of truth
and `frontend/src/styles/index.css` is its implementation. The Claude Design
canvas that seeded the first build is not authoritative and has not been since
the warm-neutral repaint.

## The world, in one paragraph

Warm bone ground. White and frosted surfaces. Near-black as the action colour,
so every filled control on every screen is the same ink the body text is set in.
One accent, tugu gold, doing exactly one job per screen. Archivo carries all
language; IBM Plex Mono is reserved for figures. The map is the only saturated
thing on screen, and that is the point: everything in the chrome recedes so the
cartography can be read.

The register was derived from `inspirations/` — a pearl/glass ride-hailing
concept and a place-detail screen whose only colour is an amber rating star.
That star's role is the role this system already reserved for tugu gold, so the
reference and the brand converged rather than competing. What the references
replaced was the earlier blue-on-blue-grey chrome, which read as generic and
competed with the basemap it sat on.

## Relationship to the marketing site's `DESIGN.md`

Same brand, different load. The landing page's `DESIGN.md`
(`pathrix-landingpage/DESIGN.md`) owns the instrument philosophy, both type
families, and the warm accent's scarcity discipline. This document extends that
into surfaces a brochure never needed: a live map, a chat interface, stacked
sheets, data-dense lists.

**Inherited unchanged:** both type families, the warm accent's scarcity rule and
its fill/read pair, the pill radius for controls, and the whole map category
palette below.

**Deliberately diverges, and why:**

- **Surface colour.** The landing page's sky/paper blue-grey does not survive
  contact with a basemap: blue-grey chrome over a blue-grey map leaves the
  cartography nothing to be the loudest thing on screen. The app's ramp is warm
  bone and white instead.
- **The action colour is ink, not the brand blue.** A saturated button competes
  with route lines for the same attention. White on `#17171a` is 17.89:1 and
  needs no further justification.
- **Mono is figures only.** The landing page's Mono-Is-Metadata rule put mono on
  every label; at app density that produced an uppercase eyebrow over every
  heading and made the product read as an instrument panel. Mono keeps fares,
  durations, distances, coordinates and counts, where tabular numerals earn it.
- **The Two-Background Rule** does not apply; an app needs surface elevation.
- **Flat-Unless-Floating** is loosened into the Earns-Its-Float Rule below.

**New, because the product needs it:** the surface elevation ramp, the map
category palette, the bottom sheet, agent chat bubbles, route components, and a
basemap-aware contrast discipline.

## Overview

**The app's version of the instrument idea: "The Instrument, Live."** The
landing page *describes* a field instrument; the app *is* one. The restraint
carries over — no bordered-card dashboard aesthetic, no ambient shadow soup —
but an instrument you operate needs affordances a poster does not: something to
press, something that floats above the map to stay reachable, a place where a
state change reads at a glance.

The map is the instrument face. Everything else, the agent and the layers and
the route, is a control surface laid over it, and control surfaces are allowed
to float where the page's sections were not.

## Colors

The chrome is a warm neutral ramp plus one accent. Everything else on screen is
either the map or a photograph. Two color systems live here and must not be
confused: the **chrome ramp** (this section) and the **map category palette**
(its own section below), which is cartographic and was measured against real
basemap tiles.

### Named rule
**The Measured-Step Rule.** No grey, tint, or accent enters this system without
its contrast ratio computed against the surfaces it will actually sit on, and
recorded in the tables below. The map palette was rewritten once because a colour
was chosen by eye and measured afterwards; the chrome ramp does not repeat that.
`frontend/src/lib/tokens.ts` mirrors every value JS needs and moves with the CSS.

### Surface elevation ramp

An app has to show what is stacked above what, so it earns a third *register* —
still not a third brand *colour*. White floats on bone; frosted white floats on
the map.

| Token | Value | Use |
|---|---|---|
| `--color-ground` | `#f3f1ee` | Warm bone page ground; 1.13 under `surface` |
| `--color-surface` | `#ffffff` | Cards, sheets, nav, fields |
| `--color-surface-2` | `#faf8f6` | Inset rows and quiet fields inside a white surface |
| `--color-surface-3` | `#efece8` | Pressed and hovered rows, icon wells, avatar fallback |
| `surface-float` | `#ffffff` at 86% + `blur(20px)` | Chrome directly over the map, so the basemap still reads as the layer underneath |

`surface-float` carries a solid fallback under `prefers-reduced-transparency`.
It is for chrome over the *map* only: the bottom tab bar is solid white, because
at 86% a scrolling list reads straight through it and looks like an overflow bug.

**Why warm rather than the landing page's `paper`.** The use scene decides it:
someone standing on Malioboro at midday, screen at full brightness, phone at
arm's length. Blue-grey chrome over a blue-grey basemap gives the cartography
nothing to win against. Bone does.

### Dark

**The dark theme is a token swap, and that is the whole design.** Because
`--color-ink` is both the text colour and the primary fill, flipping ink light
and surface dark turns every `bg-ink text-surface` button in the app into a
light button with dark text. No component knows a theme exists.

| Token | Light | Dark |
|---|---|---|
| `--color-ground` | `#ffffff` | `#0d0d0f` |
| `--color-surface` | `#ffffff` | `#17171a` |
| `--color-surface-2` | `#f7f7f8` | `#1f1f23` |
| `--color-surface-3` | `#eeeef0` | `#2a2a30` |
| `--color-ink` | `#17171a` | `#f2f2f3` |
| `--color-line` | ink @ 10% | white @ 12% |
| `--color-gold` / `-text` | `#c08a2e` / `#7c5e13` | `#f2c94c` for both |

Two rules hold across the swap:

- **`--color-ink-4` stays non-text in both themes.** Dark has more headroom —
  its `.52` step would still be AA — but the step is held at the same contract
  so a component that is legal in dark cannot be illegal in light.
- **Gold's fill/read split collapses in dark and that is correct.** On white the
  saturated value is 3.04:1 and can only be a graphic; on dark, `tugu-gold-lit`
  is 11.27:1 and reads as text as happily as it marks a star. This is the
  light/dark pair the landing page's system already documents.

**Appearance is one decision, not two.** Picking dark switches the chrome *and*
the basemap; a light app floating over a dark map is a bug, not a preference.
The map-corner control sets it, and Profil adds "system" for following the OS.

`data-theme` is stamped by a pre-paint script in `index.html` reading the same
`pathrix.v1` key the store persists to, so there is no flash of the wrong theme
and no second source of truth in a media query. `color-scheme` follows it, so
scrollbars and form furniture theme themselves.

### Ink, and why ink is also the action colour

| Token | Value | On white | On ground | Use |
|---|---|---|---|---|
| `--color-ink` | `#17171a` | 17.89 | 15.87 | Primary text **and every filled control** |
| `--color-ink-2` | ink @ 74% | 7.67 | 7.14 | Secondary body |
| `--color-ink-3` | ink @ 64% | 5.32 | 5.15 | Metadata and labels; smallest step still AA for text |
| `--color-ink-4` | ink @ 56% | 4.11 | 3.96 | **Non-text only** — icon strokes and rules, WCAG 1.4.11 |

Anything lighter than `ink-4` fails even the 3:1 graphics threshold on the
ground, which is why the ramp stops there.

**Every filled button in this app is black.** A saturated primary competes with
the route lines for the same attention, on the one screen where the route lines
are the product. Ink wins the contrast argument outright and settles the colour
argument by not having one. Hover lifts to `ink/90`; press is a `.985` scale.

### The one accent

| Token | Value | Contrast | Use |
|---|---|---|---|
| `--color-gold` | `#c08a2e` | 3.04 on white | **Fill only** — a star, a marker, an icon |
| `--color-gold-text` | `#7c5e13` | 6.06 on white, 5.26 on the tint | Anything that has to be read |
| `--color-gold-tint` | `#f7eedd` | — | The wash behind a gold figure |

This is the landing page's `tugu-gold` / `tugu-gold-deep` pair in its documented
roles, and it is the same split the place reference uses: an amber star as a
graphic, never as a word. The accent gets one job per screen. On Home it is the
carbon chip; on a place sheet it is the survey badge; on the map it is
andong/becak. It is never a second button colour.

### Map category palette (cartographic, not brand) — verified against real basemap tiles

> **Untouched by the warm-neutral repaint.** These hexes were measured against
> MAPID's real `street-v2.0` / `dark-v2.0` paint. Recolouring the app's chrome
> did not change what sits under a route line, so nothing below moved. This is
> also the only place `instrument-blue` still appears in the product.

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

Both families carry over. Archivo does every text role; IBM Plex Mono is reduced
to one job.

### Hierarchy
- **Greeting** (400, `clamp(28px, 7vw, 36px)`): the one welcome line on Home. Set light and large, the way the reference does; weight carries the hierarchy, not scale alone.
- **Headline** (600, `clamp(22px, 2.4vw, 28px)`): screen and sheet titles.
- **Title row** (600, 16px): card titles, place names, section heads.
- **Body** (400, 15px / 1.5): agent prose, descriptive copy.
- **Body, small** (400, 13px / 1.45): secondary card and row text.
- **Label** (600, 12px, `-0.005em`, sentence case): field labels, kind tags, group headings. **Never uppercase, never tracked out.**
- **Figure** (mono, tabular): fares, durations, distances, coordinates, counts, badges. Loaded at 400/500 only, so a figure is never set above `font-medium`.

### Named rules
**The Figures-Only Rule** (replaces Mono-Is-Metadata). Mono is for numerals and
the units bound to them. Not labels, not tags, not status lines, not prose. The
previous build put mono on every label and the product read as an instrument
panel; the same restraint applied only to figures reads as precision.

**No eyebrows.** A small tracked-out label above a heading is banned outright.
The heading carries itself, and its position on the screen already says what
section it is. This is the single change that did most to move the app out of
the templated register.

## Layout

No fixed shell width. The app is full-viewport and map-first, never a centred
content column. A 16px gutter replaces the landing page's fluid one; app chrome
does not need to breathe at poster scale.

**The map is the base layer.** Every other surface is stacked above it and never
replaces it. Opening route detail raises a sheet; it does not navigate away.

**Breakpoint: 900px.** Below it, the five destinations sit in a floating tab bar
and screens stack over the map. At or above it, the nav promotes to a 248px
sidebar (collapsible to 76px) and the active screen to a 384px context panel
beside a map that stays in frame. Same component tree, repositioned
(`ARCHITECTURE.md` §10.3). Desktop is the mobile design promoted, not a second
product; the desktop reference contributed its sidebar structure and nothing
else.

### Shape

One documented scale, applied everywhere:

| Radius | Value | Applies to |
|---|---|---|
| `control` | `999px` | Every interactive control: buttons, chips, fields, toggles |
| `field` | `16px` | Chat bubbles |
| `card` | `20px` | Cards and photographs inside a surface |
| `tile` | `24px` | Home action tiles, settings groups |
| `sheet` | `28px` | Sheets, the place card, the tab bar |

A mixed radius system is only legible when the rule is written down. This is the
rule; anything that breaks it is a bug, not a variation.

## Elevation & Depth

The landing page's Flat-Unless-Floating Rule doesn't disappear here — it
generalizes. The rule was never "no shadows," it was "a shadow must be earned
by floating over something." The hero CTA earned one by floating over the
diorama; here, **the map is the diorama**, and everything stacked above it
earns the same right.

### Shadow vocabulary

Four values, all tinted warm to the ground rather than the old blue-grey, all
carrying a real offset and a soft blur (a zero-offset halo is decoration, not
depth):

| Token | Floats over |
|---|---|
| `--shadow-card` | A card or tile resting on the ground |
| `--shadow-float` | Chrome over the map: tab bar, FABs, chips, the place card |
| `--shadow-sheet` | A bottom sheet over the map |
| `--shadow-rail` | The desktop context panel against the map |

### Named rule
**The Earns-Its-Float Rule** (this document's restatement of Flat-Unless-Floating
for a UI that stacks surfaces): a shadow is permitted only on something genuinely
floating over the map or over another surface. Never on a flat row inside a list,
never on a static panel for visual weight. A fifth value needs the same "what is
this floating over" answer.

## Components

### Bottom Sheet (signature component, new)
Three snap points per `ARCHITECTURE.md` §10.3 / `PLAN.md` §8.1:

- **Peek** — input field only, agent collapsed. The default resting state.
- **Half** — input + recent conversation, enough to read the last exchange.
- **Full** — full conversation history, scrollable.

`--color-surface` at 94% with a blur (`surface-float`), sheet-lift shadow,
24px rounded corners, inset 8px from the screen edges so it reads as floating
rather than welded to the frame. **Peek is sized to fit the composer**, not set
to a round number — a peek that clips the input hides the one control that must
always be reachable. A drag handle
(a short `on-light-line`/`on-dark-line` bar, not an icon) signals draggability
without adding an icon system the rest of the design deliberately avoids. The
layer panel is a second, independent sheet — the two never occupy the same
snap-point space; opening one at "full" should collapse the other to "peek."

### Agent Chat Bubble (new)
No bubble-with-tail cartoon chat aesthetic — stays instrument-flat. User
messages: right-aligned, `ink` background, white text, `field` radius (16px, not
a full pill: pill radius is reserved for controls, and a chat bubble is content).
Agent messages: left-aligned, no fill, `ink` text directly on the sheet, because
the agent speaks as the instrument rather than as a separate coloured party. This is a direct
descendant of the landing page's "no bordered-card" instinct: only the user's
own input gets a filled background, because it's the one thing that needs to
visually separate from the instrument's own voice.

Streaming state: a low-opacity mono `LABEL` reading `THINKING…` (not a spinner
icon, not animated dots) — consistent with the Image Slot component's
philosophy on the landing page: state your own status in text, don't perform a
loading animation that implies a promise about timing.

### Route Card / Itinerary Timeline (new)
A staged vertical timeline: walk → halte → transit → andong/becak → destination
(`PLAN.md` §8.2). Each stage is a hairline-separated row (white, no
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
toggle (`999px` radius, `ink` when active, `line-strong` when off; a
`line`-weight track disappears on white). Built on Radix's Switch for the
keyboard behaviour a hand-rolled div does not get for free. No nested
categories: six thematic layers (`PRD` §4.2) fit one flat list.

The same layer set is also reachable as a **filter chip row** over the map.
Chips are single-select, ink when chosen, and write to the same active set the
list toggles: one source of truth at two densities. Multi-select stays in the
list, one tap away at the end of the row.

### Sustainability Stat (new)
The One Warm Rule's clearest expression in the app, mirroring the landing
page's Index Marker component: the carbon-saved figure is set in
`tugu-gold-deep`, in mono, on white or on `tugu-gold-tint` — the same verified light/dark gold pair the map uses
for andong/becak (§Map category palette above), reused here for the same
reason: it's gold appearing as text/foreground, which is exactly what
`tugu-gold-deep`/`tugu-gold-lit` are for. `--color-gold-tint` `#f7eedd` is the
matching wash for the figure's chip on Beranda. Bare `tugu-gold` never appears here —
consistent with it being fill-only everywhere in this system, chrome and map
alike. Source citation
(`ARCHITECTURE.md` §5.1's `emission_factors.source_citation`) renders directly
beneath it in `label` scale — never omitted, per the same non-negotiable the
landing page and PRD both hold on invented numbers.

### Buttons
Pill shape. **Primary is `ink` with white text (17.89:1)**, hover `ink/90`, press
a `.985` scale for a physical push. Secondary is white with a `line-strong`
border and `ink-2` text. There is no coloured button in this system; §Ink says
why. A screen gets one primary, and the place sheet's footer is the pattern:
one quiet icon action beside one filled one. The app adds one variant the landing
page didn't need — a **map floating action button** (locate-me, recenter):
circular (not pill-elongated, since it has no label, just centers a symbol),
`surface-float` fill, card-lift shadow, since it floats directly over the map like
every other elevated surface here.

### Navigation (new)
Five destinations, one definition list, two renderings. **Mobile:** a floating
**solid** white bar inset from the screen edges, five icon-plus-label items. The
active one is marked by ink and weight alone: no rule, no filled pill, because a
coloured indicator would compete with the primary action present on nearly every
screen. Solid rather than frosted, because a scrolling list read straight through
it at 86%.
**Desktop:** the same five in a 248px sidebar (collapsible to 76px), grouped
"Navigasi" / "Milik Anda", with the local profile pinned at the bottom. This
structure is the one thing taken from the desktop reference; its palette is not. Docked to
the screen edge, because a sidebar that floats over nothing has not earned it.

Iconography is `lucide-react` at 1.7 stroke (2.1 when active). Where the library
has no glyph — the andong and becak — the icon is **drawn in lucide's own
grammar** (24px box, currentColor, round caps) in `components/icons.tsx`, never
substituted with an emoji.

### Place Sheet (new)
The detail surface for a tapped marker or a chosen search result. Mobile: rises
from the bottom over the map. Desktop: a 364px card beside the nav, anchored to
the pin the map just flew to. Same content, same order, same actions — only the
anchor moves.

Header is a circular back button, a screen title, and the heart. Then the hero
photograph, a kind pill (plus a gold survey badge where a surveyor actually
stood), name, subtitle, outlined fact chips, and a detail list: coordinate,
source, and the photo credit when one is owed. Footer is share beside a filled
`Rute ke sini`.

**Photographs are real or absent.** `lib/photos.ts` resolves named landmarks
against Wikipedia and credits them; anything it cannot honestly identify gets
the drawn placeholder, which says why. Stock imagery under the name of a real
halte is the one thing this system will not do.

Selecting a place also drops a pin on the map. A card that names a coordinate
the map never marks is a card about nothing.

### Search (new)
One surface for the whole app, opened from Beranda's field or the map's pill.
`cmdk` supplies listbox semantics and arrow-key movement; filtering is
server-side (`GET /api/geocode`). Results sit on one white card with hairline
separators, each row marking the matched substring in `ink` weight so a hit
explains itself, and the list closes with an honest count and provenance
line (`3 HASIL · DATA PATHRIX & ALAMAT`). Empty and failed states are distinct
and both offer the agent as the next move.

### Basemap Switcher (new)
A small pill-radius segmented control (`street` / `dark`) in a map corner,
`surface-float` background, card-lift shadow, icon-only (sun / moon) with the
active half filled `ink` like every other active control — it sits in a corner beside two other round controls and a
text pill breaks that rhythm. Not satellite/light in v1 UI — those two styles remain
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
- **Don't** introduce a UI hue at all. The chrome is ink, the neutral ramp, and
  one gold accent. New colour belongs to the map category palette or nowhere.
- **Don't** make a filled button any colour but `ink`, or give a screen two
  primaries.
- **Don't** assign a single hex to a map layer across both basemap styles —
  the §Map category palette rewrite exists because that mistake shipped once
  already; verify light and dark separately, every time.
- **Don't** give agent messages a filled chat-bubble background — only user
  messages get one; the agent speaks as the instrument itself.
- **Don't** add a spinner, skeleton shimmer, or animated loading icon. State
  absence and pending status in words.
- **Don't** set an uppercase, tracked-out label above a heading. No eyebrows.
- **Don't** put mono on anything that is not a figure.
- **Don't** show a photograph the app cannot honestly attribute to the place
  it is labelled with.
- **Don't** let a route card, POI popup, or layer row acquire its own
  individual shadow if it's sitting flat inside an already-elevated sheet —
  only the outermost floating surface earns the shadow.
- **Don't** add a grey, tint, or accent without measuring it against the
  surfaces it will sit on and recording the ratio — the Measured-Step Rule.
- **Don't** use `--color-ink-4` for text. It is 3.96:1 on the ground: icon
  strokes and rules only.
- **Don't** put an element reset outside `@layer base`. An unlayered
  `button { background: none }` outranks every layered utility and silently
  turns each button-shaped floating control transparent over the map.
