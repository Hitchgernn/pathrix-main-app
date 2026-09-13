import { currentLocale } from "../i18n";
import { translate } from "../i18n";
import type { CarbonLogEntry } from "./places";
import { MODE_KEY } from "./tokens";
import type { Route } from "./types";

/** Grouping and decimal marks follow the locale: Indonesian writes Rp63.000 and
 *  17,1 km; English writes Rp63,000 and 17.1 km. Reading the store directly is
 *  the pattern lib/actions.ts already uses for module-level code. */
const intlTag = () => (currentLocale() === "en" ? "en-GB" : "id-ID");

const nf = (fractionDigits: number) =>
  new Intl.NumberFormat(intlTag(), {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });

export const minutes = (seconds: number) =>
  `${Math.round(seconds / 60)} ${currentLocale() === "en" ? "min" : "mnt"}`;
export const rupiah = (idr: number) => `Rp${nf(0).format(Math.round(idr))}`;
export const km = (metres: number) => `${nf(1).format(metres / 1000)} km`;
export const kg = (grams: number) => `${nf(2).format(grams / 1000)} kg`;

/** Sum of grams CO2 logged in the current calendar month. */
export const carbonThisMonthG = (log: CarbonLogEntry[]): number => {
  const now = new Date();
  return log
    .filter((entry) => {
      const at = new Date(entry.at);
      return at.getMonth() === now.getMonth() && at.getFullYear() === now.getFullYear();
    })
    .reduce((sum, entry) => sum + entry.g, 0);
};

/** An ISO timestamp → "30 Agustus 2026". Returns null for anything unparseable,
 *  so a malformed upstream date renders as nothing rather than "Invalid Date". */
export const surveyDate = (iso: string): string | null => {
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return null;
  return at.toLocaleDateString(intlTag(), { day: "numeric", month: "long", year: "numeric" });
};

/** The four-stat summary line above the itinerary timeline. */
export const routeSummary = (route: Route): string[] => [
  minutes(route.total_time_s),
  rupiah(route.total_fare_idr),
  km(route.total_distance_m),
  translate(currentLocale(), "route.transfers", route.transfers),
];

/** Compact form for the inline card inside an agent reply. */
export const routeCardMeta = (route: Route): string =>
  `${minutes(route.total_time_s)} · ${rupiah(route.total_fare_idr)} · ${route.legs.length} leg`;

/** Which map-category family a route's own accent should echo, mirroring
 *  bridge.ts's `routeFamily` — the transit leg if there is one (bridge.ts's
 *  default of "blue" for anything unmapped stays the fallback here too),
 *  since a walk-then-bus itinerary reads as "a bus trip" overall. */
export const routePrimaryFamily = (route: Route): "krl" | "gold" | "blue" | "walk" => {
  const transitLeg = route.legs.find((leg) => (leg.transit_mode ?? leg.mode) !== "walk");
  const key = transitLeg?.transit_mode ?? transitLeg?.mode ?? route.legs[0]?.mode;
  const family = key ? MODE_KEY[key] : undefined;
  return family === "krl" || family === "gold" || family === "walk" ? family : "blue";
};

export const routeTitle = (route: Route): string => {
  const first = route.legs[0];
  const last = route.legs[route.legs.length - 1];
  if (!first || !last) return currentLocale() === "en" ? "Route" : "Rute";
  return `${first.from_name ?? first.from_node} → ${last.to_name ?? last.to_node}`;
};
