#!/usr/bin/env python3
"""Generate on-brand title cards for notes that have no image of their own.

Plenty of Theo's essays are text-only on Substack: the platform serves the same
generic subscribe card as their og:image, so there is nothing to scrape. Rather
than leave a bare text card in the archive, this draws a card in the site's own
type (Instrument Serif on cream) from the note's title, type and date.

Usage:
  python3 scripts/make_title_cards.py --write      # only fills gaps
  python3 scripts/make_title_cards.py --write --force

The fonts in scripts/assets are the same Instrument Serif the site loads
(OFL). Files land in static/opengraph/<slug>.webp and the note's
`opengraph_image` is pointed at the local copy.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
OUT = os.path.join(ROOT, "static", "opengraph")
FONTS = os.path.join(ROOT, "scripts", "assets")

W, H = 1200, 630
CREAM = (243, 238, 228)
INK = (23, 23, 23)
MUTED = (110, 104, 95)
ACCENTS = ["#6D4EE0", "#B4532F", "#2F6D5A", "#A2712F", "#39396B"]

LABELS = {
    "writing": "Substack · Essay",
    "substack": "Substack",
    "place": "Substack · Travel",
    "note": "Substack · Note",
    "social": "X",
    "video": "Film",
    "project": "Project",
}
PLATFORM_TINT = {"x": "X", "substack": "Substack"}


def read(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return (m.group(1) if m else ""), text, (m.end() if m else 0)


def field(fm, key):
    m = re.search(rf"^{key}:\s*(.+)$", fm, re.M)
    if not m:
        return None
    v = m.group(1).strip().strip('"').strip("'")
    if v in ("true", "false"):
        return v == "true"
    return v or None


def wrap(draw, text, font, width):
    words, lines, line = text.split(), [], ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=font) <= width or not line:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def build(title, label, date_text):
    img = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(img)
    accent = ACCENTS[int(hashlib.md5(title.encode()).hexdigest(), 16) % len(ACCENTS)]

    serif = os.path.join(FONTS, "InstrumentSerif-Regular.ttf")
    serif_it = os.path.join(FONTS, "InstrumentSerif-Italic.ttf")
    sans = os.path.join(FONTS, "DejaVuSans.ttf")
    sans = sans if os.path.exists(sans) else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    margin = 92
    # meta row
    meta_font = ImageFont.truetype(sans, 21)
    draw.ellipse((margin, 78, margin + 11, 89), fill=accent)
    draw.text((margin + 26, 72), label.upper(), font=meta_font, fill=MUTED, spacing=2)

    # title: largest size that fits in four lines
    avail_w = W - margin * 2
    avail_h = H - 300
    chosen = None
    for size in range(104, 44, -2):
        font = ImageFont.truetype(serif_it if len(title) < 34 else serif, size)
        lines = wrap(draw, title, font, avail_w)
        if len(lines) <= 4 and len(lines) * size * 1.18 <= avail_h + 120:
            chosen = (font, lines, size)
            break
    font, lines, size = chosen
    line_h = size * 1.14
    block_h = len(lines) * line_h
    y = (H - block_h) / 2 + 16
    for line in lines:
        draw.text((margin, y), line, font=font, fill=INK)
        y += line_h

    # footer
    draw.line((margin, H - 116, W - margin, H - 116), fill=(214, 206, 191), width=1)
    small = ImageFont.truetype(sans, 19)
    draw.text((margin, H - 94), "tstowx.com", font=small, fill=MUTED)
    if date_text:
        tw = draw.textlength(date_text, font=small)
        draw.text((W - margin - tw, H - 94), date_text, font=small, fill=MUTED)
    return img


def main():
    write = "--write" in sys.argv
    force = "--force" in sys.argv
    made = 0

    for name in sorted(os.listdir(CONTENT)):
        if not name.endswith(".md"):
            continue
        slug = name[:-3]
        path = os.path.join(CONTENT, name)
        fm, text, body_at = read(path)
        if not fm or field(fm, "timeline") is None or field(fm, "draft") is True:
            continue

        have = field(fm, "timeline_image") or field(fm, "opengraph_image")
        if have and not force:
            continue

        title = field(fm, "title")
        if not title:
            continue
        ttype = field(fm, "timeline_type") or "writing"
        label = LABELS.get(ttype, ttype.title())
        if field(fm, "platform") == "x":
            label = "X"

        date = field(fm, "date") or ""
        date_text = ""
        if re.match(r"\d{4}-\d{2}-\d{2}", date):
            import datetime
            d = datetime.date.fromisoformat(date[:10])
            date_text = d.strftime("%B %Y")

        dest = f"/opengraph/{slug}-card.webp"
        print(f"  {slug:42} {label:18} {title[:48]}")
        if not write:
            made += 1
            continue
        build(title, label, date_text).save(os.path.join(OUT, f"{slug}-card.webp"), "WEBP", quality=86, method=6)
        if "opengraph_image:" in fm:
            new_fm = re.sub(r"^opengraph_image:.*$", f'opengraph_image: "{dest}"', fm, count=1, flags=re.M)
        else:
            new_fm = fm + f'\nopengraph_image: "{dest}"'
        open(path, "w", encoding="utf-8").write(f"---\n{new_fm}\n---\n" + text[body_at:])
        made += 1

    print(f"{made} title cards {'written' if write else 'planned'}")


if __name__ == "__main__":
    main()
