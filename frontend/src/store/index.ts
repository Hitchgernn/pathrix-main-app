import { create } from "zustand";
import type {
  BBox,
  CarbonResult,
  ChatMessage,
  LayerMeta,
  Route,
  ServerMessage,
} from "../lib/types";
import type { Basemap } from "../lib/tokens";
import type { Place, RecentEntry, SavedRoute } from "../lib/places";
import { LAYER_ROWS, QUICK, REPLY_GENERIC, REPLY_ROUTE, SEED_RECENTS } from "../lib/sample";
import { demoKindFor, runScript, type DemoKind } from "../lib/demoAgent";
import type { AgentSocket } from "../lib/ws";
import {
  capRecents,
  clearPersisted,
  loadPersisted,
  savePersisted,
  type LocationPermission,
  type PersistedState,
  type Profile,
} from "./persist";

export type Tab = "home" | "explore" | "saved" | "agent" | "profile";
export type AgentSnap = "peek" | "half" | "full";
export type PanelName = "layers" | "route" | "sustain";
export type PanelSnap = "half" | "full";

/** Kraton-centred default camera; the map owns the real one from first render. */
export const YOGYA_CENTER: [number, number] = [110.3695, -7.7956];
export const YOGYA_ZOOM = 12;

/** The scripted agent's current step, or null when it is not running. Module
 *  state rather than store state only for the canceller, which is not UI. */
let cancelDemo: (() => void) | null = null;

const initialLayers = new Set(LAYER_ROWS.filter((l) => l.on).map((l) => l.id));

interface MapSlice {
  bbox: BBox | null;
  zoom: number;
  center: [number, number];
  basemap: Basemap;
  /** Where the browser says the user is, once they allow it. */
  userCoord: [number, number] | null;
  /** MapLibre owns camera state; the store mirrors it. Never bind back. */
  setCamera(center: [number, number], zoom: number, bbox: BBox): void;
  setBasemap(basemap: Basemap): void;
  setUserCoord(coord: [number, number] | null): void;
}

interface LayerSlice {
  active: Set<string>;
  catalogue: LayerMeta[];
  toggleLayer(id: string, on?: boolean): void;
  setLayers(ids: string[]): void;
  setCatalogue(catalogue: LayerMeta[]): void;
}

interface AgentSlice {
  messages: ChatMessage[];
  streaming: boolean;
  lastRoute: Route | null;
  lastCarbon: CarbonResult | null;
  /** Set when the backend has no LLM provider wired — the UI then runs on the
   *  design's sample replies rather than showing a dead input. */
  offline: boolean;
  /** While the scripted agent is running: which script, and how far in. Null
   *  once a real provider is answering, since progress will come from the
   *  backend rather than from a timer. */
  demoKind: DemoKind | null;
  demoStep: number;
  socket: AgentSocket | null;
  attachSocket(socket: AgentSocket | null): void;
  ask(text: string): void;
  handleServerMessage(message: ServerMessage): void;
}

interface UiSlice {
  tab: Tab;
  /** True once Explore has been opened. MapLibre is kept out of the first paint
   *  (ARCHITECTURE.md §14) but never unmounted afterwards — tearing down a GL
   *  context on every tab switch is far more expensive than hiding it. */
  mapMounted: boolean;
  agentSnap: AgentSnap;
  dragH: number | null;
  panel: PanelName | null;
  panelSnap: PanelSnap;
  legOpen: number | null;
  selectedPlace: Place | null;
  searchOpen: boolean;
  navCollapsed: boolean;
  input: string;
  wide: boolean;
  setTab(tab: Tab): void;
  setAgentSnap(snap: AgentSnap): void;
  setDragH(height: number | null): void;
  cycleAgentSnap(): void;
  openPanel(panel: PanelName): void;
  togglePanel(panel: PanelName): void;
  closePanel(): void;
  cyclePanelSnap(): void;
  setLegOpen(index: number | null): void;
  selectPlace(place: Place | null): void;
  setSearchOpen(open: boolean): void;
  setNavCollapsed(collapsed: boolean): void;
  setInput(value: string): void;
  setWide(wide: boolean): void;
}

interface PersistSlice extends PersistedState {
  setProfile(profile: Partial<Profile>): void;
  toggleSavedPlace(place: Place): void;
  isSaved(id: string): boolean;
  toggleSavedRoute(route: SavedRoute): void;
  isRouteSaved(id: string): boolean;
  pushRecent(entry: Omit<RecentEntry, "at">): void;
  setLocationPermission(permission: LocationPermission): void;
  setOnboarded(onboarded: boolean): void;
  resetLocalData(): void;
}

export type Store = MapSlice & LayerSlice & AgentSlice & UiSlice & PersistSlice;

const looksLikeRoute = (text: string) => /prambanan|malioboro|→|ke\s/i.test(text);

const persisted = loadPersisted();

/** Snapshot only the persisted keys, so a camera move never writes to disk. */
const persistNow = (state: Store): void =>
  savePersisted({
    profile: state.profile,
    savedPlaces: state.savedPlaces,
    savedRoutes: state.savedRoutes,
    recents: state.recents,
    locationPermission: state.locationPermission,
    onboarded: state.onboarded,
  });

export const useStore = create<Store>()((set, get) => ({
  // ---- map ----------------------------------------------------------------
  bbox: null,
  zoom: YOGYA_ZOOM,
  center: YOGYA_CENTER,
  basemap: "street",
  userCoord: null,
  setCamera: (center, zoom, bbox) => set({ center, zoom, bbox }),
  setBasemap: (basemap) => set({ basemap }),
  setUserCoord: (userCoord) => set({ userCoord }),

  // ---- layers -------------------------------------------------------------
  active: initialLayers,
  catalogue: [],
  toggleLayer: (id, on) =>
    set((s) => {
      const next = new Set(s.active);
      const shouldBeOn = on ?? !next.has(id);
      if (shouldBeOn) next.add(id);
      else next.delete(id);
      return { active: next };
    }),
  setLayers: (ids) => set({ active: new Set(ids) }),
  setCatalogue: (catalogue) => set({ catalogue }),

  // ---- agent --------------------------------------------------------------
  messages: [],
  streaming: false,
  lastRoute: null,
  lastCarbon: null,
  offline: false,
  demoKind: null,
  demoStep: 0,
  socket: null,
  attachSocket: (socket) => set({ socket }),

  ask: (text) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    const { socket, bbox, zoom } = get();

    set((s) => ({
      messages: s.messages.concat([{ who: "user", text: trimmed }]),
      input: "",
      streaming: true,
      agentSnap: s.agentSnap === "peek" ? "half" : s.agentSnap,
      panel: null,
      searchOpen: false,
    }));
    get().pushRecent({ title: trimmed, prompt: trimmed });

    cancelDemo?.();
    cancelDemo = null;
    set({ demoKind: null, demoStep: 0 });

    const sent = socket !== null && bbox !== null && socket.ask(trimmed, { bbox, zoom });
    if (sent) return;

    // No socket, or no camera yet: fall back to the design's scripted reply so
    // the screens stay inspectable before the LLM provider lands (§15.1).
    get().handleServerMessage({
      type: "error",
      code: "llm_unavailable",
      message: "Chat is unavailable right now.",
    });
  },

  handleServerMessage: (message) => {
    switch (message.type) {
      case "token":
        cancelDemo?.();
        cancelDemo = null;
        set((s) => ({
          streaming: false,
          demoKind: null,
          demoStep: 0,
          messages: s.messages.concat([{ who: "agent", text: message.delta }]),
        }));
        break;

      case "ui_command":
        // Map-affecting commands are applied by lib/bridge.ts, which owns the
        // MapLibre handle. Layer visibility is store state, so it lands here.
        if (message.action === "toggle_layer") {
          const payload = message.payload as { layer_id?: string; on?: boolean };
          if (payload.layer_id) get().toggleLayer(payload.layer_id, payload.on);
        }
        break;

      case "done":
        set((s) => {
          const messages = s.messages.slice();
          const last = messages[messages.length - 1];
          if (message.route && last && last.who === "agent") {
            messages[messages.length - 1] = { ...last, route: message.route };
          }
          return {
            streaming: false,
            messages,
            lastRoute: message.route ?? s.lastRoute,
            lastCarbon: message.carbon ?? s.lastCarbon,
          };
        });
        break;

      case "error": {
        const isLlmGap = message.code === "llm_unavailable";
        if (!isLlmGap) {
          set((s) => ({
            streaming: false,
            messages: s.messages.concat([{ who: "agent", text: message.message }]),
          }));
          break;
        }
        set({ offline: true });
        cancelDemo?.();
        const asked = get().messages[get().messages.length - 1];
        const question = asked ? asked.text : "";
        const kind = demoKindFor(question);
        const route = looksLikeRoute(question);

        set({ demoKind: kind, demoStep: 0 });
        cancelDemo = runScript(
          kind,
          (step) => set({ demoStep: step }),
          () => {
            cancelDemo = null;
            set((s) => ({
              streaming: false,
              demoKind: null,
              demoStep: 0,
              messages: s.messages.concat([
                { who: "agent", text: route ? REPLY_ROUTE : REPLY_GENERIC, route: null },
              ]),
            }));
          },
        );
        break;
      }
    }
  },

  // ---- ui -----------------------------------------------------------------
  tab: "home",
  mapMounted: false,
  agentSnap: "peek",
  dragH: null,
  panel: null,
  panelSnap: "half",
  legOpen: null,
  selectedPlace: null,
  searchOpen: false,
  navCollapsed: false,
  input: "",
  wide: false,

  setTab: (tab) =>
    set((s) => ({
      tab,
      mapMounted: s.mapMounted || tab === "explore",
      // Leaving Explore closes what was floating over the map, so coming back
      // shows the map rather than a stale sheet.
      panel: tab === "explore" ? s.panel : null,
      searchOpen: false,
      agentSnap: tab === "explore" ? s.agentSnap : "peek",
      dragH: null,
    })),
  setAgentSnap: (snap) =>
    set(
      snap === "full"
        ? { agentSnap: snap, dragH: null, panel: null }
        : { agentSnap: snap, dragH: null },
    ),
  setDragH: (dragH) => set({ dragH }),
  cycleAgentSnap: () => {
    const current = get().agentSnap;
    get().setAgentSnap(current === "peek" ? "half" : current === "half" ? "full" : "peek");
  },
  openPanel: (panel) =>
    set({ panel, panelSnap: "half", agentSnap: "peek", dragH: null, selectedPlace: null }),
  togglePanel: (panel) => (get().panel === panel ? set({ panel: null }) : get().openPanel(panel)),
  closePanel: () => set({ panel: null }),
  cyclePanelSnap: () => set((s) => ({ panelSnap: s.panelSnap === "full" ? "half" : "full" })),
  setLegOpen: (legOpen) => set({ legOpen, panelSnap: "full" }),
  selectPlace: (selectedPlace) =>
    set(selectedPlace ? { selectedPlace, panel: null, searchOpen: false } : { selectedPlace: null }),
  setSearchOpen: (searchOpen) => set({ searchOpen }),
  setNavCollapsed: (navCollapsed) => set({ navCollapsed }),
  setInput: (input) => set({ input }),
  setWide: (wide) => set({ wide }),

  // ---- persisted (localStorage, this device only) --------------------------
  ...persisted,

  setProfile: (profile) => {
    set((s) => ({ profile: { ...s.profile, ...profile } }));
    persistNow(get());
  },

  toggleSavedPlace: (place) => {
    set((s) => ({
      savedPlaces: s.savedPlaces.some((p) => p.id === place.id)
        ? s.savedPlaces.filter((p) => p.id !== place.id)
        : [place, ...s.savedPlaces],
    }));
    persistNow(get());
  },
  isSaved: (id) => get().savedPlaces.some((p) => p.id === id),

  toggleSavedRoute: (route) => {
    set((s) => ({
      savedRoutes: s.savedRoutes.some((r) => r.id === route.id)
        ? s.savedRoutes.filter((r) => r.id !== route.id)
        : [route, ...s.savedRoutes],
    }));
    persistNow(get());
  },
  isRouteSaved: (id) => get().savedRoutes.some((r) => r.id === id),

  pushRecent: (entry) => {
    set((s) => ({
      recents: capRecents([
        { ...entry, at: Date.now() },
        ...s.recents.filter((r) => r.prompt !== entry.prompt),
      ]),
    }));
    persistNow(get());
  },

  setLocationPermission: (locationPermission) => {
    set({ locationPermission });
    persistNow(get());
  },
  setOnboarded: (onboarded) => {
    set({ onboarded });
    persistNow(get());
  },

  resetLocalData: () => {
    clearPersisted();
    set({
      profile: { name: "Tamu", avatar: null },
      savedPlaces: [],
      savedRoutes: [],
      recents: [],
      locationPermission: "unknown",
      onboarded: false,
    });
  },
}));

/** Recents fall back to the labelled sample entries only while the real list is
 *  empty, so a first-run Home screen is not a blank rectangle. */
export const recentsForDisplay = (recents: RecentEntry[]): RecentEntry[] =>
  recents.length > 0 ? recents : SEED_RECENTS;

export const QUICK_PROMPTS = QUICK;
