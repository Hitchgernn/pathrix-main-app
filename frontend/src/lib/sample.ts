/** Content transcribed verbatim from the Claude Design canvas.
 *
 *  This is demo content, not a fixture the backend will ever return: no field
 *  survey data has landed and no LLM provider is wired (ARCHITECTURE.md §15.1),
 *  so the app falls back to this so the screens are inspectable. Everything
 *  here is replaced by live data the moment `/ws` answers — see store/index.ts.
 */

import type { RecentEntry } from "./places";

export interface SampleLeg {
  mode: string;
  key: "walk" | "gold" | "krl" | "blue";
  title: string;
  sub: string;
  detail: string;
}

export const SAMPLE_LEGS: SampleLeg[] = [
  {
    mode: "Jalan kaki",
    key: "walk",
    title: "Malioboro → Pangkalan Becak Sosrowijayan",
    sub: "120 m · 2 mnt · Rp0",
    detail:
      "Jalur pedestrian Malioboro, sisi timur. Jaringan jalan kaki dari OSMnx; kecepatan asumsi 4,5 km/jam.",
  },
  {
    mode: "Becak",
    key: "gold",
    title: "Pangkalan Sosrowijayan → Stasiun Lempuyangan",
    sub: "2,1 km · 14 mnt · Rp25.000",
    detail:
      "Tarif nego. Survei lapangan MAPID Apps: kisaran Rp20.000-30.000 di pangkalan ini. Pangkalan aktif 06.00-22.00; becak dimodelkan sebagai penghubung titik-ke-titik, bukan rute tetap.",
  },
  {
    mode: "KRL Yogya-Solo",
    key: "krl",
    title: "Lempuyangan → Stasiun Brambanan",
    sub: "13,4 km · 22 mnt · Rp8.000",
    detail:
      "Dimodelkan dengan headway ±30 mnt, bukan jadwal per menit. Tidak ada feed real-time untuk layanan ini. Waktu tunggu rata-rata sudah termasuk.",
  },
  {
    mode: "Jalan kaki",
    key: "walk",
    title: "Stasiun Brambanan → Pangkalan Andong",
    sub: "180 m · 2 mnt · Rp0",
    detail: "Keluar pintu barat stasiun, pangkalan andong ada di seberang jalan.",
  },
  {
    mode: "Andong",
    key: "gold",
    title: "Pangkalan Brambanan → Candi Prambanan",
    sub: "1,3 km · 11 mnt · Rp30.000",
    detail:
      "Tarif nego, kisaran survei Rp25.000-35.000. Turun di Gerbang Timur; 6 kusir terdata pada pangkalan ini.",
  },
];

export const SAMPLE_ROUTE_SUMMARY = ["51 mnt", "Rp63.000", "17,1 km", "2 transfer"];

export interface LayerRow {
  id: string;
  /** Backend catalogue id this row is served by, when one exists. */
  backendId: string | null;
  name: string;
  meta: string;
  on: boolean;
  color: string;
}

export const LAYER_ROWS: LayerRow[] = [
  { id: "transit", backendId: "transit", name: "Transportasi Publik", meta: "3 operator, 214 halte", on: true, color: "#1f6592" },
  { id: "pangkalan", backendId: "pangkalan", name: "Pangkalan Andong & Becak", meta: "42 titik dari survei lapangan", on: true, color: "#7c5e13" },
  { id: "pariwisata", backendId: "poi", name: "Pariwisata & Sosial Budaya", meta: "96 titik", on: false, color: "#5b3a8e" },
  { id: "properti", backendId: "properti", name: "Properti", meta: "310 titik dari Properti Go", on: false, color: "#17293a" },
  { id: "jangkauan", backendId: null, name: "Jangkauan Jalan Kaki", meta: "Isokron 5, 10, 15 menit", on: false, color: "#c6d9e8" },
  { id: "bangunan", backendId: null, name: "Bangunan", meta: "Urban planning, isian 12%", on: false, color: "rgba(23,41,58,.12)" },
];

/** Home's action grid. Each tile hands the agent a real prompt or drives the
 *  map directly — none of them are decorative. */
export interface QuickAction {
  id: string;
  icon: "route" | "bus" | "carriage" | "layers";
  title: string;
  sub: string;
  prompt: string | null;
  /** Layer ids to switch on when the tile is a map action rather than a query. */
  layers?: string[];
  /** Subject to look up a real photograph for (lib/photos.ts). Omitted where no
   *  honest photograph exists for the concept, and the tile stays iconographic. */
  photo?: string;
}

export const QUICK_ACTIONS: QuickAction[] = [
  {
    id: "rute",
    icon: "route",
    title: "Cari rute",
    sub: "Lintas moda, pintu ke pintu",
    prompt: "Malioboro → Candi Prambanan",
    photo: "Malioboro",
  },
  {
    id: "halte",
    icon: "bus",
    title: "Halte terdekat",
    sub: "TransJogja, KRL, KA Bandara",
    prompt: "Halte TransJogja terdekat",
    photo: "TransJogja",
  },
  {
    id: "pangkalan",
    icon: "carriage",
    title: "Andong & becak",
    sub: "Pangkalan hasil survei",
    prompt: null,
    layers: ["pangkalan"],
    photo: "Andong",
  },
  {
    id: "layer",
    icon: "layers",
    title: "Layer peta",
    sub: "6 layer tematik",
    prompt: null,
  },
];

/** Explore's filter row. Each chip is a view over the same layer catalogue the
 *  panel exposes in full — chips are the fast path, not a second system. */
export interface FilterChip {
  id: string;
  label: string;
  /** Layer ids switched on when the chip is picked. Empty means "show all". */
  layers: string[];
}

export const FILTER_CHIPS: FilterChip[] = [
  { id: "semua", label: "Semua", layers: [] },
  { id: "transit", label: "Halte & KRL", layers: ["transit"] },
  { id: "pangkalan", label: "Andong & becak", layers: ["pangkalan"] },
  { id: "pariwisata", label: "Wisata", layers: ["pariwisata"] },
  { id: "properti", label: "Properti", layers: ["properti"] },
  { id: "jangkauan", label: "Jangkauan", layers: ["jangkauan"] },
];

export interface QuickPrompt {
  text: string;
  route: boolean;
}

export const QUICK: QuickPrompt[] = [
  { text: "Malioboro → Candi Prambanan", route: true },
  { text: "Rute termurah ke YIA", route: false },
  { text: "Halte TransJogja terdekat", route: false },
];

export const REPLY_ROUTE =
  "Rute tercepat: jalan kaki ke pangkalan becak Sosrowijayan, becak ke Stasiun Lempuyangan, KRL Yogya-Solo ke Brambanan, lalu andong ke gerbang candi. Total 51 menit, Rp63.000, 17,1 km. Rutenya sudah saya tandai di peta.";

export const REPLY_GENERIC =
  "Saya perlu titik awal untuk menghitungnya. Sebutkan lokasi Anda sekarang, atau ketuk ikon lokasi di peta. Layer TransJogja sudah aktif jadi haltenya sudah terlihat.";

/** Shown on Home only while the real, localStorage-backed recents list is
 *  still empty — see store/index.ts `recentsForDisplay`. */
export const SEED_RECENTS: RecentEntry[] = [
  {
    title: "Candi Prambanan",
    prompt: "Malioboro → Candi Prambanan",
    at: Date.now() - 3 * 864e5,
  },
  { title: "Stasiun YIA", prompt: "Rute termurah ke YIA", at: Date.now() - 7 * 864e5 },
];

export const SAMPLE_POI = {
  kind: "Pangkalan andong",
  name: "Pangkalan Andong Brambanan",
  meta: "Rp25.000-35.000 · 06.00-21.00 · 6 kusir terdata",
};

export const SAMPLE_CARBON = {
  trip: "2,41 kg",
  month: "18,6 kg",
  trips: "12",
  basis:
    "Dasar perhitungan: 17,1 km dengan KRL, becak dan andong, dibandingkan mobil pribadi berisi satu penumpang untuk jarak yang sama.",
  source: "KLHK (2023), IPCC 2006 Tier 1",
  caveat: "Data contoh. Faktor emisi belum dimuat dari basis data.",
};

/** The design's sample route mirrors the alternative offer under the timeline. */
export const SAMPLE_ALTERNATIVE = {
  label: "Alternatif lebih murah",
  title: "TransJogja 1A → KRL, tanpa becak",
  sub: "63 mnt · Rp45.000 · jalan kaki 640 m lebih jauh",
};
