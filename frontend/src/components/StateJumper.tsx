import { useStore } from "../store";
import type { JumpState } from "../store";

const STATES: { label: string; state: JumpState }[] = [
  { label: "AGENT · FIRST RUN", state: "empty" },
  { label: "AGENT · THINKING…", state: "thinking" },
  { label: "ROUTE DETAIL", state: "route" },
  { label: "ROUTE · LEG EXPANDED", state: "leg" },
  { label: "LAYERS · FULL", state: "layers" },
  { label: "POI POPUP", state: "poi" },
  { label: "SUSTAINABILITY", state: "sustain" },
  { label: "SUSTAINABILITY · EMPTY", state: "sustainEmpty" },
  { label: "DARK BASEMAP", state: "dark" },
];

/** Jumps straight to any screen state without walking the flow. Carried over
 *  from the design canvas because the competition demo and QA both need it. */
export function StateJumper() {
  const barOpen = useStore((s) => s.barOpen);
  const setBarOpen = useStore((s) => s.setBarOpen);
  const jump = useStore((s) => s.jump);
  const setScreen = useStore((s) => s.setScreen);

  return (
    <div className="flex flex-col items-start gap-2">
      <button
        onClick={() => setBarOpen(!barOpen)}
        className="surface-sheet kicker pointer-events-auto flex items-center gap-2 rounded-full px-[13px] py-[7px] text-ink shadow-card"
      >
        PROTOTYPE <span className="opacity-50">{barOpen ? "▲" : "▼"}</span>
      </button>

      {barOpen && (
        <div className="surface-sheet pointer-events-auto flex min-w-[210px] animate-pxfade flex-col rounded-card p-2 shadow-card">
          {STATES.map((entry) => (
            <button
              key={entry.state}
              onClick={() => jump(entry.state)}
              className="kicker rounded-[10px] px-[10px] py-2 text-left tracking-[.14em] text-ink hover:bg-ground"
            >
              {entry.label}
            </button>
          ))}
          <div className="mx-2 my-[6px] h-px bg-line" />
          <button
            onClick={() => {
              setScreen("dashboard");
              setBarOpen(false);
            }}
            className="kicker rounded-[10px] px-[10px] py-2 text-left tracking-[.14em] text-ink-60 hover:bg-ground"
          >
            ← DASHBOARD
          </button>
        </div>
      )}
    </div>
  );
}
