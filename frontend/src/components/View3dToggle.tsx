import { Box } from "lucide-react";
import { useT } from "../i18n";
import { useStore } from "../store";

/** Tilts the map and stands the buildings up.
 *
 *  A round icon control rather than a "3D" pill: docs/DESIGN.md keeps this
 *  corner to round controls, and mono — the only face a bare figure could be
 *  set in — is reserved for real figures. Same 38px grammar as the carbon FAB
 *  beside it.
 */
export function View3dToggle() {
  const view3d = useStore((s) => s.view3d);
  const setView3d = useStore((s) => s.setView3d);
  const t = useT();
  return (
    <button
      onClick={() => setView3d(!view3d)}
      aria-pressed={view3d}
      aria-label={t(view3d ? "map.view2d" : "map.view3d")}
      className={`pointer-events-auto flex h-[38px] w-[38px] items-center justify-center rounded-full shadow-card transition-colors ${
        view3d ? "bg-ink text-surface" : "surface-float text-ink-2 ring-1 ring-line"
      }`}
    >
      <Box size={17} strokeWidth={1.9} />
    </button>
  );
}
