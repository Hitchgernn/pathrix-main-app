import { Moon, Sun } from "lucide-react";
import { useT, type MessageKey } from "../i18n";
import { useStore } from "../store";
import type { Basemap } from "../lib/tokens";

const OPTIONS: { id: Basemap; labelKey: MessageKey; Icon: typeof Sun }[] = [
  { id: "street", labelKey: "map.styleLight", Icon: Sun },
  { id: "dark", labelKey: "map.styleDark", Icon: Moon },
];

/** Route and marker contrast is verified against both treatments — a stroke
 *  that reads on street disappears on dark (ARCHITECTURE.md §10.4). */
export function BasemapSwitcher() {
  const basemap = useStore((s) => s.basemap);
  const setBasemap = useStore((s) => s.setBasemap);
  const t = useT();

  return (
    <div
      role="group"
      aria-label={t("map.styleGroup")}
      className="surface-float pointer-events-auto flex gap-[2px] rounded-control p-[3px] shadow-card ring-1 ring-line"
    >
      {OPTIONS.map(({ id, labelKey, Icon }) => {
        const active = basemap === id;
        return (
          <button
            key={id}
            onClick={() => setBasemap(id)}
            aria-label={t(labelKey)}
            aria-pressed={active}
            className={`flex h-8 w-8 items-center justify-center rounded-full transition-colors ${
              active ? "bg-ink text-surface" : "text-ink-3 hover:bg-surface-2"
            }`}
          >
            <Icon size={16} strokeWidth={1.9} />
          </button>
        );
      })}
    </div>
  );
}
