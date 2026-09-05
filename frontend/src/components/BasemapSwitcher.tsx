import { Moon, Sun } from "lucide-react";
import { useT, type MessageKey } from "../i18n";
import { useStore } from "../store";

const OPTIONS: { id: "light" | "dark"; labelKey: MessageKey; Icon: typeof Sun }[] = [
  { id: "light", labelKey: "map.styleLight", Icon: Sun },
  { id: "dark", labelKey: "map.styleDark", Icon: Moon },
];

/** Switches the whole appearance, not just the tiles. The chrome and the
 *  cartography are one decision: a light app over a dark map is a bug, not a
 *  preference. Picking either value here also pins the preference off "system".
 *
 *  Route and marker contrast is verified against both treatments — a stroke
 *  that reads on street disappears on dark (ARCHITECTURE.md §10.4). */
export function BasemapSwitcher() {
  const basemap = useStore((s) => s.basemap);
  const setTheme = useStore((s) => s.setTheme);
  const t = useT();

  return (
    <div
      role="group"
      aria-label={t("map.styleGroup")}
      className="surface-float pointer-events-auto flex gap-[2px] rounded-control p-[3px] shadow-card ring-1 ring-line"
    >
      {OPTIONS.map(({ id, labelKey, Icon }) => {
        const active = (id === "dark") === (basemap === "dark");
        return (
          <button
            key={id}
            onClick={() => setTheme(id)}
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
