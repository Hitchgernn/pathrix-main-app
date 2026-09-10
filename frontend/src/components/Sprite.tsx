import type { CSSProperties } from "react";

interface SpriteProps {
  /** Imported sprite sheet. Frames run left to right, clips top to bottom. */
  sheet: string;
  /** Native frame size, before `scale`. */
  frame: readonly [number, number];
  /** Frames per clip, and clips on the sheet — both needed to place the sheet
   *  behind a one-frame window. */
  frames: number;
  clips: number;
  /** Which clip to play. */
  clip: number;
  /** Whole numbers only. Pixel art resampled at a fraction turns to mush, and
   *  there is no half-step, so a size is chosen off this ladder rather than
   *  from a spec. */
  scale: number;
  /** One full cycle. */
  ms: number;
  className?: string;
}

/** A pixel-art sprite sheet played as a CSS `steps()` walk across a background
 *  image — no canvas, no rAF, no JS running per frame.
 *
 *  Decorative by construction: `aria-hidden`, and nothing it can show is
 *  information the surrounding words don't already carry. See the Mascot
 *  section of docs/DESIGN.md.
 */
export function Sprite({ sheet, frame, frames, clips, clip, scale, ms, className }: SpriteProps) {
  const width = frame[0] * scale;
  const height = frame[1] * scale;
  const style = {
    width,
    height,
    backgroundImage: `url(${sheet})`,
    backgroundSize: `${frames * width}px ${clips * height}px`,
    backgroundPositionY: `${-clip * height}px`,
    backgroundRepeat: "no-repeat",
    imageRendering: "pixelated",
    // How far `spriteStep` travels. It varies per sheet and per scale, so the
    // keyframe reads it from here rather than hard-coding one sheet's width.
    "--sprite-travel": `${-frames * width}px`,
    animation: `spriteStep ${ms}ms steps(${frames}) infinite`,
  } as CSSProperties;
  return <div aria-hidden="true" className={className} style={style} />;
}

/** True when the OS asks for less movement. Read at call time rather than
 *  subscribed to: every caller uses it to pick something once, at mount, and
 *  the CSS in styles/index.css is what actually stops the motion. */
export const prefersReducedMotion = () =>
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
