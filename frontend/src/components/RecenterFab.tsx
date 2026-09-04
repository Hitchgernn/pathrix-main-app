import { LocateFixed, Locate } from "lucide-react";
import { recenterOnUser } from "../lib/actions";
import { getMap } from "../lib/mapHandle";
import { useStore, YOGYA_CENTER, YOGYA_ZOOM } from "../store";

interface RecenterFabProps {
  /** Sits above whatever is anchored to the bottom, so it moves with the sheet. */
  bottom: number;
}

/** Centre on you if you have granted location, otherwise on the Kraton. The
 *  icon says which of the two it will do — a filled crosshair only once a real
 *  fix exists, so the control never promises a position it does not have. */
export function RecenterFab({ bottom }: RecenterFabProps) {
  const userCoord = useStore((s) => s.userCoord);
  const hasFix = userCoord !== null;

  return (
    <button
      onClick={() => {
        if (recenterOnUser()) return;
        getMap()?.flyTo({ center: YOGYA_CENTER, zoom: YOGYA_ZOOM, duration: 900 });
      }}
      aria-label={hasFix ? "Pusatkan ke lokasi Anda" : "Pusatkan ke Yogyakarta"}
      className="surface-float absolute right-3 z-40 flex h-12 w-12 items-center justify-center rounded-full shadow-float ring-1 ring-line transition-[bottom] duration-300 ease-[var(--ease-out-expo)]"
      style={{ bottom }}
    >
      {hasFix ? (
        <LocateFixed size={20} strokeWidth={1.9} className="text-ink" />
      ) : (
        <Locate size={20} strokeWidth={1.9} className="text-ink-2" />
      )}
    </button>
  );
}
