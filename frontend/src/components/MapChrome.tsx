import { Leaf } from "lucide-react";
import { useT } from "../i18n";
import { NAV_W, NAV_W_COLLAPSED } from "../lib/tokens";
import { useStore } from "../store";
import { BasemapSwitcher } from "./BasemapSwitcher";
import { View3dToggle } from "./View3dToggle";
import { FilterChips } from "./explore/FilterChips";
import { SearchBar } from "./search/SearchPanel";

/** Everything floating over the map on the Explore tab.
 *
 *  The container is pointer-transparent so panning still works in the gaps
 *  between controls; each control opts back in. Search leads, the map-wide
 *  switches follow on the right where they do not compete with the reading
 *  order, and the filters sit under both.
 *
 *  Wide puts the switches beside the search field. Narrow gives the field its
 *  own row and drops the switches to a right-aligned row beneath it: three
 *  controls stacked in a column beside a 390px search pill squeeze the field to
 *  about three quarters and stair-step three different widths down the edge.
 *  A row is also shorter than the column it replaces, so it hands ~36px back to
 *  the map — every control is 38px tall, including the switcher pill, so they
 *  line up across rather than ragging down.
 */
export function MapChrome() {
  const wide = useStore((s) => s.wide);
  const navCollapsed = useStore((s) => s.navCollapsed);
  const panel = useStore((s) => s.panel);
  const togglePanel = useStore((s) => s.togglePanel);
  const searchOpen = useStore((s) => s.searchOpen);
  const t = useT();

  const switches = (
    <>
      <BasemapSwitcher />
      <View3dToggle />
      <button
        onClick={() => togglePanel("sustain")}
        aria-pressed={panel === "sustain"}
        aria-label={t("map.carbon")}
        className={`pointer-events-auto flex h-[38px] w-[38px] items-center justify-center rounded-full shadow-card transition-colors ${
          panel === "sustain" ? "bg-ink text-surface" : "surface-float text-gold-text ring-1 ring-line"
        }`}
      >
        <Leaf size={17} strokeWidth={1.9} />
      </button>
    </>
  );

  return (
    <div
      className="pointer-events-none absolute right-0 top-0 z-40 flex flex-col gap-[10px] p-3"
      style={{ left: wide ? (navCollapsed ? NAV_W_COLLAPSED : NAV_W) + 8 : 0 }}
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1" style={wide ? { maxWidth: 420 } : undefined}>
          <SearchBar variant="map" />
        </div>
        {wide && <div className="flex flex-none items-center gap-2">{switches}</div>}
      </div>

      {/* The search results drop over this row, and the filters already step
          aside for them, so these do too rather than sitting half-covered. */}
      {!wide && !searchOpen && <div className="flex justify-end gap-2">{switches}</div>}

      {!searchOpen && <FilterChips />}
    </div>
  );
}
