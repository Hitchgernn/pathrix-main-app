"""Turn the Bakpia mascot contact sheet into a real sprite sheet.

The source (`spritesheet_source.png`) is a *labeled contact sheet*, not a sprite
sheet: it carries a title, per-row labels, a white background, and is drawn at
5x with no anti-aliasing. None of the geometry below is guessable from the file,
so it is pinned here and asserted on every run.

    python extract.py     ->  ../../src/assets/bakpia-mascot.png
"""

from pathlib import Path

import numpy as np
from PIL import Image

SOURCE = Path(__file__).parent / "spritesheet_source.png"
TARGET = Path(__file__).parents[2] / "src" / "assets" / "bakpia-mascot.png"

# Cell origins on the contact sheet. Pitch is 172px on both axes.
LEFTS = (165, 337, 509, 681)
TOPS = (55, 227, 399, 571, 743)
ROWS = ("idle", "walk_right", "walk_left", "wave", "jump")

# Within every cell the pixel-art block grid starts at (+5, +5) and each block
# is exactly 5x5. A uniform 145x160 crop at that offset holds all the ink in
# every cell, so frame-to-frame offsets -- the animation itself -- survive
# without per-frame trimming.
OFFSET = 5
BLOCK = 5
CROP_W, CROP_H = 145, 160
FRAME_W, FRAME_H = CROP_W // BLOCK, CROP_H // BLOCK  # 29 x 32


def main() -> None:
    source = np.array(Image.open(SOURCE).convert("RGB"))
    sheet = Image.new("RGBA", (FRAME_W * len(LEFTS), FRAME_H * len(TOPS)), (0, 0, 0, 0))

    for row, top in enumerate(TOPS):
        for col, left in enumerate(LEFTS):
            y, x = top + OFFSET, left + OFFSET
            crop = source[y : y + CROP_H, x : x + CROP_W]
            assert crop.shape == (CROP_H, CROP_W, 3), f"{ROWS[row]} {col}: crop ran off the sheet"

            # Every 5x5 block must be one flat colour, or the downscale below
            # would be lossy and the geometry above is wrong for this source.
            blocks = crop.reshape(CROP_H // BLOCK, BLOCK, CROP_W // BLOCK, BLOCK, 3)
            assert (blocks == blocks[:, :1, :, :1]).all(), f"{ROWS[row]} {col}: not on the 5px block grid"

            # And no ink may sit outside the crop, or a frame is being clipped.
            cell = source[top : top + 172, left : min(left + 172, source.shape[1])].copy()
            cell[OFFSET : OFFSET + CROP_H, OFFSET : OFFSET + CROP_W] = 255
            assert not (cell.sum(axis=2) < 720).any(), f"{ROWS[row]} {col}: ink outside the crop"

            frame = crop[::BLOCK, ::BLOCK]
            # The background is pure white with no white anywhere inside a
            # sprite, so keying it is exact rather than a threshold.
            alpha = np.where((frame == 255).all(axis=2), 0, 255).astype(np.uint8)
            sheet.paste(Image.fromarray(np.dstack([frame, alpha]), "RGBA"), (col * FRAME_W, row * FRAME_H))

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(TARGET, "PNG", optimize=True)
    print(f"{TARGET.relative_to(Path.cwd()) if TARGET.is_relative_to(Path.cwd()) else TARGET}"
          f" -- {sheet.width}x{sheet.height}, {TARGET.stat().st_size} bytes,"
          f" {len(ROWS)} clips x {len(LEFTS)} frames of {FRAME_W}x{FRAME_H}")


if __name__ == "__main__":
    main()
