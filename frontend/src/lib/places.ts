import type { MessageKey } from "../i18n";
import type {
  MissionFeature,
  RichTransitStop,
  RouteStopSchedule,
  RouteStopService,
  StopDeparture,
} from "./types";

/** One place shape the whole app speaks.
 *
 *  Search hits, tapped map markers, saved rows and recents are all the same
 *  thing to the UI, so they are the same type here. The adapters below are the
 *  only places that know what a MAPID mission row or a geocode hit looks like.
 */
export interface Place {
  /** Stable across sessions — `savedPlaces` is keyed on it. */
  id: string;
  name: string;
  kind: PlaceKind;
  /** Category, address, or operator — whatever the source actually has. */
  subtitle: string | null;
  /** [lon, lat]. */
  coord: [number, number];
  photoUrl: string | null;
  /** Detail rows the place sheet renders as chips. Only real values. */
  facts: PlaceFact[];
  /** What the surveyor wrote. An activities post carries a real narrative —
   *  shelter type, roof and ramp condition, guiding block, pavement — and it
   *  is the most informative thing we hold about a halte. Optional because
   *  every other source has nothing like it, and because saved places
   *  persisted before this field existed must still load. */
  description?: string | null;
  /** Attribution for a community survey: nothing here is ours, and the sheet
   *  says whose it is. */
  survey?: { by: string | null; community: string | null; at: string | null } | null;
  /** Every photograph the post carried; `photoUrl` is the first of them. */
  photos?: string[];
  /** Route and timetable data joined onto a surveyed transit stop. */
  transit?: {
    routes: RouteStopService[];
    schedule: RouteStopSchedule | null;
    source: string | null;
    effectiveFrom: string | null;
    effectiveUntil: string | null;
    freshnessStatus: string | null;
  } | null;
}

export type PlaceKind = "poi" | "properti" | "transit" | "pangkalan" | "address";

export interface PlaceFact {
  labelKey: MessageKey;
  value: string;
}

export interface SavedRoute {
  id: string;
  title: string;
  prompt: string;
  meta: string;
  savedAt: number;
}

export interface RecentEntry {
  title: string;
  prompt: string;
  at: number;
}

/** One computed carbon result, logged so Home/Profile/Sustainability can show
 *  a real running "this month" total instead of a permanent sample. */
export interface CarbonLogEntry {
  g: number;
  at: number;
}

/** Display name and accent for each kind. Only pangkalan carries the gold: it
 *  is the one category the field survey owns, and the One Warm Rule allows the
 *  accent exactly one job per screen. */
export const KIND_META: Record<PlaceKind, { labelKey: MessageKey; className: string }> = {
  poi: { labelKey: "kind.poi", className: "text-ink-2" },
  properti: { labelKey: "kind.properti", className: "text-ink-2" },
  transit: { labelKey: "kind.transit", className: "text-ink-2" },
  pangkalan: { labelKey: "kind.pangkalan", className: "text-gold-text" },
  address: { labelKey: "kind.address", className: "text-ink-2" },
};

const str = (value: unknown): string | null => {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return null;
};

/** First present key, so one adapter copes with MAPID's several mission
 *  shapes without pretending a missing field is an empty string. */
const pick = (raw: Record<string, unknown>, ...keys: string[]): string | null => {
  for (const key of keys) {
    const value = str(raw[key]);
    if (value) return value;
  }
  return null;
};

const FALLBACK_NAME: Record<PlaceKind, string> = {
  poi: "Tempat",
  properti: "Properti",
  transit: "Halte",
  pangkalan: "Pangkalan",
  address: "Lokasi",
};

/** An activity post carries its photographs as a `medias` array of URLs — a
 *  real photograph of the actual place, so it outranks the drawn placeholder
 *  (lib/photos.ts) the same way a mission `foto_url` does. */
const allMedia = (raw: Record<string, unknown>): string[] =>
  Array.isArray(raw.medias) ? raw.medias.filter((m): m is string => typeof m === "string") : [];

const pointOf = (feature: MissionFeature): [number, number] | null => {
  const geometry = feature.geometry;
  if (geometry.type === "Point") {
    const [lon, lat] = geometry.coordinates;
    return [lon, lat];
  }
  return null;
};

/** The fact chips a row can support. Shared by both adapters, so a place found
 *  through search and the same place tapped on the map cannot disagree. */
const factsOf = (raw: Record<string, unknown>): PlaceFact[] => {
  const facts: PlaceFact[] = [];
  const open = pick(raw, "jam_buka");
  const close = pick(raw, "jam_tutup");
  if (open) facts.push({ labelKey: "fact.hours", value: close ? `${open}-${close}` : open });
  const price = pick(raw, "harga_rata_rata");
  if (price) facts.push({ labelKey: "fact.avgPrice", value: rupiahish(price) });
  const jenis = pick(raw, "jenis_properti", "kategori_properti");
  if (jenis) facts.push({ labelKey: "fact.type", value: jenis });
  return facts;
};

/** Surveyor, community and date, or null when the row is not a survey post. */
const surveyOf = (raw: Record<string, unknown>): Place["survey"] => {
  const by = pick(raw, "user_full_name", "user_name", "surveyor");
  const community = pick(raw, "community_name");
  const at = pick(raw, "created_at", "surveyed_at", "tanggal");
  return by || community || at ? { by, community, at } : null;
};

/** A `/api/layers/{id}/features` row → a Place. Returns null for a geometry the
 *  place sheet cannot anchor (the mirrored rows are almost always Points). */
export function placeFromFeature(feature: MissionFeature, layerId: string): Place | null {
  const coord = pointOf(feature);
  if (!coord) return null;

  const raw = feature.properties ?? {};
  const kind: PlaceKind =
    layerId === "properti" || layerId === "transit" || layerId === "pangkalan"
      ? layerId
      : "poi";
  // The geoserver halte layer spells its columns in caps (NAMA, ALAMAT) where
  // the mission API spells them lowercase; both arrive here as raw upstream
  // attributes, so both spellings are listed rather than normalised anywhere.
  // `title` is the activities-mission spelling — a community survey post, which
  // is where the becak stands and the directional A/B halte come from.
  const name =
    pick(raw, "nama_tempat", "name", "nama", "NAMA", "title", "judul", "alamat", "ALAMAT") ??
    FALLBACK_NAME[kind];

  return {
    id: `${layerId}:${feature.external_id}`,
    name,
    kind,
    subtitle: pick(raw, "kategori", "alamat", "ALAMAT", "kategori_properti"),
    coord,
    photoUrl: pick(raw, "foto_url", "photo_url") ?? allMedia(raw)[0] ?? null,
    facts: factsOf(raw),
    description: pick(raw, "description", "deskripsi"),
    survey: surveyOf(raw),
    photos: allMedia(raw),
  };
}

const routeStopCoord = (stop: RichTransitStop): [number, number] | null => {
  const coord = stop.coord ?? stop.coordinate;
  if (
    !coord ||
    coord.length < 2 ||
    !Number.isFinite(coord[0]) ||
    !Number.isFinite(coord[1])
  ) {
    return null;
  }
  return [coord[0], coord[1]];
};

/** A stop embedded in a route response → the same Place the marker sheet uses.
 *  API media and survey prose remain primary; timetable data is only attached. */
export function placeFromRouteStop(stop: RichTransitStop): Place | null {
  const coord = routeStopCoord(stop);
  if (!coord) return null;

  const photos = (stop.photos ?? []).filter((url) => typeof url === "string" && url.trim());
  const photoUrl = stop.photo_url?.trim() || photos[0] || null;
  const routes = Array.isArray(stop.routes) ? stop.routes : [];
  const service = routes[0];

  return {
    id: `transit:${stop.external_id ?? stop.id}`,
    name: stop.name?.trim() || FALLBACK_NAME.transit,
    kind: "transit",
    subtitle: service?.operator ?? null,
    coord,
    photoUrl,
    facts: [],
    description: stop.description?.trim() || null,
    survey: stop.survey ?? null,
    photos,
    transit: {
      routes,
      schedule: stop.schedule ?? null,
      source: stop.source ?? service?.source ?? stop.schedule?.source ?? null,
      effectiveFrom:
        stop.effective_from ?? service?.effective_from ?? stop.schedule?.effective_from ?? null,
      effectiveUntil:
        stop.effective_until ?? service?.effective_until ?? stop.schedule?.effective_until ?? null,
      freshnessStatus:
        stop.freshness_status ??
        service?.freshness_status ??
        stop.schedule?.freshness_status ??
        null,
    },
  };
}

/** Group departure rows into the same service shape used by rich route stops. */
export function transitFromDepartures(
  departures: StopDeparture[],
): NonNullable<Place["transit"]> {
  const byRoute = new Map<number, RouteStopService>();
  for (const departure of departures) {
    const time = `${departure.day_offset > 0 ? `+${departure.day_offset} ` : ""}${departure.scheduled_time_local}`;
    const service = byRoute.get(departure.route_id);
    if (service) {
      if (!service.next_departures?.includes(time)) service.next_departures?.push(time);
      continue;
    }
    byRoute.set(departure.route_id, {
      route_id: departure.route_id,
      name: departure.service_name,
      source: departure.source,
      effective_from: departure.effective_from,
      effective_until: departure.effective_until,
      freshness_status: departure.freshness_status,
      next_departures: [time],
    });
  }
  const routes = [...byRoute.values()];
  const first = routes[0];
  return {
    routes,
    schedule: null,
    source: first?.source ?? null,
    effectiveFrom: first?.effective_from ?? null,
    effectiveUntil: first?.effective_until ?? null,
    freshnessStatus: first?.freshness_status ?? null,
  };
}

/** `/api/geocode` hit → a Place. The backend already normalizes local DB rows
 *  and Nominatim results into one shape. */
export interface PlaceHit {
  id: string;
  name: string;
  kind: string;
  subtitle: string | null;
  lon: number;
  lat: number;
  /** Upstream attributes of a mirrored row — the same payload
   *  `/api/layers/{id}/features` carries. Null for a Nominatim address. */
  raw?: Record<string, unknown> | null;
}

const KINDS = new Set<string>(["poi", "properti", "transit", "pangkalan", "address"]);

export function placeFromHit(hit: PlaceHit): Place {
  // A mirrored row arrives with its attributes, so a result chosen from the
  // search box opens the same sheet tapping its marker does. An address has
  // none, and stays the two-line result it genuinely is.
  const raw = hit.raw ?? {};
  return {
    id: hit.id,
    name: hit.name,
    kind: (KINDS.has(hit.kind) ? hit.kind : "address") as PlaceKind,
    subtitle: hit.subtitle,
    coord: [hit.lon, hit.lat],
    photoUrl: pick(raw, "foto_url", "photo_url") ?? allMedia(raw)[0] ?? null,
    facts: factsOf(raw),
    description: pick(raw, "description", "deskripsi"),
    survey: surveyOf(raw),
    photos: allMedia(raw),
  };
}

/** Rupiah for a value that arrived as text — the mission mirror stores whatever
 *  the surveyor typed, so a non-numeric value is passed through untouched
 *  rather than coerced into a fake number. */
function rupiahish(value: string): string {
  const digits = Number(value.replace(/[^\d]/g, ""));
  if (!Number.isFinite(digits) || digits === 0) return value;
  return `Rp${digits.toLocaleString("id-ID")}`;
}
