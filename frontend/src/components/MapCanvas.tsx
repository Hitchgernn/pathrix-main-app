import { useEffect, useRef, useState } from "react";
import type { Map as MapLibreMap } from "maplibre-gl";
import { useStore } from "../store";
import { setMap } from "../lib/mapHandle";
import { reapplyRoute } from "../lib/bridge";
import { paletteFor, RAIL_W } from "../lib/tokens";
import type { Basemap } from "../lib/tokens";

const STYLE_ID: Record<Basemap, string> = {
  street: "street-v2.0",
  dark: "dark-v2.0",
};

const BASEMAP_KEY = import.meta.env.VITE_MAPID_BASEMAP_KEY ?? "";

/** MAPID MAPS is a plain MapLibre style-spec v8 document behind a key — there
 *  is no SDK (ARCHITECTURE.md §6.1). */
const styleUrl = (basemap: Basemap) =>
  `https://v2.basemap.mapid.io/styles/${STYLE_ID[basemap]}/style.json?key=${BASEMAP_KEY}`;

/** Matches the design's .3s basemap cross-fade without a second GL context:
 *  a ground-coloured veil covers the swap while setStyle re-parses. */
const FADE_MS = 300;

export function MapCanvas() {
  const container = useRef<HTMLDivElement | null>(null);
  const map = useRef<MapLibreMap | null>(null);
  const basemap = useStore((s) => s.basemap);
  const wide = useStore((s) => s.wide);
  const setCamera = useStore((s) => s.setCamera);
  const [veiled, setVeiled] = useState(false);

  useEffect(() => {
    if (!BASEMAP_KEY || !container.current) return;
    let cancelled = false;

    (async () => {
      const maplibre = await import("maplibre-gl");
      await import("maplibre-gl/dist/maplibre-gl.css");
      if (cancelled || !container.current) return;

      const instance = new maplibre.Map({
        container: container.current,
        style: styleUrl(useStore.getState().basemap),
        center: useStore.getState().center,
        zoom: useStore.getState().zoom,
        attributionControl: { compact: true },
      });

      const publish = () => {
        const bounds = instance.getBounds();
        const center = instance.getCenter();
        setCamera([center.lng, center.lat], instance.getZoom(), {
          min_lon: bounds.getWest(),
          min_lat: bounds.getSouth(),
          max_lon: bounds.getEast(),
          max_lat: bounds.getNorth(),
        });
      };

      instance.on("load", publish);
      instance.on("moveend", publish);
      // setStyle discards every source and layer the bridge added, so the drawn
      // route is put back once the incoming style is ready.
      instance.on("styledata", () => {
        if (!instance.isStyleLoaded()) return;
        reapplyRoute(instance, paletteFor(useStore.getState().basemap));
      });

      map.current = instance;
      setMap(instance);
    })();

    return () => {
      cancelled = true;
      setMap(null);
      map.current?.remove();
      map.current = null;
    };
    // Mount-only: the map instance outlives every prop change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Basemap switch. The styledata handler above re-applies the drawn route in
  // the incoming palette.
  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    setVeiled(true);
    instance.setStyle(styleUrl(basemap));
    const timer = window.setTimeout(() => setVeiled(false), FADE_MS);
    return () => window.clearTimeout(timer);
  }, [basemap]);

  // The rail occupies the left edge on wide viewports; the canvas is inset to
  // match so the map's own centre is not hidden behind it.
  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const timer = window.setTimeout(() => instance.resize(), 280);
    return () => window.clearTimeout(timer);
  }, [wide]);

  const inset = wide ? RAIL_W + 14 : 0;

  if (!BASEMAP_KEY) {
    return (
      <div
        className="absolute inset-0 bg-ground flex items-center justify-center px-8"
        style={{ left: inset }}
      >
        <p className="kicker text-ink-40 text-center leading-[1.9]">
          BASEMAP KEY NOT SET
          <br />
          SET VITE_MAPID_BASEMAP_KEY TO LOAD MAPID MAPS
        </p>
      </div>
    );
  }

  return (
    <div className="absolute inset-0 bg-ground" style={{ left: inset }}>
      <div ref={container} className="absolute inset-0" />
      <div
        className="absolute inset-0 pointer-events-none bg-ground transition-opacity"
        style={{ opacity: veiled ? 1 : 0, transitionDuration: `${FADE_MS}ms` }}
      />
    </div>
  );
}
