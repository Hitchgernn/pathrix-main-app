import { getMap } from "../lib/mapHandle";
import { useStore, YOGYA_CENTER, YOGYA_ZOOM } from "../store";

interface RecenterFabProps {
  /** Sits above the agent sheet on mobile, so it moves with the snap point. */
  bottom: number;
}

export function RecenterFab({ bottom }: RecenterFabProps) {
  const wide = useStore((s) => s.wide);

  return (
    <button
      onClick={() =>
        getMap()?.flyTo({ center: YOGYA_CENTER, zoom: YOGYA_ZOOM, duration: 900 })
      }
      aria-label="Pusatkan peta"
      className="surface-sheet absolute right-4 z-25 flex h-12 w-12 items-center justify-center rounded-full shadow-card transition-[bottom] duration-[260ms] ease-[var(--ease-snap)]"
      style={{ bottom: wide ? 24 : bottom }}
    >
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#17293a" strokeWidth="1.8">
        <circle cx="12" cy="12" r="3.2" />
        <circle cx="12" cy="12" r="7.6" opacity=".45" />
        <path d="M12 1.6v3M12 19.4v3M1.6 12h3M19.4 12h3" />
      </svg>
    </button>
  );
}
