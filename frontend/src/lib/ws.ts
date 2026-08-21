import type { BBox, ClientMessage, ServerMessage } from "./types";

/** Two-channel WebSocket client for /ws — ARCHITECTURE.md §9.1.
 *
 *  Prose (`token`) and map manipulation (`ui_command`) arrive on separate
 *  message types and are never mixed, so the caller never parses instructions
 *  out of chat text.
 */

export interface AgentSocketHandlers {
  onMessage(message: ServerMessage): void;
  onOpen?(): void;
  onClose?(): void;
}

const VIEWPORT_DEBOUNCE_MS = 300;
const RECONNECT_MIN_MS = 800;
const RECONNECT_MAX_MS = 8000;

function socketUrl(): string {
  const configured = import.meta.env.VITE_WS_URL;
  if (configured) return configured;
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws`;
}

export class AgentSocket {
  private socket: WebSocket | null = null;
  private handlers: AgentSocketHandlers;
  private viewportTimer: number | null = null;
  private pendingViewport: { bbox: BBox; zoom: number } | null = null;
  private retryMs = RECONNECT_MIN_MS;
  private closedByCaller = false;

  constructor(handlers: AgentSocketHandlers) {
    this.handlers = handlers;
  }

  connect(): void {
    this.closedByCaller = false;
    const socket = new WebSocket(socketUrl());
    this.socket = socket;

    socket.onopen = () => {
      this.retryMs = RECONNECT_MIN_MS;
      this.handlers.onOpen?.();
      if (this.pendingViewport) this.flushViewport();
    };

    socket.onmessage = (event) => {
      let parsed: ServerMessage;
      try {
        parsed = JSON.parse(event.data as string) as ServerMessage;
      } catch {
        return;
      }
      this.handlers.onMessage(parsed);
    };

    socket.onclose = () => {
      this.socket = null;
      this.handlers.onClose?.();
      if (this.closedByCaller) return;
      window.setTimeout(() => this.connect(), this.retryMs);
      this.retryMs = Math.min(this.retryMs * 2, RECONNECT_MAX_MS);
    };

    // onerror always precedes onclose; reconnect is handled there only.
    socket.onerror = () => socket.close();
  }

  close(): void {
    this.closedByCaller = true;
    if (this.viewportTimer !== null) window.clearTimeout(this.viewportTimer);
    this.socket?.close();
    this.socket = null;
  }

  get isOpen(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  private send(message: ClientMessage): boolean {
    if (!this.isOpen) return false;
    this.socket!.send(JSON.stringify(message));
    return true;
  }

  /** Sent with the current viewport attached, so "di area ini" resolves against
   *  what the user is actually looking at. */
  ask(text: string, viewport: { bbox: BBox; zoom: number }): boolean {
    return this.send({ type: "user_message", text, viewport });
  }

  /** Debounced — the camera fires continuously while panning. */
  pushViewport(bbox: BBox, zoom: number): void {
    this.pendingViewport = { bbox, zoom };
    if (this.viewportTimer !== null) window.clearTimeout(this.viewportTimer);
    this.viewportTimer = window.setTimeout(() => this.flushViewport(), VIEWPORT_DEBOUNCE_MS);
  }

  private flushViewport(): void {
    this.viewportTimer = null;
    const pending = this.pendingViewport;
    if (!pending) return;
    if (this.send({ type: "viewport_changed", bbox: pending.bbox, zoom: pending.zoom })) {
      this.pendingViewport = null;
    }
  }
}
