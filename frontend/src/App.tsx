import { useEffect } from "react";
import { AppShell } from "./components/AppShell";
import { fetchLayers } from "./lib/api";
import { applyUICommand, fitRoute } from "./lib/bridge";
import { getMap } from "./lib/mapHandle";
import { paletteFor } from "./lib/tokens";
import { useWindowSize } from "./lib/useWindowSize";
import { AgentSocket } from "./lib/ws";
import { applyTheme, useStore } from "./store";

export default function App() {
  useWindowSize(); // also keeps the wide/narrow breakpoint in the store
  const wide = useStore((s) => s.wide);
  const mapMounted = useStore((s) => s.mapMounted);

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

  // The persisted locale restores into the store on boot, but <html lang> is
  // whatever index.html shipped, so a reload in English was announcing itself
  // as Indonesian to every screen reader. Only setLocale used to touch it.
  useEffect(() => {
    document.documentElement.lang = useStore.getState().locale;
  }, []);

  // The pre-paint script in index.html has already stamped data-theme; this
  // syncs the basemap to it and keeps both following the OS while the pref is
  // "system", so changing appearance in system settings updates a tab that is
  // already open.
  useEffect(() => {
    const { theme } = useStore.getState();
    applyTheme(theme, useStore.setState);
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (useStore.getState().theme === "system") {
        applyTheme("system", useStore.setState);
      }
    };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    fetchLayers()
      .then(useStore.getState().setCatalogue)
      // The catalogue is presentation metadata, not a precondition for the map.
      .catch(() => undefined);
  }, []);

  // On wide viewports the map is in frame under every screen, so it is mounted
  // once the browser is idle rather than on the first visit to Explore. The
  // first paint still has no MapLibre in it — which is what the §14 load budget
  // actually asks for — but the desktop layout is not missing its base layer.
  useEffect(() => {
    if (!wide || mapMounted) return;
    const mount = () => useStore.setState({ mapMounted: true });
    const idle = window.requestIdleCallback;
    if (idle) {
      const handle = idle(mount, { timeout: 2000 });
      return () => window.cancelIdleCallback?.(handle);
    }
    const timer = window.setTimeout(mount, 600);
    return () => window.clearTimeout(timer);
  }, [wide, mapMounted]);

  return (
    <div className="fixed inset-0 overflow-hidden bg-ground font-sans text-ink">
      <AppShell />
    </div>
  );
}
