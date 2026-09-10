import { useState } from "react";
import { useT } from "../../i18n";
import { requestLocation } from "../../lib/geolocation";
import { useStore } from "../../store";
import earth from "../../assets/bakpia-earth.png";
import { Sprite } from "../Sprite";

/** Shown once, the first time someone opens the map.
 *
 *  Standing in front of the browser's own prompt is the point: that dialog is
 *  the one most people dismiss, and a dismissal is hard to undo, so the choice
 *  is offered here first where declining is a real, complete path — the app
 *  opens on the Kraton and everything except "near me" works exactly the same.
 *
 *  The screen deliberately does not explain itself beyond the question — the
 *  mascot and the title are the whole of it. The answer is not final either
 *  way: Profil carries a location row showing the current state with a control
 *  to change it.
 */
export function PermissionScreen() {
  const setOnboarded = useStore((s) => s.setOnboarded);
  const setPermission = useStore((s) => s.setLocationPermission);
  const setUserCoord = useStore((s) => s.setUserCoord);
  const [asking, setAsking] = useState(false);
  const t = useT();

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
          <EarthMark />
          <h1 className="title-lg mt-8">{t("perm.title")}</h1>
        </div>

        <button
          onClick={() => void allow()}
          disabled={asking}
          className="w-full rounded-control bg-ink px-[22px] py-[16px] text-[16px] font-semibold tracking-[-.01em] text-surface transition-colors hover:bg-ink/90 disabled:opacity-60"
        >
          {t(asking ? "perm.waiting" : "perm.allow")}
        </button>
        <button
          onClick={() => {
            setPermission("denied");
            setOnboarded(true);
          }}
          className="mt-2 w-full rounded-control px-[22px] py-[14px] text-[15px] font-semibold text-ink-2 transition-colors hover:bg-surface-2"
        >
          {t("perm.later")}
        </button>
      </div>
    </div>
  );
}

/** The mascot waving from the top of the Earth.
 *
 *  This replaces a drawn pin-on-a-graticule. The pin said "we will put a marker
 *  where you are", which is not what the screen is asking for — it is asking
 *  permission, and a greeting is the honest illustration of that. It is also
 *  the one screen in the app with room for a mascot at full size.
 *
 *  `wave` rather than a random clip: this screen is shown once, so there is
 *  nothing for variety to relieve, and it is the only clip whose every frame
 *  reads on its own — `walk` runs off the edge of the frame and `jump` leaves
 *  the mascot mid-air and cropped.
 */
function EarthMark() {
  return <Sprite sheet={earth} frame={[34, 46]} frames={4} clips={4} clip={3} scale={4} ms={760} />;
}
