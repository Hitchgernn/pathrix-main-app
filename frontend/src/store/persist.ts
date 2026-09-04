import type { Place, RecentEntry, SavedRoute } from "../lib/places";

/** Everything the app remembers between sessions, in localStorage.
 *
 *  There is no auth and no user table in the backend (`ARCHITECTURE.md` §5.1
 *  has no users), so "your profile" is genuinely this device's profile. The
 *  Profile screen says so out loud rather than implying an account that does
 *  not exist.
 */

const KEY = "pathrix.v1";
const RECENTS_CAP = 8;

export type LocationPermission = "unknown" | "granted" | "denied";

export interface Profile {
  name: string;
  /** Data URL or remote URL. Null renders initials instead. */
  avatar: string | null;
}

export interface PersistedState {
  profile: Profile;
  savedPlaces: Place[];
  savedRoutes: SavedRoute[];
  recents: RecentEntry[];
  locationPermission: LocationPermission;
  onboarded: boolean;
}

export const EMPTY_PERSISTED: PersistedState = {
  profile: { name: "Tamu", avatar: null },
  savedPlaces: [],
  savedRoutes: [],
  recents: [],
  locationPermission: "unknown",
  onboarded: false,
};

const isArray = <T,>(value: unknown): T[] => (Array.isArray(value) ? (value as T[]) : []);

/** Reads defensively: a missing key, a quota-blocked read, a half-written value
 *  from an older build, or a hand-edited entry all fall back to defaults rather
 *  than taking the app down on boot. */
export function loadPersisted(): PersistedState {
  if (typeof window === "undefined") return EMPTY_PERSISTED;
  let parsed: unknown;
  try {
    const stored = window.localStorage.getItem(KEY);
    if (!stored) return EMPTY_PERSISTED;
    parsed = JSON.parse(stored);
  } catch {
    return EMPTY_PERSISTED;
  }
  if (typeof parsed !== "object" || parsed === null) return EMPTY_PERSISTED;

  const raw = parsed as Partial<PersistedState>;
  const profile = raw.profile;
  return {
    profile: {
      name:
        typeof profile?.name === "string" && profile.name.trim()
          ? profile.name.trim()
          : EMPTY_PERSISTED.profile.name,
      avatar: typeof profile?.avatar === "string" ? profile.avatar : null,
    },
    savedPlaces: isArray<Place>(raw.savedPlaces).filter((p) => p && typeof p.id === "string"),
    savedRoutes: isArray<SavedRoute>(raw.savedRoutes).filter((r) => r && typeof r.id === "string"),
    recents: isArray<RecentEntry>(raw.recents).filter((r) => r && typeof r.prompt === "string"),
    locationPermission:
      raw.locationPermission === "granted" || raw.locationPermission === "denied"
        ? raw.locationPermission
        : "unknown",
    onboarded: raw.onboarded === true,
  };
}

let writeTimer: number | null = null;

/** Debounced, and silent on failure — Safari private mode and a full quota both
 *  throw on setItem, and neither is a reason to interrupt someone mid-journey. */
export function savePersisted(state: PersistedState): void {
  if (typeof window === "undefined") return;
  if (writeTimer !== null) window.clearTimeout(writeTimer);
  writeTimer = window.setTimeout(() => {
    writeTimer = null;
    try {
      window.localStorage.setItem(KEY, JSON.stringify(state));
    } catch {
      /* storage unavailable — the session still works, it just won't persist */
    }
  }, 250);
}

export function clearPersisted(): void {
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    /* nothing to do */
  }
}

export const capRecents = (recents: RecentEntry[]): RecentEntry[] =>
  recents.slice(0, RECENTS_CAP);
