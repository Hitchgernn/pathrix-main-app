import { Leaf } from "lucide-react";
import { NAV_W, NAV_W_COLLAPSED } from "../lib/tokens";
import { useStore } from "../store";
import { BasemapSwitcher } from "./BasemapSwitcher";
import { FilterChips } from "./explore/FilterChips";
import { SearchBar } from "./search/SearchPanel";

/** Everything floating over the map on the Explore tab.
 *
 *  The container is pointer-transparent so panning still works in the gaps
 *  between controls; each control opts back in. Search leads, filters sit under
 *  it, and the two map-wide switches (basemap, carbon) stay on the right where
 *  they do not compete with the reading order.
 */
export function MapChrome() {
  const wide = useStore((s) => s.wide);
  const navCollapsed = useStore((s) => s.navCollapsed);
  const panel = useStore((s) => s.panel);
  const togglePanel = useStore((s) => s.togglePanel);
  const searchOpen = useStore((s) => s.searchOpen);

  return (
    <div
      className="pointer-events-none absolute right-0 top-0 z-40 flex flex-col gap-[10px] p-3"
      style={{ left: wide ? (navCollapsed ? NAV_W_COLLAPSED : NAV_W) + 8 : 0 }}
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1" style={wide ? { maxWidth: 420 } : undefined}>
          <SearchBar variant="map" />
        </div>

        {/* Desktop has the width to sit the two map-wide switches on one row
            beside the search field. Narrow stacks them so neither eats into the
            search pill at 390px. */}
        <div
          className={`flex flex-none gap-2 ${
            wide ? "flex-row items-center" : "flex-col items-end"
          }`}
        >
          <BasemapSwitcher />
          <button
            onClick={() => togglePanel("sustain")}
            aria-pressed={panel === "sustain"}
            aria-label="Jejak karbon"
            className={`pointer-events-auto flex h-[38px] w-[38px] items-center justify-center rounded-full shadow-card transition-colors ${
              panel === "sustain" ? "bg-ink text-surface" : "surface-float text-gold-text ring-1 ring-line"
            }`}
          >
            <Leaf size={17} strokeWidth={1.9} />
          </button>
        </div>
      </div>

      {!searchOpen && <FilterChips />}
    </div>
  );
}
