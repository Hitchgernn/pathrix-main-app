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
  "taman sari": "Istana_Air_Taman_Sari",
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
  krl: "Kereta_Rel_Listrik",
  andong: "Andong",
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
    .then(async (response) => {
      // Wikipedia rate-limits bursts with a 429. Returning null for that is
      // right; *caching* it is not, so only a real answer reaches writeCache.
      if (!response.ok) return { photo: null as Photo | null, cacheable: false };
      const data = (await response.json()) as WikiSummary;
      const url = data.thumbnail?.source ?? null;
      // A 200 with no thumbnail is a genuine "this article has no photograph",
      // and that is worth remembering.
      if (!url) return { photo: null as Photo | null, cacheable: true };
      return {
        photo: {
          // Wikipedia's own thumbnails cap around 320px; ask for a width that
          // survives a full-bleed hero on a 3x screen.
          url: url.replace(/\/\d+px-/, "/960px-"),
          credit: "Wikimedia Commons",
          href: data.content_urls?.desktop?.page ?? `https://id.wikipedia.org/wiki/${article}`,
        } as Photo,
        cacheable: true,
      };
    })
    .catch(() => ({ photo: null as Photo | null, cacheable: false }))
    .then(({ photo, cacheable }) => {
      if (cacheable) writeCache(article, { photo, at: Date.now() });
      // A failed lookup must not stick in the in-flight map either, or the
      // whole session keeps replaying one bad moment.
      else memory.delete(article);
      return photo;
    });

  memory.set(article, request);
  return request;
}

interface WikiSummary {
  thumbnail?: { source?: string };
  content_urls?: { desktop?: { page?: string } };
}
