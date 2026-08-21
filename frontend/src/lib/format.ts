import type { Route } from "./types";

/** Indonesian number conventions: comma decimal, dot thousands. */
const nf = (fractionDigits: number) =>
  new Intl.NumberFormat("id-ID", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });

export const minutes = (seconds: number) => `${Math.round(seconds / 60)} MNT`;
export const rupiah = (idr: number) => `RP${nf(0).format(Math.round(idr))}`;
export const km = (metres: number) => `${nf(1).format(metres / 1000)} KM`;
export const kg = (grams: number) => `${nf(2).format(grams / 1000)} kg`;

/** The four-stat summary line above the itinerary timeline. */
export const routeSummary = (route: Route): string[] => [
  minutes(route.total_time_s),
  rupiah(route.total_fare_idr),
  km(route.total_distance_m),
  `${route.transfers} TRANSFER`,
];

/** Compact form for the inline card inside an agent reply. */
export const routeCardMeta = (route: Route): string =>
  `${minutes(route.total_time_s)} · ${rupiah(route.total_fare_idr)} · ${route.legs.length} LEG`;
