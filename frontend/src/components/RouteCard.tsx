import { ChevronRight, Navigation } from "lucide-react";
import { useT } from "../i18n";
import { focusRouteIn3d } from "../lib/actions";
import { routeCardMeta, routePrimaryFamily, routeTitle } from "../lib/format";
import type { Route } from "../lib/types";
import { useStore } from "../store";

interface RouteCardProps {
  route: Route | null;
}

const SAMPLE_TITLE = "Malioboro → Candi Prambanan";

/** docs/DESIGN.md's Route Card spec: mode is a colored 4px vertical, in the
 *  map category palette — never a second icon system. */
const FAMILY_COLOR: Record<"krl" | "gold" | "blue" | "walk", string> = {
  krl: "var(--color-map-krl)",
  gold: "var(--color-map-gold)",
  blue: "var(--color-map-blue)",
  walk: "var(--color-map-walk)",
};

/** The route affordance attached to an agent reply. Tapping it opens the full
 *  itinerary — the reply itself stays prose, never an instruction to parse. */
export function RouteCard({ route }: RouteCardProps) {
  const openPanel = useStore((s) => s.openPanel);
  const title = route ? routeTitle(route) : SAMPLE_TITLE;
  const saved = useStore((s) => s.savedRoutes.some((r) => r.id === title));
  const toggleSavedRoute = useStore((s) => s.toggleSavedRoute);
  const t = useT();

  const meta = route ? routeCardMeta(route) : "51 MNT · RP63.000 · 5 LEG";
  const family = route ? routePrimaryFamily(route) : "blue";

  return (
    <div className="mt-[10px] w-full overflow-hidden rounded-card bg-surface ring-1 ring-line">
      <button
        onClick={() => openPanel("route")}
        className="flex w-full items-center gap-3 px-[14px] py-[13px] text-left transition-colors hover:bg-surface-2"
      >
        <span
          className="h-[32px] w-[3px] flex-none rounded-[2px]"
          style={{ backgroundColor: FAMILY_COLOR[family] }}
        />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[15px] font-semibold leading-tight tracking-[-.01em]">
            {title}
          </span>
          <span className="figure mt-[5px] block text-[12px] text-ink-3">{meta}</span>
        </span>
        <ChevronRight size={17} strokeWidth={2} className="flex-none text-ink-4" />
      </button>

      {route && (
        <button
          onClick={() => focusRouteIn3d(route)}
          className="flex w-full items-center gap-2 border-t border-line px-[13px] py-[10px] text-left text-[13px] font-semibold text-ink-2 transition-colors hover:bg-surface-2"
        >
          <Navigation size={15} strokeWidth={2} />
          {t("route.goTo")}
        </button>
      )}

      <button
        onClick={() =>
          toggleSavedRoute({
            id: title,
            title,
            prompt: title,
            meta,
            savedAt: Date.now(),
          })
        }
        className={`w-full border-t border-line px-[13px] py-[10px] text-left text-[13px] font-semibold transition-colors ${
          saved ? "text-ink" : "text-ink-2 hover:bg-surface-2"
        }`}
      >
        {t(saved ? "route.savedHere" : "route.saveThis")}
      </button>
    </div>
  );
}
