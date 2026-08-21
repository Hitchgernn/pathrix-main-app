import { routeCardMeta } from "../lib/format";
import type { Route } from "../lib/types";
import { useStore } from "../store";

interface RouteCardProps {
  route: Route | null;
}

/** The route affordance attached to an agent reply. Tapping it opens the full
 *  itinerary — the reply itself stays prose, never an instruction to parse. */
export function RouteCard({ route }: RouteCardProps) {
  const openPanel = useStore((s) => s.openPanel);

  const title = "Malioboro → Candi Prambanan";
  const meta = route ? routeCardMeta(route) : "51 MNT · RP63.000 · 5 LEG";

  return (
    <button
      onClick={() => openPanel("route")}
      className="hairline mt-[9px] flex w-full items-center gap-[9px] pt-[11px] text-left"
    >
      <span className="h-[26px] w-1 flex-none rounded-[1px] bg-teal" />
      <span className="flex flex-col gap-[2px]">
        <span className="text-[15px] font-semibold tracking-[-.01em]">{title}</span>
        <span className="kicker text-ink-55">{meta}</span>
      </span>
    </button>
  );
}
