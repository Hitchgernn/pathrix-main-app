import { RAIL_W } from "../lib/tokens";
import { useWindowSize } from "../lib/useWindowSize";
import { useStore } from "../store";
import { LayerToggleList } from "./LayerToggleList";
import { RouteDetail } from "./RouteDetail";
import { SustainabilityStat } from "./SustainabilityStat";

const KICKER = { layers: "LAYERS", route: "ROUTE DETAIL", sustain: "SUSTAINABILITY" } as const;
const TITLE = {
  layers: "Layer Tematik",
  route: "Malioboro → Prambanan",
  sustain: "Jejak Karbon",
} as const;

/** The second sheet — layers, route detail, sustainability. Deliberately a
 *  sheet and not a sidebar: a 390px sidebar is how existing WebGIS tools lose
 *  the users this product exists for (ARCHITECTURE.md §10.3). */
export function PanelSheet() {
  const panel = useStore((s) => s.panel);
  const panelSnap = useStore((s) => s.panelSnap);
  const cyclePanelSnap = useStore((s) => s.cyclePanelSnap);
  const closePanel = useStore((s) => s.closePanel);
  const wide = useStore((s) => s.wide);
  const { vw, vh } = useWindowSize();

  if (!panel) return null;

  const panelW = Math.max(300, Math.min(368, vw - RAIL_W - 14 - 190));
  const panelH = Math.round(vh * (panelSnap === "full" ? 0.78 : 0.52));

  const shellStyle = wide
    ? {
        left: RAIL_W + 14,
        top: 62,
        bottom: 16,
        width: panelW,
        borderRadius: "var(--radius-card)",
        boxShadow: "var(--shadow-card)",
      }
    : {
        left: 0,
        right: 0,
        bottom: 96,
        height: panelH,
        borderRadius: "20px 20px 0 0",
        boxShadow: "var(--shadow-sheet)",
        transition: "height .26s var(--ease-snap)",
      };

  return (
    <div className="surface-sheet absolute z-40 flex animate-pxrise flex-col" style={shellStyle}>
      <div
        onClick={cyclePanelSnap}
        className="flex flex-none cursor-pointer justify-center pb-1 pt-[10px]"
      >
        <div className="h-1 w-[38px] rounded-[2px] bg-line" />
      </div>

      <div className="flex flex-none items-start justify-between gap-3 px-5 pb-3 pt-1">
        <div className="min-w-0 flex-1">
          <div className="kicker text-ink-55">{KICKER[panel]}</div>
          <div className="title-lg mt-[7px]">{TITLE[panel]}</div>
        </div>
        <button
          onClick={closePanel}
          className="kicker flex-none whitespace-nowrap px-[2px] py-1 text-ink-50"
        >
          CLOSE
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-[22px]">
        {panel === "layers" && <LayerToggleList />}
        {panel === "route" && <RouteDetail />}
        {panel === "sustain" && <SustainabilityStat />}
      </div>
    </div>
  );
}
