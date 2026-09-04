/** Browser geolocation, wrapped so the UI only ever deals with a Place-shaped
 *  answer and a permission verdict.
 *
 *  Denial is a first-class path, not an error: Yogyakarta's Kraton is the
 *  fallback camera and the whole app works without ever knowing where you are.
 */

export type PermissionOutcome = "granted" | "denied";

export interface LocationFix {
  outcome: PermissionOutcome;
  coord: [number, number] | null;
}

const OPTIONS: PositionOptions = {
  enableHighAccuracy: true,
  timeout: 10_000,
  maximumAge: 60_000,
};

export function requestLocation(): Promise<LocationFix> {
  if (typeof navigator === "undefined" || !navigator.geolocation) {
    return Promise.resolve({ outcome: "denied", coord: null });
  }
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({
          outcome: "granted",
          coord: [position.coords.longitude, position.coords.latitude],
        }),
      // A timeout and a hard refusal are the same thing to the UI: we do not
      // have a position, so keep going with the default camera.
      () => resolve({ outcome: "denied", coord: null }),
      OPTIONS,
    );
  });
}
