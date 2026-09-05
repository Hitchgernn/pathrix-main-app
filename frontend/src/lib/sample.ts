/** Content transcribed verbatim from the Claude Design canvas.
 *
 *  This is demo content, not a fixture the backend will ever return: no field
 *  survey data has landed and no LLM provider is wired (ARCHITECTURE.md §15.1),
 *  so the app falls back to this so the screens are inspectable. Everything
 *  here is replaced by live data the moment `/ws` answers — see store/index.ts.
 */

import type { MessageKey } from "../i18n";

export interface SampleLeg {
  modeKey: MessageKey;
  key: "walk" | "gold" | "krl" | "blue";
  /** Place names, left literal on purpose: they read the same in both locales
   *  and match the signage someone is standing in front of. */
  title: string;
  subKey: MessageKey;
  detailKey: MessageKey;
}

export const SAMPLE_LEGS: SampleLeg[] = [
  {
    modeKey: "demo.leg1.mode",
    key: "walk",
    title: "Malioboro → Pangkalan Becak Sosrowijayan",
    subKey: "demo.leg1.sub",
    detailKey: "demo.leg1.detail",
  },
  {
    modeKey: "demo.leg2.mode",
    key: "gold",
    title: "Pangkalan Sosrowijayan → Stasiun Lempuyangan",
    subKey: "demo.leg2.sub",
    detailKey: "demo.leg2.detail",
  },
  {
    modeKey: "demo.leg3.mode",
    key: "krl",
    title: "Lempuyangan → Stasiun Brambanan",
    subKey: "demo.leg3.sub",
    detailKey: "demo.leg3.detail",
  },
  {
    modeKey: "demo.leg4.mode",
    key: "walk",
    title: "Stasiun Brambanan → Pangkalan Andong",
    subKey: "demo.leg4.sub",
    detailKey: "demo.leg4.detail",
  },
  {
    modeKey: "demo.leg5.mode",
    key: "gold",
    title: "Pangkalan Brambanan → Candi Prambanan",
    subKey: "demo.leg5.sub",
    detailKey: "demo.leg5.detail",
  },
];

export const SAMPLE_SUMMARY_KEYS: MessageKey[] = [
  "demo.summary.time",
  "demo.summary.fare",
  "demo.summary.distance",
  "demo.summary.transfers",
];

export interface LayerRow {
  id: string;
  /** Backend catalogue id this row is served by, when one exists. */
  backendId: string | null;
  nameKey: MessageKey;
  metaKey: MessageKey;
  on: boolean;
  color: string;
}

export const LAYER_ROWS: LayerRow[] = [
  { id: "transit", backendId: "transit", nameKey: "layer.transit.name", metaKey: "layer.transit.meta", on: true, color: "#1f6592" },
  { id: "pangkalan", backendId: "pangkalan", nameKey: "layer.pangkalan.name", metaKey: "layer.pangkalan.meta", on: true, color: "#7c5e13" },
  { id: "pariwisata", backendId: "poi", nameKey: "layer.pariwisata.name", metaKey: "layer.pariwisata.meta", on: false, color: "#5b3a8e" },
  { id: "properti", backendId: "properti", nameKey: "layer.properti.name", metaKey: "layer.properti.meta", on: false, color: "#17293a" },
  { id: "jangkauan", backendId: null, nameKey: "layer.jangkauan.name", metaKey: "layer.jangkauan.meta", on: false, color: "#c6d9e8" },
  { id: "bangunan", backendId: null, nameKey: "layer.bangunan.name", metaKey: "layer.bangunan.meta", on: false, color: "rgba(23,41,58,.12)" },
];

/** Home's action grid. Each tile hands the agent a real prompt or drives the
 *  map directly — none of them are decorative. */
export interface QuickAction {
  id: string;
  icon: "route" | "bus" | "carriage" | "layers";
  titleKey: MessageKey;
  subKey: MessageKey;
  prompt: string | null;
  /** Layer ids to switch on when the tile is a map action rather than a query. */
  layers?: string[];
  /** Subject to look up a real photograph for (lib/photos.ts). Omitted where no
   *  honest photograph exists for the concept, and the tile stays iconographic. */
  photo?: string;
}

export const QUICK_ACTIONS: QuickAction[] = [
  {
    id: "rute",
    icon: "route",
    titleKey: "action.route.title",
    subKey: "action.route.sub",
    prompt: "Malioboro → Candi Prambanan",
    photo: "Malioboro",
  },
  {
    id: "halte",
    icon: "bus",
    titleKey: "action.stops.title",
    subKey: "action.stops.sub",
    prompt: "Halte TransJogja terdekat",
    photo: "TransJogja",
  },
  {
    id: "pangkalan",
    icon: "carriage",
    titleKey: "action.pangkalan.title",
    subKey: "action.pangkalan.sub",
    prompt: null,
    layers: ["pangkalan"],
    photo: "Andong",
  },
  {
    id: "layer",
    icon: "layers",
    titleKey: "action.layers.title",
    subKey: "action.layers.sub",
    prompt: null,
  },
];

/** Explore's filter row. Each chip is a view over the same layer catalogue the
 *  panel exposes in full — chips are the fast path, not a second system. */
export interface FilterChip {
  id: string;
  labelKey: MessageKey;
  /** Layer ids switched on when the chip is picked. Empty means "show all". */
  layers: string[];
}

export const FILTER_CHIPS: FilterChip[] = [
  { id: "semua", labelKey: "filter.all", layers: [] },
  { id: "transit", labelKey: "filter.transit", layers: ["transit"] },
  { id: "pangkalan", labelKey: "filter.pangkalan", layers: ["pangkalan"] },
  { id: "pariwisata", labelKey: "filter.tourism", layers: ["pariwisata"] },
  { id: "properti", labelKey: "filter.property", layers: ["properti"] },
  { id: "jangkauan", labelKey: "filter.reach", layers: ["jangkauan"] },
];

export interface QuickPrompt {
  key: MessageKey;
  route: boolean;
}

export const QUICK: QuickPrompt[] = [
  { key: "quick.route", route: true },
  { key: "quick.cheapest", route: false },
  { key: "quick.nearest", route: false },
];



/** Shown on Home only while the real, localStorage-backed recents list is
 *  still empty — see store/index.ts `recentsForDisplay`. */
/** Shown on Home only while the real, localStorage-backed recents list is
 *  still empty. Keys rather than text, so the samples follow the locale. */
export const SEED_RECENTS: { titleKey: MessageKey; promptKey: MessageKey; at: number }[] = [
  { titleKey: "demo.recent1.title", promptKey: "demo.recent1.prompt", at: Date.now() - 3 * 864e5 },
  { titleKey: "demo.recent2.title", promptKey: "demo.recent2.prompt", at: Date.now() - 7 * 864e5 },
];

export const SAMPLE_CARBON = {
  trip: "2,41 kg",
  month: "18,6 kg",
  trips: "12",
  basisKey: "demo.carbon.basis" as MessageKey,
  source: "KLHK (2023), IPCC 2006 Tier 1",
  caveatKey: "demo.carbon.caveat" as MessageKey,
};

/** The design's sample route mirrors the alternative offer under the timeline. */
export const SAMPLE_ALTERNATIVE = {
  labelKey: "demo.alt.label" as MessageKey,
  titleKey: "demo.alt.title" as MessageKey,
  subKey: "demo.alt.sub" as MessageKey,
};
