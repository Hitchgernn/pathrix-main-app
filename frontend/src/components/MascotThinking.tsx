import { useState } from "react";

import sheet from "../assets/bakpia-mascot.png";

/** Native frame size on `bakpia-mascot.png`, and the integer factor it is drawn
 *  at. Pixel art may only scale by whole numbers; 3x (87x96) swamps a 13px step
 *  list, so 2x it is. */
const FRAME_W = 29;
const FRAME_H = 32;
const SCALE = 2;
const FRAMES = 4;
/** Rows on the sheet, including `jump`, which the pool below skips. */
const SHEET_ROWS = 5;

const WIDTH = FRAME_W * SCALE;
const HEIGHT = FRAME_H * SCALE;

/** One entry per animated row of the sheet. `jump` (row 4) is deliberately out
 *  of the pool: it reads as celebration rather than work, and its vertical
 *  travel makes the whole row jitter against the text beside it. It stays in
 *  the sheet for a future "done" beat. */
const CLIPS = [
  { row: 0, ms: 900 }, // idle
  { row: 1, ms: 640 }, // walk right
  { row: 2, ms: 640 }, // walk left
  { row: 3, ms: 760 }, // wave
] as const;

const IDLE = CLIPS[0];

function pickClip() {
  // Reduced motion still renders the mascot, it just holds still — and it holds
  // still on a rest pose rather than on a raised leg or a raised arm. The CSS
  // animation itself is already flattened globally in styles/index.css.
  if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return IDLE;
  return CLIPS[Math.floor(Math.random() * CLIPS.length)];
}

/** The Bakpia mascot, animated while the agent works.
 *
 *  Decorative on purpose: it is `aria-hidden`, and the words beside it — the
 *  stepped list, or the calculating label — remain the status. See the Mascot
 *  section of docs/DESIGN.md for why this is not the animated loading icon the
 *  same document bans.
 *
 *  A clip is picked once per mount, and the mascot is mounted only while
 *  `streaming` is true, so each question gets its own.
 */
export function MascotThinking() {
  const [clip] = useState(pickClip);
  return (
    <div
      aria-hidden="true"
      className="flex-none"
      style={{
        width: WIDTH,
        height: HEIGHT,
        backgroundImage: `url(${sheet})`,
        backgroundSize: `${FRAMES * WIDTH}px ${SHEET_ROWS * HEIGHT}px`,
        backgroundPositionY: `${-clip.row * HEIGHT}px`,
        backgroundRepeat: "no-repeat",
        imageRendering: "pixelated",
        animation: `mascotStep ${clip.ms}ms steps(${FRAMES}) infinite`,
      }}
    />
  );
}
