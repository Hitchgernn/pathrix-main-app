# Bakpia mascot sprite sheet

`spritesheet_source.png` is the artwork as delivered: a *labeled* contact sheet
(title, row labels, white ground, drawn at 5x). `extract.py` crops the 20 frames
off it, downscales them back to their native 29x32, keys the white background to
transparent, and writes `src/assets/bakpia-mascot.png` — a 116x160 sheet of 5
clips (idle, walk_right, walk_left, wave, jump) x 4 frames.

The cell geometry is not recoverable by looking at the file, so it is pinned in
`extract.py` and asserted on every run. Run `python extract.py` (needs Pillow +
numpy) after replacing the source.
