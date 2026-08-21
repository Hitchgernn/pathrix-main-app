import { useStore } from "../store";
import { paletteFor, RAIL_W } from "../lib/tokens";
import { useWindowSize } from "../lib/useWindowSize";

/** The itinerary schematic over the map.
 *
 *  Authored in a 400×800 space spanning x 40..380, y 170..720 and mapped 1:1 to
 *  CSS pixels (scaling down only when the map box is smaller than the content)
 *  so stroke weights and marker radii hold their authored size at every
 *  viewport. Transcribed from the design canvas.
 *
 *  This is the sample itinerary. Real geometry arrives through the
 *  `draw_route` ui_command once the backend's Route carries coordinates —
 *  see lib/bridge.ts.
 */
export function RouteOverlay() {
  const basemap = useStore((s) => s.basemap);
  const wide = useStore((s) => s.wide);
  const { vw, vh } = useWindowSize();
  const c = paletteFor(basemap);

  const mapW = wide ? Math.max(240, vw - RAIL_W - 14) : vw;
  const k = Math.min(1, mapW / 360, vh / 580);
  const vbW = Math.round(mapW / k);
  const vbH = Math.round(vh / k);
  const viewBox = `${Math.round(210 - vbW / 2)} ${Math.round(445 - vbH / 2)} ${vbW} ${vbH}`;

  return (
    <svg
      viewBox={viewBox}
      preserveAspectRatio="xMidYMid meet"
      className="absolute right-0 top-0 bottom-0 pointer-events-none"
      style={{ left: wide ? RAIL_W + 14 : 0 }}
    >
      {/* Halo pass — one dark/light casing under every leg so the coloured
          strokes hold contrast on both basemap treatments. */}
      <path d="M72 690 L110 652" fill="none" stroke={c.halo} strokeWidth="9" strokeLinecap="round" opacity=".5" />
      <path d="M110 652 L168 560" fill="none" stroke={c.halo} strokeWidth="11" strokeLinecap="round" />
      <path d="M168 560 L300 300" fill="none" stroke={c.halo} strokeWidth="13" strokeLinecap="round" />
      <path d="M300 300 L330 250" fill="none" stroke={c.halo} strokeWidth="9" strokeLinecap="round" opacity=".5" />
      <path d="M330 250 L352 196" fill="none" stroke={c.halo} strokeWidth="11" strokeLinecap="round" />

      {/* Legs, in mode colour. Walk is dashed and thin; it is never the hero. */}
      <path d="M72 690 L110 652" fill="none" stroke={c.walk} strokeWidth="3" strokeLinecap="round" strokeDasharray="2 6" />
      <path d="M110 652 L168 560" fill="none" stroke={c.gold} strokeWidth="5" strokeLinecap="round" />
      <path d="M168 560 L300 300" fill="none" stroke={c.krl} strokeWidth="7" strokeLinecap="round" />
      <path d="M300 300 L330 250" fill="none" stroke={c.walk} strokeWidth="3" strokeLinecap="round" strokeDasharray="2 6" />
      <path d="M330 250 L352 196" fill="none" stroke={c.gold} strokeWidth="5" strokeLinecap="round" />

      {/* The cheaper alternative, shown alongside rather than replacing. */}
      <path d="M243 470 L296 430" fill="none" stroke={c.blue} strokeWidth="4" strokeLinecap="round" opacity=".85" />
      <path d="M296 430 L318 372" fill="none" stroke={c.blue} strokeWidth="4" strokeLinecap="round" opacity=".85" />

      <circle cx="168" cy="560" r="8" fill={c.stopFill} stroke={c.krl} strokeWidth="3.5" />
      <circle cx="300" cy="300" r="8" fill={c.stopFill} stroke={c.krl} strokeWidth="3.5" />
      <circle cx="243" cy="470" r="6" fill={c.stopFill} stroke={c.blue} strokeWidth="3" />
      <circle cx="296" cy="430" r="6" fill={c.stopFill} stroke={c.blue} strokeWidth="3" />

      <circle cx="72" cy="690" r="7" fill={c.halo} />
      <circle cx="72" cy="690" r="2.5" fill={c.stopFill} />
      <circle cx="352" cy="196" r="7" fill={c.halo} />
      <circle cx="352" cy="196" r="2.5" fill={c.stopFill} />

      {/* Pangkalan pins — the andong/becak handoffs. */}
      <g>
        <circle cx="110" cy="640" r="11" fill="#d9a521" stroke={c.halo} strokeWidth="1.5" />
        <path d="M110 651 l-4 -5 h8 Z" fill="#d9a521" />
        <rect x="106" y="636" width="8" height="8" rx="1" fill="#101e2a" />
      </g>
      <g>
        <circle cx="330" cy="239" r="11" fill="#d9a521" stroke={c.halo} strokeWidth="1.5" />
        <path d="M330 250 l-4 -5 h8 Z" fill="#d9a521" />
        <rect x="326" y="235" width="8" height="8" rx="1" fill="#101e2a" />
      </g>
    </svg>
  );
}
