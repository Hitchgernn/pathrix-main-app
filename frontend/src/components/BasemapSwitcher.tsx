import { useStore } from "../store";
import type { Basemap } from "../lib/tokens";

const OPTIONS: { id: Basemap; label: string }[] = [
  { id: "street", label: "STREET" },
  { id: "dark", label: "DARK" },
];

/** Route and marker contrast is verified against both treatments — a stroke
 *  that reads on street disappears on dark (ARCHITECTURE.md §10.4). */
export function BasemapSwitcher() {
  const basemap = useStore((s) => s.basemap);
  const setBasemap = useStore((s) => s.setBasemap);

  return (
    <div className="surface-sheet flex gap-[2px] rounded-full p-[3px] shadow-sheet">
      {OPTIONS.map((option) => {
        const active = basemap === option.id;
        return (
          <button
            key={option.id}
            onClick={() => setBasemap(option.id)}
            className={`kicker pointer-events-auto rounded-full px-[14px] py-[7px] transition-colors ${
              active ? "bg-blue text-surface" : "text-ink-60"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
