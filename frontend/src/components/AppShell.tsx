import { snapPoints, useWindowSize } from "../lib/useWindowSize";
import { useStore } from "../store";
import { AgentSheet } from "./AgentSheet";
import { MapCanvas } from "./MapCanvas";
import { MapChrome } from "./MapChrome";
import { PanelSheet } from "./PanelSheet";
import { PoiCard } from "./PoiCard";
import { RecenterFab } from "./RecenterFab";

/** Full-bleed map with everything else floating over it. */
export function AppShell() {
  const agentSnap = useStore((s) => s.agentSnap);
  const dragH = useStore((s) => s.dragH);
  const poi = useStore((s) => s.poi);
  const { vh } = useWindowSize();

  const agentHeight = dragH ?? snapPoints(vh)[agentSnap];

  return (
    <div className="absolute inset-0">
      <MapCanvas />
      <MapChrome />
      {poi && <PoiCard />}
      <RecenterFab bottom={agentHeight + 14} />
      <AgentSheet height={agentHeight} vh={vh} />
      <PanelSheet />
    </div>
  );
}
