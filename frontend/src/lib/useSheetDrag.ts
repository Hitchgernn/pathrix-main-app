import { useRef } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import type { AgentSnap } from "../store";
import { useStore } from "../store";
import { snapPoints } from "./useWindowSize";

const MOVE_THRESHOLD_PX = 3;

/** Direct-manipulation drag for the agent sheet.
 *
 *  A drag that never crossed the threshold is a tap, and cycles the snap point
 *  instead — so the handle works with a thumb and with a mouse.
 */
export function useSheetDrag(vh: number) {
  const setDragH = useStore((s) => s.setDragH);
  const setAgentSnap = useStore((s) => s.setAgentSnap);
  const cycleAgentSnap = useStore((s) => s.cycleAgentSnap);
  const drag = useRef<{ y: number; h: number; moved: boolean } | null>(null);

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    const snap = useStore.getState().agentSnap;
    drag.current = { y: event.clientY, h: snapPoints(vh)[snap], moved: false };
    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch {
      // Pointer capture is best-effort; the drag still tracks without it.
    }
  };

  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const current = drag.current;
    if (!current) return;
    const dy = current.y - event.clientY;
    if (Math.abs(dy) > MOVE_THRESHOLD_PX) current.moved = true;
    const points = snapPoints(vh);
    setDragH(Math.max(points.peek, Math.min(points.full, current.h + dy)));
  };

  const onPointerUp = () => {
    const current = drag.current;
    drag.current = null;
    if (!current) return;

    const height = useStore.getState().dragH;
    if (!current.moved || height == null) {
      setDragH(null);
      if (!current.moved) cycleAgentSnap();
      return;
    }

    const points = snapPoints(vh);
    const nearest = (["peek", "half", "full"] as AgentSnap[]).reduce((best, key) =>
      Math.abs(points[key] - height) < Math.abs(points[best] - height) ? key : best,
    );
    setAgentSnap(nearest);
  };

  return { onPointerDown, onPointerMove, onPointerUp };
}
