import { X } from "lucide-react";
import { useT, type MessageKey } from "../i18n";
import { NAV_W, NAV_W_COLLAPSED } from "../lib/tokens";
import { useWindowSize } from "../lib/useWindowSize";
import { useStore } from "../store";
import { LayerToggleList } from "./LayerToggleList";
import { RouteDetail } from "./RouteDetail";
import { SustainabilityStat } from "./SustainabilityStat";

const TITLE: Record<"layers" | "route" | "sustain", MessageKey> = {
  layers: "panel.layers",
  route: "panel.route",
  sustain: "panel.sustain",
};

interface PanelSheetProps {
  /** Room to leave for the floating tab bar on narrow viewports. */
  bottomInset?: number;
}

/** The map's second surface — layers, route detail, sustainability.
 *
 *  Deliberately a sheet and not a permanent sidebar: a 390px sidebar is how
 *  existing WebGIS tools lose the users this product exists for
 *  (ARCHITECTURE.md §10.3).
 */
export function PanelSheet({ bottomInset = 0 }: PanelSheetProps) {
  const panel = useStore((s) => s.panel);
  const panelSnap = useStore((s) => s.panelSnap);
  const cyclePanelSnap = useStore((s) => s.cyclePanelSnap);
  const closePanel = useStore((s) => s.closePanel);
  const wide = useStore((s) => s.wide);
  const navCollapsed = useStore((s) => s.navCollapsed);
  const { vh } = useWindowSize();
  const t = useT();

  if (!panel) return null;

  const panelH = Math.round(vh * (panelSnap === "full" ? 0.76 : 0.5));

  const shellStyle = wide
    ? {
        left: (navCollapsed ? NAV_W_COLLAPSED : NAV_W) + 20,
        top: 130,
        bottom: 92,
        width: 360,
        borderRadius: 22,
        boxShadow: "var(--shadow-float)",
      }
    : {
        left: 8,
        right: 8,
        bottom: bottomInset,
        height: panelH,
        borderRadius: "var(--radius-sheet)",
        boxShadow: "var(--shadow-sheet)",
        // Height, not transform, on purpose: the sheet's height *is* the snap
        // state, and the composer must stay pinned to the bottom edge while
        // the content above it reflows. A transform would slide the whole
        // sheet off-screen instead of resizing it.
        transition: "height .3s var(--ease-out-expo)",
      };

  return (
    <section
      aria-label={t(TITLE[panel])}
      className="absolute z-[45] flex animate-pxrise flex-col overflow-hidden bg-surface ring-1 ring-line"
      style={shellStyle}
    >
      {!wide && (
        <button
          onClick={cyclePanelSnap}
          aria-label={t(panelSnap === "full" ? "panel.shrink" : "panel.expand")}
          className="flex flex-none justify-center pb-1 pt-[10px]"
        >
          <span className="h-1 w-[38px] rounded-[2px] bg-line-strong" />
        </button>
      )}

      <div className="flex flex-none items-start justify-between gap-3 px-5 pb-3 pt-4">
        <h2 className="title-lg min-w-0 flex-1">{t(TITLE[panel])}</h2>
        <button
          onClick={closePanel}
          aria-label={t("panel.close")}
          className="-mr-2 flex-none rounded-full p-2 text-ink-4 transition-colors hover:bg-surface-2 hover:text-ink"
        >
          <X size={18} strokeWidth={2} />
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-[22px]">
        {panel === "layers" && <LayerToggleList />}
        {panel === "route" && <RouteDetail />}
        {panel === "sustain" && <SustainabilityStat />}
      </div>
    </section>
  );
}
