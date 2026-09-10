import { useState } from "react";

import sheet from "../assets/bakpia-mascot.png";
import { Sprite, prefersReducedMotion } from "./Sprite";

const FRAME = [29, 32] as const;
const CLIPS_ON_SHEET = 5;

/** One entry per animated clip. `jump` (clip 4) is deliberately out of the
 *  pool: it reads as celebration rather than work, and its vertical travel
 *  makes the whole row jitter against the text beside it. It stays on the sheet
 *  for a future "done" beat. */
const POOL = [
  { clip: 0, ms: 900 }, // idle
  { clip: 1, ms: 640 }, // walk right
  { clip: 2, ms: 640 }, // walk left
  { clip: 3, ms: 760 }, // wave
] as const;

const IDLE = POOL[0];

function pick() {
  // Reduced motion still renders the mascot, it just holds still — and it holds
  // still on a rest pose rather than on a raised leg or a raised arm. The CSS
  // animation itself is already flattened globally in styles/index.css.
  return prefersReducedMotion() ? IDLE : POOL[Math.floor(Math.random() * POOL.length)];
}

/** The Bakpia mascot, animated while the agent works.
 *
 *  A clip is picked once per mount, and the mascot is mounted only while
 *  `streaming` is true, so each question gets its own.
 */
export function MascotThinking() {
  const [{ clip, ms }] = useState(pick);
  return (
    <Sprite
      sheet={sheet}
      frame={FRAME}
      frames={4}
      clips={CLIPS_ON_SHEET}
      clip={clip}
      scale={2}
      ms={ms}
      className="flex-none"
    />
  );
}
