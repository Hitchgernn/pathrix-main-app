import { SAMPLE_POI } from "../lib/sample";
import { RAIL_W } from "../lib/tokens";
import { useWindowSize } from "../lib/useWindowSize";
import { useStore } from "../store";
import { PhotoSlot } from "./PhotoSlot";

/** Feature popup for a tapped map point. Anchored beside the rail on desktop,
 *  full-width under the chrome on mobile. */
export function PoiCard() {
  const wide = useStore((s) => s.wide);
  const setPoi = useStore((s) => s.setPoi);
  const openPanel = useStore((s) => s.openPanel);
  const { vw } = useWindowSize();

  const position = wide
    ? {
        left: Math.max(RAIL_W + 14, Math.min(RAIL_W + 400, vw - 356)),
        top: 96,
        width: 340,
      }
    : { left: 16, right: 16, top: 118 };

  return (
    <div
      className="absolute z-25 animate-pxrise overflow-hidden rounded-card border border-line bg-surface shadow-card"
      style={position}
    >
      <div className="flex gap-[14px] p-[14px]">
        <div className="h-[74px] w-[74px] flex-none">
          <PhotoSlot src={null} alt={SAMPLE_POI.name} placeholder="Foto survei" />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="h-3 w-1 rounded-[1px] bg-gold" />
            <span className="kicker text-gold">{SAMPLE_POI.kicker}</span>
          </div>
          <div className="title-row mt-[5px]">{SAMPLE_POI.name}</div>
          <div className="body-13 mt-[3px] text-ink-66">{SAMPLE_POI.meta}</div>
        </div>

        <button
          onClick={() => setPoi(false)}
          className="kicker self-start px-1 py-[2px] text-ink-50"
          aria-label="Tutup"
        >
          ✕
        </button>
      </div>

      <div className="h-px bg-line" />

      <button
        onClick={() => openPanel("route")}
        className="body-13 block w-full px-[14px] py-3 text-left text-blue hover:bg-surface-2"
      >
        Pakai sebagai penghubung last-mile →
      </button>
    </div>
  );
}
