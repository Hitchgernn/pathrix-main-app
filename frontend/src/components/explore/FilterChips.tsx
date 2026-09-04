import { SlidersHorizontal } from "lucide-react";
import { FILTER_CHIPS, LAYER_ROWS } from "../../lib/sample";
import { useStore } from "../../store";

const DEFAULT_LAYERS = LAYER_ROWS.filter((row) => row.on).map((row) => row.id);

/** The fast path over the layer catalogue.
 *
 *  These are the same layer ids the panel's full list toggles — one source of
 *  truth, two densities — so a chip and its row can never disagree about what
 *  is on the map.
 */
export function FilterChips() {
  const active = useStore((s) => s.active);
  const setLayers = useStore((s) => s.setLayers);
  const openPanel = useStore((s) => s.openPanel);
  const panel = useStore((s) => s.panel);

  // Exactly one chip reads as chosen at a time. Multi-select still exists — it
  // is the full layer list behind the button at the end of the row.
  const chosen =
    FILTER_CHIPS.find(
      (chip) =>
        chip.layers.length > 0 &&
        chip.layers.length === active.size &&
        chip.layers.every((id) => active.has(id)),
    )?.id ?? (sameSet(active, DEFAULT_LAYERS) ? "semua" : null);

  return (
    <div className="pointer-events-auto flex items-center gap-2">
      <div className="no-scrollbar flex min-w-0 flex-1 gap-2 overflow-x-auto">
        {FILTER_CHIPS.map((chip) => {
          const on = chosen === chip.id;
          return (
            <button
              key={chip.id}
              onClick={() => setLayers(chip.layers.length === 0 ? DEFAULT_LAYERS : chip.layers)}
              aria-pressed={on}
              className={`flex-none whitespace-nowrap rounded-control px-[15px] py-[9px] text-[13px] font-semibold tracking-[-.005em] shadow-card transition-colors ${
                on ? "bg-ink text-surface" : "surface-float text-ink-2 ring-1 ring-line"
              }`}
            >
              {chip.label}
            </button>
          );
        })}
      </div>

      <button
        onClick={() => openPanel("layers")}
        aria-label="Semua layer"
        aria-pressed={panel === "layers"}
        className={`flex h-[38px] w-[38px] flex-none items-center justify-center rounded-full shadow-card transition-colors ${
          panel === "layers" ? "bg-ink text-surface" : "surface-float text-ink-2 ring-1 ring-line"
        }`}
      >
        <SlidersHorizontal size={17} strokeWidth={1.9} />
      </button>
    </div>
  );
}

const sameSet = (active: Set<string>, ids: string[]): boolean =>
  active.size === ids.length && ids.every((id) => active.has(id));
