"""Turn the Bakpia contact sheets into real sprite sheets.

Each source is a *labeled contact sheet*, not a sprite sheet: it carries a
title, per-row labels, a white background, and is drawn at an integer zoom with
no anti-aliasing. None of the geometry in SHEETS is guessable from the files, so
it is pinned here and asserted on every run.

    python extract.py     ->  ../../src/assets/*.png
"""

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).parent
ASSETS = Path(__file__).parents[2] / "src" / "assets"

SHEETS = (
    {
        "source": "mascot_source.png",
        "target": "bakpia-mascot.png",
        # Cell origins. Pitch is 172px on both axes.
        "lefts": (165, 337, 509, 681),
        "tops": (55, 227, 399, 571, 743),
        "rows": ("idle", "walk_right", "walk_left", "wave", "jump"),
        # Within every cell the pixel-art block grid starts at this offset and
        # each block is exactly `block` square. A uniform crop of `frame` holds
        # all the ink in every cell, so frame-to-frame offsets -- the animation
        # itself -- survive without per-frame trimming.
        "block": 5,
        "offset": (5, 5),
        "frame": (145, 160),
        "cell": (172, 172),
    },
    {
        "source": "earth_source.png",
        "target": "bakpia-earth.png",
        "lefts": (186, 462, 738, 1014),
        "tops": (54, 342, 630, 918),
        "rows": ("idle", "walk", "jump", "wave"),
        "block": 6,
        "offset": (6, 6),
        "frame": (204, 276),
        "cell": (276, 288),
    },
)


def background(frame: np.ndarray) -> np.ndarray:
    """White reachable from the edge of the frame.

    A flat colour test would also punch out white *inside* the art -- the eye
    highlights on the Earth sheet -- so the background is found by reach rather
    than by value.
    """
    white = (frame == 255).all(axis=2)
    h, w = white.shape
    seen = np.zeros_like(white)
    queue: deque[tuple[int, int]] = deque()
    edges = [(y, x) for y in range(h) for x in (0, w - 1)]
    edges += [(y, x) for x in range(w) for y in (0, h - 1)]
    for y, x in edges:
        if white[y, x] and not seen[y, x]:
            seen[y, x] = True
            queue.append((y, x))
    while queue:
        y, x = queue.popleft()
        for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= ny < h and 0 <= nx < w and white[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                queue.append((ny, nx))
    return seen


def extract(spec: dict) -> None:
    source = np.array(Image.open(HERE / spec["source"]).convert("RGB"))
    block = spec["block"]
    off_x, off_y = spec["offset"]
    crop_w, crop_h = spec["frame"]
    cell_w, cell_h = spec["cell"]
    frame_w, frame_h = crop_w // block, crop_h // block

    sheet = Image.new(
        "RGBA", (frame_w * len(spec["lefts"]), frame_h * len(spec["tops"])), (0, 0, 0, 0)
    )

    for row, top in enumerate(spec["tops"]):
        for col, left in enumerate(spec["lefts"]):
            where = f"{spec['rows'][row]} {col}"
            y, x = top + off_y, left + off_x
            crop = source[y : y + crop_h, x : x + crop_w]
            assert crop.shape == (crop_h, crop_w, 3), f"{where}: crop ran off the sheet"

            # Every block must be one flat colour, or the downscale below would
            # be lossy and the geometry above is wrong for this source.
            blocks = crop.reshape(crop_h // block, block, crop_w // block, block, 3)
            assert (blocks == blocks[:, :1, :, :1]).all(), f"{where}: not on the {block}px block grid"

            # And no ink may sit outside the crop, or a frame is being clipped.
            cell = source[top : top + cell_h, left : min(left + cell_w, source.shape[1])].copy()
            cell[off_y : off_y + crop_h, off_x : off_x + crop_w] = 255
            assert not (cell.sum(axis=2) < 720).any(), f"{where}: ink outside the crop"

            frame = crop[::block, ::block]
            alpha = np.where(background(frame), 0, 255).astype(np.uint8)
            sheet.paste(
                Image.fromarray(np.dstack([frame, alpha]), "RGBA"),
                (col * frame_w, row * frame_h),
            )

    target = ASSETS / spec["target"]
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, "PNG", optimize=True)
    print(
        f"{spec['target']} -- {sheet.width}x{sheet.height}, {target.stat().st_size} bytes,"
        f" {len(spec['rows'])} clips x {len(spec['lefts'])} frames of {frame_w}x{frame_h}"
    )


if __name__ == "__main__":
    for sheet_spec in SHEETS:
        extract(sheet_spec)
