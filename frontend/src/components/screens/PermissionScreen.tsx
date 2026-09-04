import { useState } from "react";
import { requestLocation } from "../../lib/geolocation";
import { useStore } from "../../store";

/** Shown once, the first time someone opens the map.
 *
 *  Asking before the browser's own prompt fires is the point: a cold permission
 *  dialog with no context is the one most people dismiss, and a dismissal is
 *  hard to undo. Declining here is a real, complete path — the app opens on the
 *  Kraton and everything except "near me" works exactly the same.
 */
export function PermissionScreen() {
  const setOnboarded = useStore((s) => s.setOnboarded);
  const setPermission = useStore((s) => s.setLocationPermission);
  const setUserCoord = useStore((s) => s.setUserCoord);
  const [asking, setAsking] = useState(false);

  const allow = async () => {
    setAsking(true);
    const fix = await requestLocation();
    setPermission(fix.outcome);
    setUserCoord(fix.coord);
    setOnboarded(true);
  };

  return (
    <div className="absolute inset-0 z-[80] flex animate-pxfade flex-col bg-surface">
      <div className="mx-auto flex w-full max-w-[440px] flex-1 flex-col px-6 pb-8 pt-16">
        <div className="flex flex-1 flex-col items-center justify-center text-center">
          <LocationMark />
          <h1 className="title-lg mt-8">Izinkan akses lokasi</h1>
          <p className="body-15 mt-3 max-w-[34ch] text-ink-2">
            Dipakai untuk menunjukkan halte, pangkalan andong dan becak terdekat, serta menghitung
            rute dari posisi Anda.
          </p>
          <p className="body-13 mt-4 max-w-[34ch] text-ink-3">
            Lokasi diproses di perangkat dan dikirim ke server hanya sebagai titik awal rute. Anda
            bisa mengubahnya kapan saja di Profil.
          </p>
        </div>

        <button
          onClick={() => void allow()}
          disabled={asking}
          className="w-full rounded-control bg-ink px-[22px] py-[16px] text-[16px] font-semibold tracking-[-.01em] text-surface transition-colors hover:bg-ink/90 disabled:opacity-60"
        >
          {asking ? "Menunggu izin…" : "Izinkan akses"}
        </button>
        <button
          onClick={() => {
            setPermission("denied");
            setOnboarded(true);
          }}
          className="mt-2 w-full rounded-control px-[22px] py-[14px] text-[15px] font-semibold text-ink-2 transition-colors hover:bg-surface-2"
        >
          Nanti saja — buka peta Yogyakarta
        </button>
      </div>
    </div>
  );
}

/** A pin dropped on a coordinate grid, in the app's own line language: the
 *  graticule is the instrument, the pin is you on it. */
function LocationMark() {
  return (
    <svg viewBox="0 0 132 132" width="132" height="132" fill="none" aria-hidden>
      <circle cx="66" cy="66" r="55" fill="var(--color-surface-3)" />
      <g stroke="var(--color-ink)" strokeWidth="1" opacity=".18">
        <path d="M11 66h110M66 11v110" />
        <circle cx="66" cy="66" r="34" />
        <circle cx="66" cy="66" r="18" />
      </g>
      <path
        d="M66 40c-8.8 0-16 7.1-16 15.9 0 11.2 14.3 24.9 15 25.5.6.5 1.5.5 2.1 0 .7-.6 15-14.3 15-25.5C82 47.1 74.8 40 66 40Z"
        fill="var(--color-ink)"
      />
      <circle cx="66" cy="56" r="5.6" fill="var(--color-gold)" />
      <ellipse cx="66" cy="90" rx="13" ry="3.4" fill="var(--color-ink)" opacity=".14" />
    </svg>
  );
}
