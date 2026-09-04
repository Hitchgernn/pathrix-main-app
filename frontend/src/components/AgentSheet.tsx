import { useEffect, useRef } from "react";
import { ArrowUp, ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import { Check } from "lucide-react";
import { useT } from "../i18n";
import { scriptFor, type DemoKind } from "../lib/demoAgent";
import { QUICK } from "../lib/sample";
import { useSheetDrag } from "../lib/useSheetDrag";
import { useStore } from "../store";
import { RouteCard } from "./RouteCard";

interface AgentSheetProps {
  /** `sheet` floats over the map with three snap points; `panel` fills the tab
   *  or the desktop context column. Same conversation, same store slice. */
  variant: "sheet" | "panel";
  /** Resolved height in px (drag height, or the current snap point). */
  height: number;
  vh: number;
  /** Room to leave for the floating tab bar underneath. */
  bottomInset?: number;
}

/** The agent. In `sheet` it is the map's companion; in `panel` it is a screen of
 *  its own — the only difference is the chrome around the same message list. */
export function AgentSheet({ variant, height, vh, bottomInset = 0 }: AgentSheetProps) {
  const agentSnap = useStore((s) => s.agentSnap);
  const dragH = useStore((s) => s.dragH);
  const messages = useStore((s) => s.messages);
  const streaming = useStore((s) => s.streaming);
  const demoKind = useStore((s) => s.demoKind);
  const demoStep = useStore((s) => s.demoStep);
  const offline = useStore((s) => s.offline);
  const input = useStore((s) => s.input);
  const setInput = useStore((s) => s.setInput);
  const ask = useStore((s) => s.ask);
  const setAgentSnap = useStore((s) => s.setAgentSnap);
  const t = useT();

  const drag = useSheetDrag(vh);
  const scroller = useRef<HTMLDivElement | null>(null);

  const isSheet = variant === "sheet";
  const showConversation = !isSheet || agentSnap !== "peek";
  const firstRun = messages.length === 0;

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages.length, streaming]);

  const submit = () => {
    const text = input.trim();
    if (!text) {
      // Empty send is a request to see the conversation, not a message.
      if (isSheet) setAgentSnap(agentSnap === "peek" ? "half" : agentSnap);
      return;
    }
    ask(text);
  };

  const shellStyle = isSheet
    ? {
        left: 8,
        right: 8,
        bottom: bottomInset,
        height,
        borderRadius: "var(--radius-sheet)",
        boxShadow: "var(--shadow-sheet)",
        // Height, not transform, on purpose: the sheet's height *is* the snap
        // state, and the composer must stay pinned to the bottom edge while
        // the content above it reflows. A transform would slide the whole
        // sheet off-screen instead of resizing it.
        transition: dragH != null ? "none" : "height .3s var(--ease-out-expo)",
      }
    : { inset: 0, height };

  return (
    <div
      className={
        isSheet
          ? "surface-float absolute z-30 flex flex-col ring-1 ring-line"
          : "absolute z-30 flex flex-col bg-ground"
      }
      style={shellStyle}
    >
      {isSheet ? (
        <div
          onPointerDown={drag.onPointerDown}
          onPointerMove={drag.onPointerMove}
          onPointerUp={drag.onPointerUp}
          className="flex flex-none cursor-grab touch-none flex-col items-center pb-[6px] pt-[10px]"
        >
          <div className="h-1 w-[38px] rounded-[2px] bg-line-strong" />
        </div>
      ) : (
        <div className="h-4 flex-none" />
      )}

      <div
        className={`flex flex-none items-center gap-[9px] px-5 ${isSheet ? "pb-[6px]" : "pb-3"}`}
      >
        <span className="flex h-7 w-7 flex-none items-center justify-center rounded-[9px] bg-surface-3">
          <Sparkles size={15} strokeWidth={1.9} className="text-ink" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-[15px] font-semibold tracking-[-.01em]">{t("agent.name")}</span>
          {/* The simulation banner must not disappear at the one moment the app
              is most convincing. While a script runs, the steps below already
              say what is happening, so the header keeps saying what it is. */}
          {streaming && demoKind ? (
            <span className="label-sm block text-ink-3">{t("agent.demoBanner")}</span>
          ) : streaming ? (
            <span className="label-sm animate-pxdim block text-ink-2">{t("agent.composing")}</span>
          ) : (
            <span className="label-sm block text-ink-3">
              {t(offline ? "agent.demoBanner" : "agent.reading")}
            </span>
          )}
        </span>
        {isSheet && (
          <button
            onClick={() => setAgentSnap(agentSnap === "full" ? "peek" : "full")}
            aria-label={t(agentSnap === "full" ? "agent.collapse" : "agent.expand")}
            className="-mr-1 flex-none rounded-full p-2 text-ink-4 transition-colors hover:bg-surface-2 hover:text-ink"
          >
            {agentSnap === "full" ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
          </button>
        )}
      </div>

      {showConversation && (
        <div
          ref={scroller}
          className="flex min-h-0 flex-1 flex-col gap-[14px] overflow-y-auto px-5 pb-1 pt-2"
        >
          {firstRun && (
            <div className="flex flex-col gap-[14px] pb-[2px] pt-1">
              <p className="body-15 max-w-[46ch] text-ink-2">
                {t("agent.intro")}
              </p>
              <div className="flex flex-wrap gap-2">
                {QUICK.map((q) => (
                  <button
                    key={q.text}
                    onClick={() => ask(q.text)}
                    className="body-13 flex-none whitespace-nowrap rounded-control border border-line-strong px-[14px] py-2 text-ink-2 transition-colors hover:border-transparent hover:bg-ink/90 hover:text-surface"
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
                {/* Only user messages get a fill — the agent speaks as the
                    instrument itself, so its prose sits unfilled on the sheet
                    (docs/DESIGN.md §Agent Chat Bubble). */}
                <div
                  className={
                    user
                      ? "body-15 max-w-[82%] rounded-field bg-ink px-[15px] py-[11px] text-surface"
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

          {streaming &&
            (demoKind ? (
              <ThinkingSteps kind={demoKind} step={demoStep} />
            ) : (
              <p className="label-sm animate-pxdim text-ink-3">{t("agent.calculating")}</p>
            ))}
        </div>
      )}

      <div className="flex flex-none items-center gap-[10px] border-t border-line px-4 pb-[18px] pt-[12px]">
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") submit();
          }}
          placeholder={t("agent.placeholder")}
          aria-label={t("agent.inputLabel")}
          className="min-w-0 flex-1 rounded-control border border-line-strong bg-surface px-[16px] py-[12px] text-[15px] text-ink outline-none placeholder:text-ink-3"
        />
        <button
          onClick={submit}
          aria-label={t("agent.send")}
          disabled={streaming}
          className="flex h-[44px] w-[44px] flex-none items-center justify-center rounded-full bg-ink text-surface transition-colors hover:bg-ink/90 disabled:opacity-45"
        >
          <ArrowUp size={19} strokeWidth={2.2} />
        </button>
      </div>
    </div>
  );
}

/** What the agent is doing, in words.
 *
 *  docs/DESIGN.md bans spinners, shimmer and animated loading icons and asks
 *  that pending status be stated in language. A stepped list satisfies that
 *  rule rather than working around it, and it says something a spinner cannot:
 *  which part of the work is happening.
 *
 *  Every step names something the real agent will actually do, so when a
 *  provider lands these become progress the backend reports rather than lines a
 *  timer prints.
 */
function ThinkingSteps({ kind, step }: { kind: DemoKind; step: number }) {
  const steps = scriptFor(kind);
  const t = useT();
  return (
    <ol className="flex flex-col gap-[7px] py-1" aria-live="polite">
      {steps.map((entry, index) => {
        const done = index < step;
        const current = index === step;
        // Steps that have not started yet are not announced at all: a list of
        // future promises reads as a progress bar with extra words.
        if (!done && !current) return null;
        return (
          <li
            key={entry.key}
            className={`flex items-center gap-[8px] text-[13px] ${
              current ? "animate-pxdim text-ink" : "text-ink-3"
            }`}
          >
            <span className="flex h-4 w-4 flex-none items-center justify-center">
              {done ? (
                <Check size={13} strokeWidth={2.4} className="text-ink-4" />
              ) : (
                <span className="h-[6px] w-[6px] rounded-full bg-ink" />
              )}
            </span>
            {t(entry.key)}
          </li>
        );
      })}
    </ol>
  );
}
