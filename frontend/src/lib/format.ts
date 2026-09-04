import { currentLocale } from "../i18n";
import { translate } from "../i18n";
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
