import { useEffect, useRef, useState } from "react";
import type { Map as MapLibreMap } from "maplibre-gl";
import { useStore } from "../store";
import { setMap } from "../lib/mapHandle";
import { reapplyRoute } from "../lib/bridge";
import { fetchLayerFeatures } from "../lib/api";
import { reapplyMissionLayers, removeMissionLayer, syncMissionLayer } from "../lib/missionLayers";
import { LAYER_ROWS } from "../lib/sample";
import { paletteFor, RAIL_W } from "../lib/tokens";
import type { Basemap } from "../lib/tokens";

const STYLE_ID: Record<Basemap, string> = {
  street: "street-v2.0",
  dark: "dark-v2.0",
};

const BASEMAP_KEY = import.meta.env.VITE_MAPID_BASEMAP_KEY ?? "";

/** Matches lib/ws.ts's viewport debounce — the camera fires continuously while
 *  panning, so a fetch per moveend would spam the layer endpoint. */
const MISSION_FETCH_DEBOUNCE_MS = 400;

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
  const active = useStore((s) => s.active);
  const bbox = useStore((s) => s.bbox);
  const catalogue = useStore((s) => s.catalogue);
  const setCamera = useStore((s) => s.setCamera);
  const [veiled, setVeiled] = useState(false);
  const drawnMissionLayers = useRef<Set<string>>(new Set());

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
        reapplyMissionLayers(instance);
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

  // Mission layers (poi/properti — the only two /api/layers ids that aren't a
  // 501 today, per catalogue.queryable): fetch-and-draw whichever are toggled
  // on, scoped to the current viewport, debounced against the moveend flood.
  // A layer that's toggled off is removed immediately, no debounce needed for
  // that direction.
  useEffect(() => {
    const instance = map.current;
    if (!instance || !bbox) return;

    const queryable = new Set(catalogue.filter((l) => l.queryable).map((l) => l.id));
    const liveRows = LAYER_ROWS.filter(
      (row) => row.backendId !== null && queryable.has(row.backendId) && active.has(row.id),
    );
    const liveIds = new Set(liveRows.map((row) => row.backendId as string));

    for (const layerId of drawnMissionLayers.current) {
      if (!liveIds.has(layerId)) {
        removeMissionLayer(instance, layerId);
        drawnMissionLayers.current.delete(layerId);
      }
    }

    const timer = window.setTimeout(() => {
      for (const row of liveRows) {
        const layerId = row.backendId as string;
        fetchLayerFeatures(layerId, bbox)
          .then((features) => {
            if (!map.current) return;
            syncMissionLayer(map.current, layerId, features, row.color);
            drawnMissionLayers.current.add(layerId);
          })
          .catch(() => undefined); // a failed mission fetch must never break the map
      }
    }, MISSION_FETCH_DEBOUNCE_MS);

    return () => window.clearTimeout(timer);
  }, [active, bbox, catalogue]);

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
      {/* maplibre-gl sets this container's position to relative, which drops
          Tailwind's inset-0 auto-sizing (that only fills the parent while the
          element is absolute/fixed) — the div collapsed to height:0 and the
          canvas never got real dimensions. h-full/w-full sizes it explicitly
          instead of relying on inset offsets. */}
      <div ref={container} className="absolute inset-0 h-full w-full" />
      <div
        className="absolute inset-0 pointer-events-none bg-ground transition-opacity"
        style={{ opacity: veiled ? 1 : 0, transitionDuration: `${FADE_MS}ms` }}
      />
    </div>
  );
}
