#!/usr/bin/env python3
"""
Prepare the Subnotes site's screenshot assets.

Takes the same raw device captures the App Store script uses
(Subnotes/tools/make_store_screenshots.py) and produces small, text-free
images sized for this site.

Deliberately NOT the store script's output. Those have the caption baked into
the pixels at 1284x2778 with the alpha stripped — all three wrong here: the
caption would repeat the card's own <h3> in a form no one can select, search or
translate, and the Mac window's transparent corners are worth keeping on a page
whose background changes with the theme.

What this does instead:

  * crops each phone capture from the top of the screen down, keeping the
    status bar and navigation so it reads as an iPhone rather than as a
    floating fragment of UI. The page stands the result on the bottom edge of
    a tinted panel with only its top corners rounded, so the crop looks like a
    screen continuing past the panel rather than an image cut short — which is
    what makes the vertical budget a design choice instead of a problem;
  * scales to 2x the size the image is actually displayed at, no more;
  * keeps alpha on the Mac window, drops it on the phone shots (they're opaque
    rectangles anyway);
  * writes WebP, which every browser this site targets has supported for years.

Usage
-----
    python3 tools/make_web_images.py            # build everything
    python3 tools/make_web_images.py --list     # show the plan, write nothing

Re-run it whenever the captures are re-shot for a new release; point
SOURCE_DIR at that release's raw folder first.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required:  python3 -m pip install --user Pillow")


SOURCE_DIR = Path.home() / "Downloads/Subnotes/screenshots/1.2/raw"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "assets/shots"

# Quality 86 is where these stop getting visibly softer around the small UI
# text; the files are a few tens of KB either side of it, so this is chosen on
# looks rather than weight.
WEBP_QUALITY = 86


@dataclass(frozen=True)
class Shot:
    slug: str
    source: str
    # The band of the capture to keep, as (top, bottom) fractions of its
    # height. The phone shots all start at 0.0 — the status bar and nav are
    # what identify these as an iPhone — and all end at the same fraction so
    # the three panels come out the same height.
    band: tuple[float, float]
    # Width to write, in pixels: 2x the CSS width the <img> is displayed at.
    out_width: int
    # Mac captures sit on transparency with a shadow; phone captures don't.
    keep_alpha: bool = False
    note: str = ""


SHOTS = [
    Shot(
        slug="phone-notes",
        source="2-iPhone-Notes.png",
        # Reaches the tagged tasks under "Before we go" and most of the
        # itinerary — the tags are the whole point of this one.
        band=(0.0, 0.60),
        out_width=768,  # ~300px wide in the page, with 2x to spare
        note="Write it down. Some of it gets done.",
    ),
    Shot(
        slug="phone-today",
        source="3-iPhone-AllTasks.png",
        # Reaches the TODAY and NEXT headings and the first tagged rows.
        band=(0.0, 0.60),
        out_width=768,
        note="You are the boss (not your todo list)",
    ),
    Shot(
        slug="phone-notebooks",
        source="1-iPhone-Notebooks.png",
        # Reaches the Today / All Tasks summary pair and the notebook covers.
        band=(0.0, 0.60),
        out_width=768,
        note="One app, not two",
    ),
    Shot(
        slug="mac-notebooks",
        source="1-Mac-Notebooks.png",
        band=(0.0, 1.0),
        # Shares a row with its text now rather than spanning the page, so it
        # displays at roughly 460px and this is comfortably 2x that.
        out_width=1400,
        keep_alpha=True,
        note="Nothing to learn or lock you in",
    ),
]


def trim_transparent(im: Image.Image) -> Image.Image:
    """Crop away fully transparent margins, keeping the window's own shadow."""
    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im


def build(shot: Shot, dry_run: bool) -> str:
    src = SOURCE_DIR / shot.source
    if not src.exists():
        return f"  SKIP  {shot.slug}: no capture at {src}"

    with Image.open(src) as im:
        im = im.convert("RGBA")
        if shot.keep_alpha:
            im = trim_transparent(im)
        top, bottom = shot.band
        if (top, bottom) != (0.0, 1.0):
            im = im.crop((0, round(im.height * top),
                          im.width, round(im.height * bottom)))
        if not shot.keep_alpha:
            im = im.convert("RGB")

        height = round(im.height * shot.out_width / im.width)
        if shot.out_width > im.width:
            return (f"  SKIP  {shot.slug}: would upscale "
                    f"{im.width}px to {shot.out_width}px")
        im = im.resize((shot.out_width, height), Image.LANCZOS)

        out = OUTPUT_DIR / f"{shot.slug}.webp"
        if dry_run:
            return f"  plan  {shot.slug}.webp  {im.width}x{im.height}  ({shot.note})"

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        im.save(out, "WEBP", quality=WEBP_QUALITY, method=6)

    kb = out.stat().st_size / 1024
    return f"  wrote {out.name}  {im.width}x{im.height}  {kb:.0f} KB"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true",
                        help="show what would be written, write nothing")
    args = parser.parse_args()

    print(f"from {SOURCE_DIR}")
    print(f"into {OUTPUT_DIR}")
    for shot in SHOTS:
        print(build(shot, dry_run=args.list))


if __name__ == "__main__":
    main()
