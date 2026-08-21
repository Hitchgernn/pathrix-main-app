import { useEffect, useRef } from "react";
import { QUICK } from "../lib/sample";
import { RAIL_W } from "../lib/tokens";
import { useSheetDrag } from "../lib/useSheetDrag";
import { useStore } from "../store";
import { RouteCard } from "./RouteCard";

interface AgentSheetProps {
  /** Resolved sheet height in px (drag height, or the current snap point). */
  height: number;
  vh: number;
}

/** The agent, in a three-snap-point bottom sheet. At the wide breakpoint it is
 *  promoted to a left rail without changing the component tree
 *  (ARCHITECTURE.md §10.3). */
export function AgentSheet({ height, vh }: AgentSheetProps) {
  const wide = useStore((s) => s.wide);
  const agentSnap = useStore((s) => s.agentSnap);
  const dragH = useStore((s) => s.dragH);
  const messages = useStore((s) => s.messages);
  const streaming = useStore((s) => s.streaming);
  const input = useStore((s) => s.input);
  const setInput = useStore((s) => s.setInput);
  const ask = useStore((s) => s.ask);
  const setAgentSnap = useStore((s) => s.setAgentSnap);

  const drag = useSheetDrag(vh);
  const scroller = useRef<HTMLDivElement | null>(null);

  const showConversation = wide || agentSnap !== "peek";
  const firstRun = messages.length === 0;

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages.length, streaming]);

  const submit = () => {
    const text = input.trim();
    if (!text) {
      // Empty send is a request to see the conversation, not a message.
      setAgentSnap(agentSnap === "peek" ? "half" : agentSnap);
      return;
    }
    ask(text);
  };

  const shellStyle = wide
    ? { left: 0, top: 0, bottom: 0, width: RAIL_W, borderRadius: "0 20px 20px 0", boxShadow: "var(--shadow-rail)" }
    : {
        left: 0,
        right: 0,
        bottom: 0,
        height,
        borderRadius: "20px 20px 0 0",
        boxShadow: "var(--shadow-sheet)",
        transition: dragH != null ? "none" : "height .26s var(--ease-snap)",
      };

  return (
    <div className="surface-sheet absolute z-30 flex flex-col" style={shellStyle}>
      <div
        onPointerDown={drag.onPointerDown}
        onPointerMove={drag.onPointerMove}
        onPointerUp={drag.onPointerUp}
        className="flex flex-none cursor-grab flex-col items-center pb-[6px] pt-[10px] touch-none"
      >
        <div className="h-1 w-[38px] rounded-[2px] bg-line" />
      </div>

      <div className="flex flex-none items-center justify-between gap-3 px-5 pb-[6px]">
        <div className="flex min-w-0 items-center gap-[9px]">
          <span className="kicker text-ink-55">AGENT</span>
          {streaming && <span className="kicker animate-pxdim text-blue">THINKING…</span>}
        </div>
        <span className="kicker text-ink-40">{wide ? "RAIL" : agentSnap.toUpperCase()}</span>
      </div>

      {showConversation && (
        <div
          ref={scroller}
          className="flex min-h-0 flex-1 flex-col gap-[14px] overflow-y-auto px-5 pb-1 pt-2"
        >
          {firstRun && (
            <div className="flex flex-col gap-[14px] pb-[2px] pt-1">
              <div className="body-15 max-w-[46ch] text-ink-72">
                Saya membaca peta yang sedang Anda lihat — layer aktif, rute terakhir, dan
                viewport. Sebutkan tujuan, atau minta hal lain.
              </div>
              <div className="flex flex-wrap gap-2">
                {QUICK.map((q) => (
                  <button
                    key={q.text}
                    onClick={() => ask(q.text)}
                    className="body-13 flex-none whitespace-nowrap rounded-full border border-line px-[14px] py-2 text-ink transition-colors hover:border-blue hover:bg-blue hover:text-surface"
                  >
                    {q.text}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message, index) => {
            const user = message.who === "user";
            return (
              <div
                key={index}
                className={`flex animate-pxrise-slow flex-col ${user ? "items-end" : "items-start"}`}
              >
                {/* Only user messages get a fill — agent prose stays unfilled. */}
                <div
                  className={
                    user
                      ? "body-15 max-w-[82%] rounded-bubble bg-blue px-[15px] py-[11px] text-surface"
                      : "body-15 max-w-[47ch] text-ink"
                  }
                >
                  {message.text}
                </div>
                {message.who === "agent" && message.route !== undefined && (
                  <RouteCard route={message.route} />
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="flex flex-none items-center gap-[10px] border-t border-line px-5 pb-[18px] pt-[10px]">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submit();
          }}
          placeholder="Tanya agen…"
          className="min-w-0 flex-1 rounded-full border border-line bg-surface px-4 py-[11px] text-[15px] text-ink outline-none"
        />
        <button
          onClick={submit}
          className="kicker rounded-full bg-blue px-[17px] py-[11px] text-surface transition-colors hover:bg-ink"
        >
          SEND
        </button>
      </div>
    </div>
  );
}
