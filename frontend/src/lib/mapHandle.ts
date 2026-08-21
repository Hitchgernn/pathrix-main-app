import type { Map as MapLibreMap } from "maplibre-gl";

/** The live MapLibre instance. MapCanvas owns its lifecycle; the bridge and the
 *  agent socket read it. Module-scoped rather than in the store because a GL
 *  map is not serialisable state and must never trigger a React re-render. */
let handle: MapLibreMap | null = null;

export const setMap = (map: MapLibreMap | null): void => {
  handle = map;
};

export const getMap = (): MapLibreMap | null => handle;
