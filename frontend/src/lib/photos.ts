/** Real photographs for real places, from Wikipedia's REST summary endpoint.
 *
 *  The backend has nowhere to serve a photo from yet: `poi.foto_url` and
 *  `pangkalan.photo_url` exist in the schema but stay empty until the field
 *  survey is digitized. Rather than fill that gap with stock imagery — which
 *  would put a photograph of somewhere else under the name of a real halte —
 *  this resolves named Yogyakarta landmarks against Wikipedia and returns
 *  nothing at all for anything it cannot honestly identify.
 *
 *  Keyless, CORS-open, and cached for a week: place photographs are about as
 *  stable as data gets. A miss is a normal answer, never an error.
 */

const ENDPOINT = "https://id.wikipedia.org/api/rest_v1/page/summary";
const CACHE_KEY = "pathrix.photos.v1";
const CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000;

export interface Photo {
  url: string;
  /** Shown beneath the image. Wikipedia's licence expects attribution. */
  credit: string;
  /** Where the credit points. */
  href: string;
}

/** Names the app itself uses, mapped to the article that actually depicts them.
 *  Hand-curated rather than guessed: a fuzzy title search returns a photograph
 *  of *something*, which is exactly the failure mode this module exists to
 *  avoid. */
const ARTICLES: Record<string, string> = {
  malioboro: "Jalan_Malioboro",
  prambanan: "Candi_Prambanan",
  "candi prambanan": "Candi_Prambanan",
  borobudur: "Borobudur",
  tugu: "Tugu_Yogyakarta",
  "tugu jogja": "Tugu_Yogyakarta",
  kraton: "Keraton_Ngayogyakarta_Hadiningrat",
  keraton: "Keraton_Ngayogyakarta_Hadiningrat",
  "taman sari": "Taman_Sari,_Yogyakarta",
  lempuyangan: "Stasiun_Lempuyangan",
  "stasiun lempuyangan": "Stasiun_Lempuyangan",
  "stasiun tugu": "Stasiun_Yogyakarta",
  "stasiun yogyakarta": "Stasiun_Yogyakarta",
  yia: "Bandar_Udara_Internasional_Yogyakarta",
  "stasiun yia": "Bandar_Udara_Internasional_Yogyakarta",
  brambanan: "Stasiun_Brambanan",
  "stasiun brambanan": "Stasiun_Brambanan",
  transjogja: "Trans_Jogja",
  "trans jogja": "Trans_Jogja",
  krl: "KRL_Commuter_Line_Yogyakarta–Palur",
  andong: "Andong_(kendaraan)",
  becak: "Becak",
  parangtritis: "Pantai_Parangtritis",
  yogyakarta: "Kota_Yogyakarta",
};

type CacheEntry = { photo: Photo | null; at: number };

const memory = new Map<string, Promise<Photo | null>>();

function readCache(): Record<string, CacheEntry> {
  try {
    const raw = window.localStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as Record<string, CacheEntry>) : {};
  } catch {
    return {};
  }
}

function writeCache(key: string, entry: CacheEntry): void {
  try {
    const all = readCache();
    all[key] = entry;
    window.localStorage.setItem(CACHE_KEY, JSON.stringify(all));
  } catch {
    /* private mode or quota — the in-memory map still spares repeat fetches */
  }
}

/** Longest match wins, so "Stasiun Lempuyangan" does not resolve on the bare
 *  word "stasiun" that a shorter key would have caught. */
export function articleFor(name: string): string | null {
  const haystack = name.toLowerCase();
  let best: string | null = null;
  for (const key of Object.keys(ARTICLES)) {
    if (haystack.includes(key) && (best === null || key.length > best.length)) {
      best = key;
    }
  }
  return best ? ARTICLES[best] : null;
}

/** A photograph of this place, or null when we cannot honestly name one. */
export function photoFor(name: string): Promise<Photo | null> {
  const article = articleFor(name);
  if (!article) return Promise.resolve(null);

  const cached = readCache()[article];
  if (cached && Date.now() - cached.at < CACHE_TTL_MS) {
    return Promise.resolve(cached.photo);
  }

  const existing = memory.get(article);
  if (existing) return existing;

  const request = fetch(`${ENDPOINT}/${encodeURIComponent(article)}`)
    .then((response) => (response.ok ? response.json() : null))
    .then((data: WikiSummary | null): Photo | null => {
      const url = data?.thumbnail?.source ?? null;
      if (!url) return null;
      return {
        // Wikipedia's own thumbnails cap around 320px; ask for a width that
        // survives a full-bleed hero on a 3x screen.
        url: url.replace(/\/\d+px-/, "/960px-"),
        credit: "Wikimedia Commons",
        href: data?.content_urls?.desktop?.page ?? `https://id.wikipedia.org/wiki/${article}`,
      };
    })
    .catch(() => null)
    .then((photo) => {
      writeCache(article, { photo, at: Date.now() });
      return photo;
    });

  memory.set(article, request);
  return request;
}

interface WikiSummary {
  thumbnail?: { source?: string };
  content_urls?: { desktop?: { page?: string } };
}
