#!/usr/bin/env python3
"""Generate typographic cover for one speaking entry (800x500 JPG)."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

V1 = Path(__file__).resolve().parents[1]
MEDIA = V1 / "snapshot" / "2026-06-05" / "_media"

W, H = 800, 500
BG = (18, 18, 18)
FG = (245, 245, 245)
MUTED = (140, 140, 140)
ACCENT = (90, 90, 90)


def load_font(size):
    candidates = [
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def text_w(draw, s, font):
    bbox = draw.textbbox((0, 0), s, font=font)
    return bbox[2] - bbox[0]


def render(tag, year, kind, slug):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    margin = 28
    tick = 12

    for (x, y) in [
        (margin, margin),
        (W - margin, margin),
        (margin, H - margin),
        (W - margin, H - margin),
    ]:
        dx = tick if x == margin else -tick
        dy = tick if y == margin else -tick
        draw.line([(x, y), (x + dx, y)], fill=ACCENT, width=1)
        draw.line([(x, y), (x, y + dy)], fill=ACCENT, width=1)

    tag_font = load_font(15)
    draw.text((margin + 16, margin + 6), tag.upper(), font=tag_font, fill=MUTED)

    year_font = load_font(15)
    yw = text_w(draw, year, year_font)
    draw.text((W - margin - 16 - yw, margin + 6), year, font=year_font, fill=MUTED)

    kind_font = load_font(13)
    draw.text((margin + 16, H - margin - 28), kind.upper(), font=kind_font, fill=FG)

    slug_font = load_font(12)
    draw.text((margin + 16, H - margin - 12), "/speaking/" + slug, font=slug_font, fill=MUTED)

    return img


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--year", required=True)
    parser.add_argument("--kind", default="Talk")
    args = parser.parse_args()

    outdir = MEDIA / "speaking" / args.slug
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / "cover.jpg"
    render(args.tag, args.year, args.kind, args.slug).save(outpath, "JPEG", quality=88, optimize=True)
    print("wrote", outpath.relative_to(V1), "({} bytes)".format(outpath.stat().st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
