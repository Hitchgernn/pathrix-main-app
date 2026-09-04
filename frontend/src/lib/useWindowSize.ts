import { useEffect, useState } from "react";
import { WIDE_BREAKPOINT } from "./tokens";
import { useStore } from "../store";

export interface WindowSize {
  vw: number;
  vh: number;
}

const read = (): WindowSize => ({
  vw: typeof window === "undefined" ? 1200 : window.innerWidth,
  vh: typeof window === "undefined" ? 800 : window.innerHeight,
});

/** Sheet heights, the SVG overlay viewBox, and the rail/sheet promotion are all
 *  computed from live viewport pixels — the design does the same. */
export function useWindowSize(): WindowSize {
  const [size, setSize] = useState<WindowSize>(read);
  const setWide = useStore((s) => s.setWide);

  useEffect(() => {
    const onResize = () => {
      const next = read();
      setSize(next);
      setWide(next.vw >= WIDE_BREAKPOINT);
    };
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [setWide]);

  return size;
}

/** Sheet snap points: peek is a fixed handle strip, half and full are fractions
 *  of viewport height. Values are the design's. */
export const snapPoints = (vh: number) => ({
  // Tall enough for the agent header and its composer row — a shorter peek
  // clips the input, which is the one control that must always be reachable.
  peek: 152,
  half: Math.round(vh * 0.46),
  full: Math.round(vh * 0.84),
});
