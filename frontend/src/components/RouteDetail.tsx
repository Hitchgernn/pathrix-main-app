import { minutes, routeSummary, rupiah } from "../lib/format";
import { useT } from "../i18n";
import { SAMPLE_ALTERNATIVE, SAMPLE_LEGS, SAMPLE_SUMMARY_KEYS } from "../lib/sample";
import { MODE_KEY, paletteFor } from "../lib/tokens";
import { useStore } from "../store";

interface LegRow {
  mode: string;
  colorKey: "walk" | "gold" | "krl" | "blue";
  title: string;
  sub: string;
  detail: string | null;
}

/** Backend EdgeType → the design's four visual mode families. */
const colorKeyFor = (mode: string): LegRow["colorKey"] => {
  const key = MODE_KEY[mode] ?? "blue";
  return key === "walk" ? "walk" : key === "gold" ? "gold" : key === "krl" ? "krl" : "blue";
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
  const rows: LegRow[] = route
    ? route.legs.map((leg) => ({
        mode: leg.mode.toUpperCase(),
        colorKey: colorKeyFor(leg.mode),
        title: `${leg.from_node} → ${leg.to_node}`,
        sub: `${minutes(leg.time_s)} · ${rupiah(leg.fare_idr)}`,
        detail: null,
      }))
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

      {rows.map((row, index) => {
        const open = legOpen === index;
        const color = palette[row.colorKey === "krl" ? "krl" : row.colorKey];
        const walk = row.colorKey === "walk";
        return (
          <button
            key={index}
            onClick={() => setLegOpen(open ? null : index)}
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
                <span className="body-13 mt-[5px] block animate-pxrise rounded-card border border-line bg-surface px-[14px] py-3 text-ink-2">
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
