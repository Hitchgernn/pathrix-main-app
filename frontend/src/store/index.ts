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
import { LAYER_ROWS, QUICK, REPLY_GENERIC, REPLY_ROUTE } from "../lib/sample";
import type { AgentSocket } from "../lib/ws";

export type Screen = "dashboard" | "app";
export type AgentSnap = "peek" | "half" | "full";
export type PanelName = "layers" | "route" | "sustain";
export type PanelSnap = "half" | "full";

/** Kraton-centred default camera; the map owns the real one from first render. */
export const YOGYA_CENTER: [number, number] = [110.3695, -7.7956];
export const YOGYA_ZOOM = 12;

const DEMO_REPLY_MS = 1400;

const initialLayers = new Set(LAYER_ROWS.filter((l) => l.on).map((l) => l.id));

interface MapSlice {
  bbox: BBox | null;
  zoom: number;
  center: [number, number];
  basemap: Basemap;
  /** MapLibre owns camera state; the store mirrors it. Never bind back. */
  setCamera(center: [number, number], zoom: number, bbox: BBox): void;
  setBasemap(basemap: Basemap): void;
}

interface LayerSlice {
  active: Set<string>;
  catalogue: LayerMeta[];
  toggleLayer(id: string, on?: boolean): void;
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
  socket: AgentSocket | null;
  attachSocket(socket: AgentSocket | null): void;
  ask(text: string): void;
  handleServerMessage(message: ServerMessage): void;
}

interface UiSlice {
  screen: Screen;
  agentSnap: AgentSnap;
  dragH: number | null;
  panel: PanelName | null;
  panelSnap: PanelSnap;
  legOpen: number | null;
  poi: boolean;
  barOpen: boolean;
  input: string;
  wide: boolean;
  sustainEmpty: boolean;
  setScreen(screen: Screen): void;
  setAgentSnap(snap: AgentSnap): void;
  setDragH(height: number | null): void;
  cycleAgentSnap(): void;
  openPanel(panel: PanelName): void;
  togglePanel(panel: PanelName): void;
  closePanel(): void;
  cyclePanelSnap(): void;
  setLegOpen(index: number | null): void;
  setPoi(open: boolean): void;
  setBarOpen(open: boolean): void;
  setInput(value: string): void;
  setWide(wide: boolean): void;
  setSustainEmpty(empty: boolean): void;
  jump(state: JumpState): void;
}

export type JumpState =
  | "empty"
  | "thinking"
  | "route"
  | "leg"
  | "layers"
  | "poi"
  | "sustain"
  | "sustainEmpty"
  | "dark";

export type Store = MapSlice & LayerSlice & AgentSlice & UiSlice;

/** Demo timer, module-scoped so a second ask cancels the first. */
let demoTimer: number | null = null;

const looksLikeRoute = (text: string) => /prambanan|malioboro/i.test(text);

const seedConversation = (): ChatMessage[] => [
  { who: "user", text: "Malioboro → Candi Prambanan" },
  { who: "agent", text: REPLY_ROUTE, route: null },
];

export const useStore = create<Store>()((set, get) => ({
  // ---- map ----------------------------------------------------------------
  bbox: null,
  zoom: YOGYA_ZOOM,
  center: YOGYA_CENTER,
  basemap: "street",
  setCamera: (center, zoom, bbox) => set({ center, zoom, bbox }),
  setBasemap: (basemap) => set({ basemap }),

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
  setCatalogue: (catalogue) => set({ catalogue }),

  // ---- agent --------------------------------------------------------------
  messages: [],
  streaming: false,
  lastRoute: null,
  lastCarbon: null,
  offline: false,
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
      agentSnap: "half",
      panel: null,
      barOpen: false,
    }));

    const sent =
      socket !== null && bbox !== null && socket.ask(trimmed, { bbox, zoom });
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
        set((s) => ({
          streaming: false,
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
        if (demoTimer !== null) window.clearTimeout(demoTimer);
        const asked = get().messages[get().messages.length - 1];
        const route = asked ? looksLikeRoute(asked.text) : false;
        demoTimer = window.setTimeout(() => {
          demoTimer = null;
          set((s) => ({
            streaming: false,
            messages: s.messages.concat([
              { who: "agent", text: route ? REPLY_ROUTE : REPLY_GENERIC, route: null },
            ]),
          }));
        }, DEMO_REPLY_MS);
        break;
      }
    }
  },

  // ---- ui -----------------------------------------------------------------
  screen: "dashboard",
  agentSnap: "peek",
  dragH: null,
  panel: null,
  panelSnap: "half",
  legOpen: null,
  poi: false,
  barOpen: false,
  input: "",
  wide: false,
  sustainEmpty: false,

  setScreen: (screen) => set({ screen }),
  setAgentSnap: (snap) =>
    set(snap === "full" ? { agentSnap: snap, dragH: null, panel: null } : { agentSnap: snap, dragH: null }),
  setDragH: (dragH) => set({ dragH }),
  cycleAgentSnap: () => {
    const current = get().agentSnap;
    get().setAgentSnap(current === "peek" ? "half" : current === "half" ? "full" : "peek");
  },
  openPanel: (panel) =>
    set({ panel, panelSnap: "half", agentSnap: "peek", dragH: null, barOpen: false, poi: false }),
  togglePanel: (panel) =>
    get().panel === panel ? set({ panel: null }) : get().openPanel(panel),
  closePanel: () => set({ panel: null }),
  cyclePanelSnap: () => set((s) => ({ panelSnap: s.panelSnap === "full" ? "half" : "full" })),
  setLegOpen: (legOpen) => set({ legOpen, panelSnap: "full" }),
  setPoi: (poi) => set({ poi }),
  setBarOpen: (barOpen) => set({ barOpen }),
  setInput: (input) => set({ input }),
  setWide: (wide) => set({ wide }),
  setSustainEmpty: (sustainEmpty) => set({ sustainEmpty }),

  /** State jumper from the design's PROTOTYPE menu — every screen state the
   *  canvas can show, reachable without walking the whole flow. */
  jump: (state) => {
    if (demoTimer !== null) {
      window.clearTimeout(demoTimer);
      demoTimer = null;
    }
    const base = {
      screen: "app" as Screen,
      barOpen: false,
      poi: false,
      panel: null as PanelName | null,
      streaming: false,
      legOpen: null as number | null,
      sustainEmpty: false,
      dragH: null,
    };
    const seed = seedConversation();
    const map: Record<JumpState, Partial<Store>> = {
      empty: { agentSnap: "half", messages: [] },
      thinking: {
        agentSnap: "half",
        messages: [{ who: "user", text: "Malioboro → Candi Prambanan" }],
        streaming: true,
      },
      route: { agentSnap: "peek", messages: seed, panel: "route", panelSnap: "half" },
      leg: { agentSnap: "peek", messages: seed, panel: "route", panelSnap: "full", legOpen: 2 },
      layers: { agentSnap: "peek", messages: seed, panel: "layers", panelSnap: "full" },
      poi: { agentSnap: "peek", messages: seed, poi: true },
      sustain: { agentSnap: "peek", messages: seed, panel: "sustain", panelSnap: "half" },
      sustainEmpty: {
        agentSnap: "peek",
        messages: [],
        panel: "sustain",
        panelSnap: "half",
        sustainEmpty: true,
      },
      dark: { agentSnap: "peek", messages: seed, basemap: "dark" },
    };
    set({ ...base, ...map[state] });
  },
}));

export const QUICK_PROMPTS = QUICK;
