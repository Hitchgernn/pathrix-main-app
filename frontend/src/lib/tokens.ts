/** Palette values that JS needs (SVG overlay strokes, MapLibre paint props).
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

/** Route and marker colours are verified against both basemap treatments —
 *  a line colour that reads on street disappears on dark (ARCHITECTURE.md §10.4). */
const PALETTE: Record<Basemap, MapPalette> = {
  street: {
    krl: "#0f766e",
    gold: "#7c5e13",
    blue: "#1f6592",
    walk: "#17293a",
    halo: "#17293a",
    stopFill: "#e7f0f7",
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

export const SURFACE_SHEET = "rgba(231,240,247,.96)";
export const LINE = "rgba(16,30,42,.14)";
export const SHEET_LIFT = "0 -8px 24px -8px rgba(16, 30, 42, 0.28)";
export const RAIL_LIFT = "8px 0 24px -8px rgba(16, 30, 42, 0.28)";
export const CARD_LIFT = "0 4px 12px -4px rgba(16, 30, 42, 0.18)";

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

/** Desktop left rail width. The breakpoint promotes both sheets to rails
 *  without changing the component tree (ARCHITECTURE.md §10.3). */
export const RAIL_W = 392;
export const WIDE_BREAKPOINT = 900;
export const PEEK_H = 96;
