import { useEffect } from "react";
import { AppShell } from "./components/AppShell";
import { Dashboard } from "./components/Dashboard";
import { fetchLayers } from "./lib/api";
import { applyUICommand, fitRoute } from "./lib/bridge";
import { getMap } from "./lib/mapHandle";
import { paletteFor } from "./lib/tokens";
import { useWindowSize } from "./lib/useWindowSize";
import { AgentSocket } from "./lib/ws";
import { useStore } from "./store";

export default function App() {
  const screen = useStore((s) => s.screen);
  useWindowSize(); // also keeps the wide/narrow breakpoint in the store

  // One socket for the session. ui_commands fan out: map-affecting ones to the
  // bridge, layer visibility to the store (ARCHITECTURE.md §10.2).
  useEffect(() => {
    const socket = new AgentSocket({
      onMessage: (message) => {
        if (message.type === "ui_command") {
          const map = getMap();
          if (map) {
            const palette = paletteFor(useStore.getState().basemap);
            if (applyUICommand(map, message, palette) && message.action === "draw_route") {
              fitRoute(map, message.payload as never);
            }
          }
        }
        useStore.getState().handleServerMessage(message);
      },
    });
    socket.connect();
    useStore.getState().attachSocket(socket);

    return () => {
      useStore.getState().attachSocket(null);
      socket.close();
    };
  }, []);

  // Debounced viewport push, so "di area ini" resolves against what is on
  // screen. The map is the source of truth; the store mirrors it.
  useEffect(
    () =>
      useStore.subscribe((state, previous) => {
        if (!state.bbox || state.bbox === previous.bbox) return;
        state.socket?.pushViewport(state.bbox, state.zoom);
      }),
    [],
  );

  useEffect(() => {
    fetchLayers()
      .then(useStore.getState().setCatalogue)
      // The catalogue is presentation metadata, not a precondition for the map.
      .catch(() => undefined);
  }, []);

  return (
    <div className="fixed inset-0 overflow-hidden bg-ground font-sans text-ink">
      {screen === "dashboard" ? <Dashboard /> : <AppShell />}
    </div>
  );
}
