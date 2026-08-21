import { minutes, routeSummary, rupiah } from "../lib/format";
import { SAMPLE_ALTERNATIVE, SAMPLE_LEGS, SAMPLE_ROUTE_SUMMARY } from "../lib/sample";
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

  const summary = route ? routeSummary(route) : SAMPLE_ROUTE_SUMMARY;
  const rows: LegRow[] = route
    ? route.legs.map((leg) => ({
        mode: leg.mode.toUpperCase(),
        colorKey: colorKeyFor(leg.mode),
        title: `${leg.from_node} → ${leg.to_node}`,
        sub: `${minutes(leg.time_s)} · ${rupiah(leg.fare_idr)}`,
        detail: null,
      }))
    : SAMPLE_LEGS.map((leg) => ({
        mode: leg.mode,
        colorKey: leg.key,
        title: leg.title,
        sub: leg.sub,
        detail: leg.detail,
      }));

  return (
    <div>
      <div className="flex flex-wrap gap-x-5 gap-y-[6px] pb-4">
        {summary.map((stat) => (
          <span key={stat} className="kicker text-ink-55">
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
                <span className="kicker" style={{ color: walk ? "rgba(16,30,42,.5)" : color }}>
                  {row.mode}
                </span>
                <span className="kicker text-ink-40">
                  {String(index + 1).padStart(2, "0")}
                </span>
              </span>
              <span className="title-row" style={{ textWrap: "pretty" }}>
                {row.title}
              </span>
              <span className="body-13 text-ink-66">{row.sub}</span>
              {open && row.detail && (
                <span className="body-13 mt-[5px] block animate-pxrise rounded-card border border-line bg-surface px-[14px] py-3 text-ink-66">
                  {row.detail}
                </span>
              )}
            </span>
          </button>
        );
      })}

      {/* The cheaper option is offered alongside, never swapped in silently. */}
      <div className="hairline flex gap-[13px] pt-4">
        <span className="w-1 flex-none self-stretch rounded-[1px] bg-blue" />
        <div>
          <div className="kicker text-blue">{SAMPLE_ALTERNATIVE.kicker}</div>
          <div className="title-row mt-[6px]">{SAMPLE_ALTERNATIVE.title}</div>
          <div className="body-13 mt-[3px] text-ink-66">{SAMPLE_ALTERNATIVE.sub}</div>
        </div>
      </div>
    </div>
  );
}
