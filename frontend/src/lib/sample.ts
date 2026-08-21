/** Content transcribed verbatim from the Claude Design canvas.
 *
 *  This is demo content, not a fixture the backend will ever return: no field
 *  survey data has landed and no LLM provider is wired (ARCHITECTURE.md §15.1),
 *  so the app falls back to this so the screens are inspectable. Everything
 *  here is replaced by live data the moment `/ws` answers — see store/index.ts.
 */

export interface SampleLeg {
  mode: string;
  key: "walk" | "gold" | "krl" | "blue";
  title: string;
  sub: string;
  detail: string;
}

export const SAMPLE_LEGS: SampleLeg[] = [
  {
    mode: "JALAN KAKI",
    key: "walk",
    title: "Malioboro → Pangkalan Becak Sosrowijayan",
    sub: "120 m · 2 mnt · Rp0",
    detail:
      "Jalur pedestrian Malioboro, sisi timur. Jaringan jalan kaki dari OSMnx; kecepatan asumsi 4,5 km/jam.",
  },
  {
    mode: "BECAK",
    key: "gold",
    title: "Pangkalan Sosrowijayan → Stasiun Lempuyangan",
    sub: "2,1 km · 14 mnt · Rp25.000",
    detail:
      "Tarif nego. Survei lapangan MAPID Apps: kisaran Rp20.000–30.000 di pangkalan ini. Pangkalan aktif 06.00–22.00; becak dimodelkan sebagai penghubung titik-ke-titik, bukan rute tetap.",
  },
  {
    mode: "KRL YOGYA–SOLO",
    key: "krl",
    title: "Lempuyangan → Stasiun Brambanan",
    sub: "13,4 km · 22 mnt · Rp8.000",
    detail:
      "Dimodelkan dengan headway ±30 mnt, bukan jadwal per menit — tidak ada feed real-time untuk layanan ini. Waktu tunggu rata-rata sudah termasuk.",
  },
  {
    mode: "JALAN KAKI",
    key: "walk",
    title: "Stasiun Brambanan → Pangkalan Andong",
    sub: "180 m · 2 mnt · Rp0",
    detail: "Keluar pintu barat stasiun, pangkalan andong ada di seberang jalan.",
  },
  {
    mode: "ANDONG",
    key: "gold",
    title: "Pangkalan Brambanan → Candi Prambanan",
    sub: "1,3 km · 11 mnt · Rp30.000",
    detail:
      "Tarif nego, kisaran survei Rp25.000–35.000. Turun di Gerbang Timur; 6 kusir terdata pada pangkalan ini.",
  },
];

export const SAMPLE_ROUTE_SUMMARY = ["51 MNT", "RP63.000", "17,1 KM", "2 TRANSFER"];

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
  { id: "transit", backendId: "transit", name: "Transportasi Publik", meta: "3 OPERATOR · 214 HALTE", on: true, color: "#1f6592" },
  { id: "pangkalan", backendId: "pangkalan", name: "Pangkalan Andong & Becak", meta: "42 TITIK · SURVEI LAPANGAN", on: true, color: "#7c5e13" },
  { id: "pariwisata", backendId: "poi", name: "Pariwisata & Sosial Budaya", meta: "96 TITIK", on: false, color: "#5b3a8e" },
  { id: "properti", backendId: "properti", name: "Properti", meta: "310 TITIK · PROPERTI GO", on: false, color: "#17293a" },
  { id: "jangkauan", backendId: null, name: "Jangkauan Jalan Kaki", meta: "ISOKRON 5 / 10 / 15 MNT", on: false, color: "#c6d9e8" },
  { id: "bangunan", backendId: null, name: "Bangunan", meta: "URBAN PLANNING · FILL 12%", on: false, color: "rgba(23,41,58,.12)" },
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
  "Rute tercepat: jalan kaki ke pangkalan becak Sosrowijayan, becak ke Stasiun Lempuyangan, KRL Yogya–Solo ke Brambanan, lalu andong ke gerbang candi. Total 51 menit, Rp63.000, 17,1 km. Rutenya sudah saya tandai di peta.";

export const REPLY_GENERIC =
  "Saya perlu titik awal untuk menghitungnya. Sebutkan lokasi Anda sekarang, atau ketuk ikon lokasi di peta — layer TransJogja sudah aktif jadi haltenya sudah terlihat.";

export const RECENT = [
  { title: "Candi Prambanan", meta: "3 HARI LALU", prompt: "Malioboro → Candi Prambanan", route: true },
  { title: "Stasiun YIA", meta: "1 PEKAN LALU", prompt: "Rute termurah ke YIA", route: false },
];

export const SAMPLE_POI = {
  kicker: "ANDONG",
  name: "Pangkalan Andong Brambanan",
  meta: "Rp25.000–35.000 · 06.00–21.00 · 6 kusir terdata",
};

export const SAMPLE_CARBON = {
  trip: "2,41 kg",
  month: "18,6 kg",
  trips: "12",
  basis:
    "Dasar perhitungan: 17,1 km dengan KRL, becak dan andong, dibandingkan mobil pribadi berisi satu penumpang untuk jarak yang sama.",
  source: "SOURCE · KLHK (2023) · IPCC 2006 TIER 1",
  caveat: "SAMPLE DATA — FACTORS NOT YET LOADED FROM DB",
};

/** The design's sample route mirrors the alternative offer under the timeline. */
export const SAMPLE_ALTERNATIVE = {
  kicker: "ALTERNATIVE · LEBIH MURAH",
  title: "TransJogja 1A → KRL, tanpa becak",
  sub: "63 mnt · Rp45.000 · jalan kaki 640 m lebih jauh",
};
