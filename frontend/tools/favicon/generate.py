"""Generate favicon / PWA icon PNGs from the two source logo marks.

Run from `frontend/`: `uv run --with pillow python tools/favicon/generate.py`
(or any Python with Pillow on the path). Source files are the two 500x500
RGBA marks in `src/assets/` — `logo-pathrix-black.png` on transparent, used
wherever the icon needs to read against a light background, and
`logo-pathrix-white.png` for a dark background. Re-run this after replacing
either source; nothing else needs to change.
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "src" / "assets"
PUBLIC = ROOT / "public"

BLACK = ASSETS / "logo-pathrix-black.png"
WHITE = ASSETS / "logo-pathrix-white.png"


def resized(source: Path, size: int) -> Image.Image:
    image = Image.open(source).convert("RGBA")
    return image.resize((size, size), Image.LANCZOS)


def on_white(source: Path, size: int) -> Image.Image:
    """Composited onto an opaque white square — transparency renders as a
    solid black box on iOS home screens and looks inconsistent across
    Android launchers, so installable/touch icons get a real background."""
    mark = resized(source, size)
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    canvas.alpha_composite(mark)
    return canvas.convert("RGB")


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)

    # Browser-tab favicons: transparent, theme-matched via `prefers-color-scheme`
    # in index.html. Confirmed against a real browser: the light-mode link
    # wants the white mark, the dark-mode link wants the black mark.
    resized(WHITE, 32).save(PUBLIC / "favicon-32-light.png")
    resized(BLACK, 32).save(PUBLIC / "favicon-32-dark.png")

    # Installable/home-screen icons: opaque background, one static variant.
    on_white(BLACK, 180).save(PUBLIC / "apple-touch-icon.png")
    on_white(BLACK, 192).save(PUBLIC / "pwa-192.png")
    on_white(BLACK, 512).save(PUBLIC / "pwa-512.png")

    print("wrote favicon-32-light.png, favicon-32-dark.png, apple-touch-icon.png, pwa-192.png, pwa-512.png")


if __name__ == "__main__":
    main()
