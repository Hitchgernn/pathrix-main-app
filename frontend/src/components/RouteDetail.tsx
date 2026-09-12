import { minutes, routeSummary, rupiah } from "../lib/format";
import { useT } from "../i18n";
import { goToPlace } from "../lib/actions";
import { placeFromRouteStop } from "../lib/places";
import { SAMPLE_ALTERNATIVE, SAMPLE_LEGS, SAMPLE_SUMMARY_KEYS } from "../lib/sample";
import { MODE_KEY, paletteFor } from "../lib/tokens";
import type { RouteLeg } from "../lib/types";
import { useStore } from "../store";

interface LegRow {
  mode: string;
  colorKey: "walk" | "gold" | "krl" | "blue";
  title: string;
  sub: string;
  detail: string | null;
}

/** Backend EdgeType → the design's four visual mode families. */
const colorKeyFor = (leg: RouteLeg): LegRow["colorKey"] => {
  const key = MODE_KEY[leg.transit_mode ?? leg.mode] ?? "blue";
  return key === "walk" ? "walk" : key === "gold" ? "gold" : key === "krl" ? "krl" : "blue";
};

const sourceMetadata = (leg: RouteLeg) => {
  const effective = leg.source?.match(/effective_from=([^;]+)/)?.[1];
  const freshness = leg.source?.match(/freshness_status=([^;]+)/)?.[1];
  return { effective, freshness };
};

/** Itinerary timeline. Every leg is expandable, because the modelling choices
 *  behind a number (headway not timetable, negotiated fare not tariff) are the
 *  answer to "why should I trust this" — ARCHITECTURE.md §7.1. */
export function RouteDetail() {
  const basemap = useStore((s) => s.basemap);
  const legOpen = useStore((s) => s.legOpen);
  const setLegOpen = useStore((s) => s.setLegOpen);
  const route = useStore((s) => s.lastRoute);
  const palette = paletteFor(basemap);
  const t = useT();

  const summary = route ? routeSummary(route) : SAMPLE_SUMMARY_KEYS.map((key) => t(key));
  const stops = (route?.stops ?? [])
    .map((stop) => ({ stop, place: placeFromRouteStop(stop) }))
    .filter((item) => item.place !== null);
  const rows: LegRow[] = route
    ? route.legs.map((leg) => {
        const { effective, freshness } = sourceMetadata(leg);
        const detail = [
          leg.operator,
          effective ? t("transit.effectiveFrom", effective) : null,
          freshness ? t("transit.freshness", freshness) : null,
        ].filter(Boolean);
        return {
          mode: (leg.service_name ?? leg.transit_mode ?? leg.mode).toUpperCase(),
          colorKey: colorKeyFor(leg),
          title: `${leg.from_name ?? leg.from_node} → ${leg.to_name ?? leg.to_node}`,
          sub: `${minutes(leg.time_s)} · ${rupiah(leg.fare_idr)}`,
          detail: detail.length ? detail.join(" · ") : null,
        };
      })
    : SAMPLE_LEGS.map((leg) => ({
        mode: t(leg.modeKey),
        colorKey: leg.key,
        title: leg.title,
        sub: t(leg.subKey),
        detail: t(leg.detailKey),
      }));

  return (
    <div>
      <div className="flex flex-wrap gap-x-5 gap-y-[6px] pb-4">
        {summary.map((stat: string) => (
          <span key={stat} className="figure text-[12px] text-ink-3">
            {stat}
          </span>
        ))}
      </div>

      {stops.length > 0 && (
        <section className="pb-4" aria-labelledby="route-stops-heading">
          <h3 id="route-stops-heading" className="label-sm pb-1 text-ink-2">
            {t("transit.stops")}
          </h3>
          <ol>
            {stops.map(({ stop, place }, index) => {
              if (!place) return null;
              const service = stop.routes?.find((item) => item.next_departures?.length) ?? stop.routes?.[0];
              const departures = service?.next_departures ?? stop.schedule?.next_departures ?? [];
              const headway =
                service?.headway_min_minutes ?? service?.headway_min ?? stop.schedule?.headway_min;
              const freshness =
                service?.freshness_status ??
                stop.freshness_status ??
                stop.schedule?.freshness_status;
              const schedule = departures.length
                ? t("transit.nextDepartures", departures.slice(0, 3).join(" · "))
                : headway != null
                  ? t("transit.headway", headway)
                  : null;

              return (
                <li key={String(stop.external_id ?? stop.id)} className="hairline">
                  <button
                    type="button"
                    onClick={() => goToPlace(place)}
                    aria-label={t("transit.openStop", place.name)}
                    className="flex w-full min-w-0 items-start gap-3 rounded-control px-1 py-[11px] text-left transition-colors hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink"
                  >
                    <span className="figure mt-[2px] w-6 flex-none text-[12px] text-ink-3">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="title-row block break-words">{place.name}</span>
                      {(service?.name || schedule) && (
                        <span className="body-13 mt-[3px] block break-words text-ink-2">
                          {[service?.name, schedule].filter(Boolean).join(" · ")}
                        </span>
                      )}
                      {freshness && (
                        <span className="body-13 mt-[2px] block break-words text-ink-3">
                          {t("transit.freshness", freshness)}
                        </span>
                      )}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        </section>
      )}

      {rows.map((row, index) => {
        const open = legOpen === index;
        const color = palette[row.colorKey === "krl" ? "krl" : row.colorKey];
        const walk = row.colorKey === "walk";
        return (
          <button
            key={index}
            type="button"
            onClick={() => setLegOpen(open ? null : index)}
            aria-expanded={open}
            aria-controls={row.detail ? `route-leg-detail-${index}` : undefined}
            className="hairline flex w-full gap-[13px] py-[15px] text-left"
          >
            <span
              className="w-1 flex-none self-stretch rounded-[1px]"
              style={{ background: color, opacity: walk ? 0.38 : 1, minHeight: 44 }}
            />
            <span className="flex min-w-0 flex-1 flex-col gap-[5px]">
              <span className="flex items-center gap-[9px]">
                <span className="label-sm" style={{ color: walk ? "rgba(23,23,26,.64)" : color }}>
                  {row.mode}
                </span>
                <span className="figure text-[12px] text-ink-3">
                  {String(index + 1).padStart(2, "0")}
                </span>
              </span>
              <span className="title-row" style={{ textWrap: "pretty" }}>
                {row.title}
              </span>
              <span className="body-13 text-ink-2">{row.sub}</span>
              {open && row.detail && (
                <span
                  id={`route-leg-detail-${index}`}
                  className="body-13 mt-[5px] block animate-pxrise rounded-card border border-line bg-surface px-[14px] py-3 text-ink-2"
                >
                  {row.detail}
                </span>
              )}
            </span>
          </button>
        );
      })}

      {/* The cheaper option is offered alongside, never swapped in silently. */}
      <div className="hairline flex gap-[13px] pt-4">
        <span className="w-1 flex-none self-stretch rounded-[1px] bg-ink" />
        <div>
          <div className="label-sm text-ink-2">{t(SAMPLE_ALTERNATIVE.labelKey)}</div>
          <div className="title-row mt-[6px]">{t(SAMPLE_ALTERNATIVE.titleKey)}</div>
          <div className="body-13 mt-[3px] text-ink-2">{t(SAMPLE_ALTERNATIVE.subKey)}</div>
        </div>
      </div>
    </div>
  );
}
