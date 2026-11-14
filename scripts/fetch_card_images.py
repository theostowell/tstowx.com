#!/usr/bin/env python3
"""Fill in card/share images for tstowx.com notes.

The site is an index: every note points at something published elsewhere, and
the archive card wants that thing's image. This script asks the platform for it,
stores one 1200x630 webp per note in static/opengraph/, and writes the local
path back into `opengraph_image` so nothing depends on a CDN at runtime.

Order of preference per note:
  1. an image already set in front matter (downloaded if it is remote)
  2. Substack cover image, then the first real image in the post body
  3. X media (photo, or a video's poster frame)
  4. the YouTube thumbnail
  5. the Open Graph image of any other external_url

Usage:
  python3 scripts/fetch_card_images.py            # dry run, prints the plan
  python3 scripts/fetch_card_images.py --write    # downloads and edits notes
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
OUT = os.path.join(ROOT, "static", "opengraph")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}
SIZE = (1200, 630)


def fetch(url: str, binary: bool = False, timeout: int = 30):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.getcode(), r.read() if binary else r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            return e.code, b"" if binary else ""
        except Exception:
            if attempt < 2:
                time.sleep(2)
                continue
            return None, b"" if binary else ""
    return None, b"" if binary else ""


def read_note(path: str):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None, text
    return m.group(1), text


def field(fm: str, key: str):
    m = re.search(rf"^{key}:\s*(.+)$", fm, re.M)
    if not m:
        return None
    v = m.group(1).strip()
    if v in ("true", "false"):
        return v == "true"
    v = v.strip('"').strip("'")
    return v or None


def og_image(html: str):
    m = (re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
         or re.search(r'<meta[^>]*content="([^"]+)"[^>]*property="og:image"', html))
    return m.group(1) if m else None


def substack_image(url: str):
    """Cover image, then the first real body image. Skips avatars/badges."""
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    host = urllib.parse.urlparse(url).netloc
    code, body = fetch(f"https://{host}/api/v1/posts/{slug}")
    if code == 200 and body:
        try:
            post = json.loads(body)
        except Exception:
            post = {}
        if post.get("cover_image"):
            return post["cover_image"]
        for src in re.findall(r'<img[^>]+src="([^"]+)"', post.get("body_html") or ""):
            if "substack-post-media" in src or "substackcdn.com/image/fetch" in src:
                if re.search(r"/w_(?:[1-9]\d|1\d\d),h_", src):   # small avatars/badges
                    continue
                return src
    code, html = fetch(url)
    if code == 200:
        img = og_image(html)
        if img and "subscribe-card" not in img:
            return img
    return None


def x_image(handle: str, post_id: str):
    code, body = fetch(f"https://cdn.syndication.twimg.com/tweet-result?id={post_id}&token=a")
    if code != 200 or not body:
        return None
    try:
        data = json.loads(body)
    except Exception:
        return None
    for media in data.get("mediaDetails") or []:
        if media.get("media_url_https"):
            return media["media_url_https"]
    for media in (data.get("entities") or {}).get("media") or []:
        if media.get("media_url_https"):
            return media["media_url_https"]
    return None


def youtube_image(video_id: str):
    for name in ("maxresdefault", "sddefault", "hqdefault"):
        url = f"https://i.ytimg.com/vi/{video_id}/{name}.jpg"
        code, _ = fetch(url, timeout=20)
        if code == 200:
            return url
    return None


def page_image(url: str):
    code, html = fetch(url)
    return og_image(html) if code == 200 else None


def to_webp(raw: bytes, dest: str) -> bool:
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        return False
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (243, 238, 228))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    img = img.copy()
    target_ratio = SIZE[0] / SIZE[1]
    w, h = img.size
    if w / h > target_ratio:                      # too wide: trim sides
        new_w = int(h * target_ratio)
        img = img.crop(((w - new_w) // 2, 0, (w + new_w) // 2, h))
    else:                                          # too tall: trim top/bottom
        new_h = int(w / target_ratio)
        img = img.crop((0, (h - new_h) // 2, w, (h + new_h) // 2))
    img = img.resize(SIZE, Image.Resampling.LANCZOS)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    img.save(dest, "WEBP", quality=82, method=6)
    return True


def main():
    write = "--write" in sys.argv
    plan, skipped = [], []

    for name in sorted(os.listdir(CONTENT)):
        if not name.endswith(".md"):
            continue
        slug = name[:-3]
        path = os.path.join(CONTENT, name)
        fm, text = read_note(path)
        if fm is None or not field(fm, "timeline"):
            continue

        have = field(fm, "timeline_image") or field(fm, "opengraph_image")
        local_dest = f"/opengraph/{slug}.webp"

        if have and have.startswith("/"):
            continue                                # already a local file
        if have and not have.startswith("http"):
            continue

        source, why = None, ""
        if have:
            source, why = have, "existing og image"
        elif field(fm, "external_url") and "substack" in field(fm, "external_url"):
            source, why = substack_image(field(fm, "external_url")), "substack"
        elif field(fm, "platform") == "x":
            source, why = x_image(field(fm, "author_handle"), field(fm, "post_id")), "x"
        elif field(fm, "youtube_id"):
            source, why = youtube_image(field(fm, "youtube_id")), "youtube"
        elif field(fm, "external_url"):
            source, why = page_image(field(fm, "external_url")), "web"

        if not source:
            skipped.append(slug)
            continue
        plan.append((slug, source, why, path, fm, text))

    print(f"{len(plan)} notes to fill, {len(skipped)} with no image anywhere")
    if skipped:
        print("  no image: " + ", ".join(skipped))

    for slug, source, why, path, fm, text in plan:
        print(f"  {slug:42} {why:16} {source[:80]}")
        if not write:
            continue
        local_dest = f"/opengraph/{slug}.webp"
        code, raw = fetch(source, binary=True)
        if code != 200 or not raw:
            print(f"    ! download failed ({code})")
            continue
        dest = os.path.join(OUT, f"{slug}.webp")
        if not to_webp(raw, dest):
            print("    ! not a usable image")
            continue
        kb = os.path.getsize(dest) // 1024
        if "opengraph_image:" in fm:
            new_fm = re.sub(r'^opengraph_image:.*$', f'opengraph_image: "{local_dest}"', fm, count=1, flags=re.M)
        else:
            new_fm = fm + f'\nopengraph_image: "{local_dest}"'
        open(path, "w", encoding="utf-8").write(f"---\n{new_fm}\n---\n" + text[text.index("\n---", 4) + 5:])
        print(f"    -> {local_dest} ({kb} KB)")
        time.sleep(0.4)


if __name__ == "__main__":
    main()
