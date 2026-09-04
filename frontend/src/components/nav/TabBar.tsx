import { TABBAR_H } from "../../lib/tokens";
import { useStore } from "../../store";
import { TABS } from "./tabs";

/** Mobile navigation: a floating white bar over the map, not a docked one.
 *  Docking it to the screen edge would cut the map at a hard line; floating it
 *  keeps the map reading as the layer underneath everything, which is the one
 *  rule docs/DESIGN.md holds hardest. */
export function TabBar() {
  const tab = useStore((s) => s.tab);
  const setTab = useStore((s) => s.setTab);

  return (
    <nav
      aria-label="Navigasi utama"
      className="pointer-events-auto absolute inset-x-3 z-50 flex items-stretch overflow-hidden rounded-sheet bg-surface shadow-float ring-1 ring-line"
      style={{ bottom: "calc(env(safe-area-inset-bottom, 0px) + 10px)", height: TABBAR_H }}
    >
      {TABS.map(({ id, label, icon: Icon }) => {
        const active = tab === id;
        return (
          <button
            key={id}
            onClick={() => setTab(id)}
            aria-current={active ? "page" : undefined}
            className="group relative flex flex-1 flex-col items-center justify-center gap-[3px] rounded-[22px]"
          >
            <Icon
              size={21}
              strokeWidth={active ? 2.1 : 1.7}
              className={`transition-colors ${active ? "text-ink" : "text-ink-4"}`}
            />
            <span
              className={`text-[10.5px] leading-none tracking-[-.005em] transition-colors ${
                active ? "font-semibold text-ink" : "font-normal text-ink-3"
              }`}
            >
              {label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
