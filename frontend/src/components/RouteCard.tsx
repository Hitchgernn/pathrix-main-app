import { ChevronRight } from "lucide-react";
import { routeCardMeta } from "../lib/format";
import type { Route } from "../lib/types";
import { useStore } from "../store";

interface RouteCardProps {
  route: Route | null;
}

const SAMPLE_TITLE = "Malioboro → Candi Prambanan";

/** The route affordance attached to an agent reply. Tapping it opens the full
 *  itinerary — the reply itself stays prose, never an instruction to parse. */
export function RouteCard({ route }: RouteCardProps) {
  const openPanel = useStore((s) => s.openPanel);
  const saved = useStore((s) => s.savedRoutes.some((r) => r.id === SAMPLE_TITLE));
  const toggleSavedRoute = useStore((s) => s.toggleSavedRoute);

  const meta = route ? routeCardMeta(route) : "51 MNT · RP63.000 · 5 LEG";

  return (
    <div className="mt-[10px] w-full overflow-hidden rounded-card bg-surface ring-1 ring-line">
      <button
        onClick={() => openPanel("route")}
        className="flex w-full items-center gap-[11px] px-[13px] py-[12px] text-left transition-colors hover:bg-surface-2"
      >
        <span className="h-[30px] w-[3px] flex-none rounded-[2px] bg-ink" />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[15px] font-semibold tracking-[-.01em]">
            {SAMPLE_TITLE}
          </span>
          <span className="figure mt-[4px] block text-[12px] text-ink-3">{meta}</span>
        </span>
        <ChevronRight size={17} strokeWidth={2} className="flex-none text-ink-4" />
      </button>

      <button
        onClick={() =>
          toggleSavedRoute({
            id: SAMPLE_TITLE,
            title: SAMPLE_TITLE,
            prompt: SAMPLE_TITLE,
            meta,
            savedAt: Date.now(),
          })
        }
        className={`w-full border-t border-line px-[13px] py-[10px] text-left text-[13px] font-semibold transition-colors ${
          saved ? "text-ink" : "text-ink-2 hover:bg-surface-2"
        }`}
      >
        {saved ? "Tersimpan di perangkat ini" : "Simpan rute ini"}
      </button>
    </div>
  );
}
