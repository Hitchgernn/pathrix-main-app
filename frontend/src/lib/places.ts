import type { MissionFeature } from "./types";

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
}

export type PlaceKind = "poi" | "properti" | "transit" | "pangkalan" | "address";

export interface PlaceFact {
  label: string;
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

/** Display name and accent for each kind. Only pangkalan carries the gold: it
 *  is the one category the field survey owns, and the One Warm Rule allows the
 *  accent exactly one job per screen. */
export const KIND_META: Record<PlaceKind, { label: string; className: string }> = {
  poi: { label: "Tempat", className: "text-ink-2" },
  properti: { label: "Properti", className: "text-ink-2" },
  transit: { label: "Halte", className: "text-ink-2" },
  pangkalan: { label: "Pangkalan", className: "text-gold-text" },
  address: { label: "Alamat", className: "text-ink-2" },
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

const pointOf = (feature: MissionFeature): [number, number] | null => {
  const geometry = feature.geometry;
  if (geometry.type === "Point") {
    const [lon, lat] = geometry.coordinates;
    return [lon, lat];
  }
  return null;
};

/** A `/api/layers/{id}/features` row → a Place. Returns null for a geometry the
 *  place sheet cannot anchor (the mirrored rows are almost always Points). */
export function placeFromFeature(feature: MissionFeature, layerId: string): Place | null {
  const coord = pointOf(feature);
  if (!coord) return null;

  const raw = feature.properties ?? {};
  const kind: PlaceKind = layerId === "properti" ? "properti" : "poi";
  const name =
    pick(raw, "nama_tempat", "name", "nama", "judul", "alamat") ??
    (kind === "properti" ? "Properti" : "Tempat");

  const facts: PlaceFact[] = [];
  const open = pick(raw, "jam_buka");
  const close = pick(raw, "jam_tutup");
  if (open) facts.push({ label: "Jam buka", value: close ? `${open}-${close}` : open });
  const price = pick(raw, "harga_rata_rata");
  if (price) facts.push({ label: "Harga rata-rata", value: rupiahish(price) });
  const jenis = pick(raw, "jenis_properti", "kategori_properti");
  if (jenis) facts.push({ label: "Jenis", value: jenis });

  return {
    id: `${layerId}:${feature.external_id}`,
    name,
    kind,
    subtitle: pick(raw, "kategori", "alamat", "kategori_properti"),
    coord,
    photoUrl: pick(raw, "foto_url", "photo_url"),
    facts,
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
}

const KINDS = new Set<string>(["poi", "properti", "transit", "pangkalan", "address"]);

export function placeFromHit(hit: PlaceHit): Place {
  return {
    id: hit.id,
    name: hit.name,
    kind: (KINDS.has(hit.kind) ? hit.kind : "address") as PlaceKind,
    subtitle: hit.subtitle,
    coord: [hit.lon, hit.lat],
    photoUrl: null,
    facts: [],
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
