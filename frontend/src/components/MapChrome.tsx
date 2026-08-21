import { LAYER_ROWS } from "../lib/sample";
import { RAIL_W } from "../lib/tokens";
import { useStore } from "../store";
import { BasemapSwitcher } from "./BasemapSwitcher";
import { StateJumper } from "./StateJumper";

/** Floating map chrome. The container is pointer-transparent so panning still
 *  works between the controls; each control opts back in. */
export function MapChrome() {
  const wide = useStore((s) => s.wide);
  const panel = useStore((s) => s.panel);
  const active = useStore((s) => s.active);
  const togglePanel = useStore((s) => s.togglePanel);

  const chip = (on: boolean) =>
    `kicker pointer-events-auto flex items-center gap-[7px] rounded-full px-[14px] py-2 shadow-card transition-colors ${
      on ? "bg-blue text-surface" : "surface-sheet text-ink"
    }`;

  return (
    <div
      className="pointer-events-none absolute right-0 top-0 z-50 p-4"
      style={{ left: wide ? RAIL_W + 14 : 0 }}
    >
      <div className="flex items-start justify-between gap-[10px]">
        <StateJumper />

        <div className="flex flex-col items-end gap-2">
          <BasemapSwitcher />
          <button onClick={() => togglePanel("layers")} className={chip(panel === "layers")}>
            LAYERS <span className="opacity-55">{active.size}/{LAYER_ROWS.length}</span>
          </button>
          <button onClick={() => togglePanel("sustain")} className={chip(panel === "sustain")}>
            CO₂E
          </button>
        </div>
      </div>
    </div>
  );
}
