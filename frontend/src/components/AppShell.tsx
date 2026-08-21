import { snapPoints, useWindowSize } from "../lib/useWindowSize";
import { useStore } from "../store";
import { AgentSheet } from "./AgentSheet";
import { MapCanvas } from "./MapCanvas";
import { MapChrome } from "./MapChrome";
import { PanelSheet } from "./PanelSheet";
import { PoiCard } from "./PoiCard";
import { RecenterFab } from "./RecenterFab";
import { RouteOverlay } from "./RouteOverlay";

/** Full-bleed map with everything else floating over it. */
export function AppShell() {
  const agentSnap = useStore((s) => s.agentSnap);
  const dragH = useStore((s) => s.dragH);
  const poi = useStore((s) => s.poi);
  const lastRoute = useStore((s) => s.lastRoute);
  const { vh } = useWindowSize();

  const agentHeight = dragH ?? snapPoints(vh)[agentSnap];

  // The authored schematic stands in only while no real route is drawable —
  // once the bridge has real geometry on the map, two itineraries would show.
  const drawable = lastRoute?.legs.some((leg) => leg.coordinates.length >= 2) ?? false;

  return (
    <div className="absolute inset-0">
      <MapCanvas />
      {!drawable && <RouteOverlay />}
      <MapChrome />
      {poi && <PoiCard />}
      <RecenterFab bottom={agentHeight + 14} />
      <AgentSheet height={agentHeight} vh={vh} />
      <PanelSheet />
    </div>
  );
}
