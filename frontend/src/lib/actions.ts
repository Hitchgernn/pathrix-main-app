import { getMap } from "./mapHandle";
import type { Place } from "./places";
import { useStore } from "../store";

/** Cross-cutting gestures that touch both the store and the imperative map.
 *
 *  They live here rather than in the store because the store must not hold or
 *  reach for a GL context (`lib/mapHandle.ts` exists for exactly that reason),
 *  and not in a component because Home, Explore, Saved and search all perform
 *  the same gesture.
 */

const PLACE_ZOOM = 16;

/** Show a place: switch to the map, fly there, open its sheet, remember it. */
export function goToPlace(place: Place): void {
  const store = useStore.getState();
  store.setTab("explore");
  store.selectPlace(place);
  store.pushRecent({ title: place.name, prompt: `Rute ke ${place.name}` });

  const map = getMap();
  if (!map) return;
  map.flyTo({ center: place.coord, zoom: Math.max(map.getZoom(), PLACE_ZOOM), duration: 900 });
}

/** Hand a prompt to the agent from anywhere, landing on the map so the route it
 *  draws is actually visible. */
export function askFromAnywhere(prompt: string): void {
  const store = useStore.getState();
  store.setTab("explore");
  store.setAgentSnap("half");
  store.ask(prompt);
}

/** Centre on the user's own position, if they have granted it. */
export function recenterOnUser(): boolean {
  const { userCoord } = useStore.getState();
  const map = getMap();
  if (!map || !userCoord) return false;
  map.flyTo({ center: userCoord, zoom: Math.max(map.getZoom(), 15), duration: 900 });
  return true;
}
