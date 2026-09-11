import type { Map as MapLibreMap } from "maplibre-gl";

/** Extruded buildings, the half of "3D view" that is not just a tilted camera.
 *
 *  MAPID's vector sources carry a `building` source-layer with a `render_height`
 *  attribute — real OSM heights, defaulting to 5m where a building has no
 *  height or levels tag. Over central Yogyakarta that is ~24k buildings a tile,
 *  most at the 5m default with a few hundred standing out of them.
 *
 *  `street-v2.0` already ships its own `building-3d` layers off the same data.
 *  We hide them and draw our own instead, because they exist in *no* other
 *  style — dark has flat 2D building fills and nothing more — so using them
 *  would mean 3D looking like a different feature per theme. Their paint ramps
 *  to royalblue above 200m as well, and blue in the chrome is the one colour
 *  docs/DESIGN.md rules out: it competes with the route line.
 *
 *  Ids follow bridge.ts's pathrix-{concern}-{id} convention, but deliberately
 *  not the `pathrix-mission-` prefix — MapCanvas's tap hit test matches on that
 *  string, and a rooftop is not a marker.
 */

/** MAPID's own extrusion layers, hidden in favour of ours. Street-only. */
const MAPID_LAYERS = ["building-3d", "building-3d_indonesia"];

/** The two vector sources that carry buildings. `indonesiatiles` is the one
 *  that matters here; `mapidtiles` is world-minus-Indonesia and draws nothing
 *  over Yogyakarta, but it is cheap and keeps the map honest if it is ever
 *  panned off the island. Neither exists in `satellite-v2.0`, hence the guard. */
const SOURCES = ["indonesiatiles", "mapidtiles"];

const layerId = (source: string) => `pathrix-buildings-${source}`;

/** Where to slot the extrusions: directly above the last road layer.
 *
 *  Buildings stand on the ground, so they belong over the roads and under the
 *  type. "Below the first label" is the usual shorthand for that and it is
 *  wrong here — dark-v2.0 puts `water_name` at index 15, twelve layers *below*
 *  its road network, so anchoring on labels would bury the buildings under the
 *  streets. Anchoring on roads lands at index 165 in street-v2.0 — exactly
 *  where MAPID puts its own extrusions — and 63 in dark-v2.0, just under the
 *  road labels. */
function beforeLayerId(map: MapLibreMap): string | undefined {
  const layers = map.getStyle().layers;
  let after = -1;
  layers.forEach((layer, index) => {
    if (layer.type !== "symbol" && "source-layer" in layer && layer["source-layer"] === "transportation") {
      after = index;
    }
  });
  return after >= 0 ? layers[after + 1]?.id : layers.find((layer) => layer.type === "symbol")?.id;
}

function addLayer(map: MapLibreMap, source: string, color: string): void {
  if (map.getLayer(layerId(source)) || !map.getSource(source)) return;
  map.addLayer(
    {
      id: layerId(source),
      type: "fill-extrusion",
      source,
      "source-layer": "building",
      minzoom: 14,
      // OSM's own opt-out, honoured by MAPID's layers too.
      filter: ["!=", ["get", "hide_3d"], true],
      paint: {
        "fill-extrusion-color": color,
        // Buildings grow out of the ground between z15 and z16 rather than
        // appearing at full height, so crossing the minzoom is not a pop.
        "fill-extrusion-height": [
          "interpolate",
          ["linear"],
          ["zoom"],
          15,
          0,
          16,
          ["get", "render_height"],
        ],
        "fill-extrusion-base": 0,
        "fill-extrusion-opacity": ["interpolate", ["linear"], ["zoom"], 15, 0.5, 20, 1],
      },
    },
    beforeLayerId(map),
  );
}

function setVisible(map: MapLibreMap, id: string, visible: boolean): void {
  if (!map.getLayer(id)) return;
  map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
}

/** Draws (or hides) the extrusions for the current style. Safe to call on a
 *  style that has neither source — it simply draws nothing. */
export function applyBuildings3d(map: MapLibreMap, color: string, on: boolean): void {
  for (const id of MAPID_LAYERS) setVisible(map, id, false);
  for (const source of SOURCES) {
    if (on) addLayer(map, source, color);
    setVisible(map, layerId(source), on);
  }
}

/** setStyle discards every layer we added, the same way it does for the route.
 *  Called from MapCanvas's `styledata` handler *before* the route and mission
 *  layers go back on, so those redraw above the buildings rather than under
 *  them. */
export const reapplyBuildings3d = applyBuildings3d;
