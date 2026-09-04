/** Palette values that JS needs (MapLibre paint props, inline styles).
 *  CSS-only values live in styles/index.css; these two must stay in step. */

export type Basemap = "street" | "dark";

export interface MapPalette {
  krl: string;
  gold: string;
  blue: string;
  walk: string;
  halo: string;
  stopFill: string;
}

/** Inherited unchanged from docs/DESIGN.md §Map category palette. These are
 *  cartographic, not chrome: each hex was measured against MAPID's real
 *  street-v2.0 / dark-v2.0 paint colours at the WCAG 1.4.11 3:1 threshold. The
 *  white repaint of the app's chrome does not touch them — the basemap under a
 *  route line did not change. */
const PALETTE: Record<Basemap, MapPalette> = {
  street: {
    krl: "#0f766e",
    gold: "#7c5e13",
    blue: "#1f6592",
    walk: "#17293a",
    halo: "#17293a",
    stopFill: "#ffffff",
  },
  dark: {
    krl: "#2dd4bf",
    gold: "#f2c94c",
    blue: "#5aa9dd",
    walk: "#e7f0f7",
    halo: "#e7f0f7",
    stopFill: "#0c1822",
  },
};

export const paletteFor = (basemap: Basemap): MapPalette => PALETTE[basemap];

/** Chrome values, mirroring @theme in styles/index.css. Warm neutral: the
 *  action colour is ink, not a hue. */
export const SURFACE = "#ffffff";
export const SURFACE_FLOAT = "rgba(255,255,255,.86)";
export const GROUND = "#ffffff";
export const INK = "#17171a";
export const LINE = "rgba(23,23,26,.1)";
/** Fill-only accent (3.04:1 on white — a graphical object, never text) and the
 *  deep pair for anything that has to be read (6.06:1). */
export const GOLD = "#c08a2e";
export const GOLD_TEXT = "#7c5e13";

export const CARD_LIFT =
  "0 1px 2px rgba(23,23,26,.04), 0 8px 20px -8px rgba(23,23,26,.1)";
export const FLOAT_LIFT =
  "0 2px 6px rgba(23,23,26,.05), 0 16px 40px -12px rgba(23,23,26,.16)";
export const SHEET_LIFT =
  "0 -1px 3px rgba(23,23,26,.03), 0 -20px 48px -16px rgba(23,23,26,.14)";
export const RAIL_LIFT =
  "1px 0 3px rgba(23,23,26,.03), 20px 0 48px -16px rgba(23,23,26,.12)";

/** Which stroke colour each itinerary leg mode draws in. Backend EdgeType maps
 *  onto the design's four visual families. */
export const MODE_KEY: Record<string, keyof MapPalette> = {
  walk: "walk",
  board: "blue",
  ride: "blue",
  alight: "blue",
  transfer: "blue",
  andong: "gold",
  becak: "gold",
};

/** Desktop shell metrics. Above WIDE_BREAKPOINT the mobile tab bar promotes to
 *  a nav sidebar and the active screen promotes to a context panel beside it —
 *  same component tree, repositioned (ARCHITECTURE.md §10.3). */
export const NAV_W = 248;
export const NAV_W_COLLAPSED = 76;
export const PANEL_W = 384;
export const WIDE_BREAKPOINT = 900;

/** Mobile bottom-nav height, and the gap every bottom-anchored floating control
 *  keeps above it. */
export const TABBAR_H = 64;
export const TABBAR_GAP = 12;
export const PEEK_H = 96;
