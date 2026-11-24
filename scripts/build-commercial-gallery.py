#!/usr/bin/env python3
"""Build the `commercial` gallery from the client work on the photo site.

Pulls a spread of frames from each client project, converts them to 1600px webp, uploads them to
the tstowx-images bucket under galleries/commercial/, and adds the gallery to data/galleries.yaml
so the homepage strip and /photos/commercial/ both pick it up.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

from PIL import Image

REPO = pathlib.Path("/root/tstowx.com")
PROJECTS = pathlib.Path("/root/photos.tstowx.com/content/projects")
STAGE = pathlib.Path("/root/.hermes/cache/scratch/gallery-staging/commercial")
BUCKET = "R2:tstowx-images"
GALLERY = "commercial"
# Client work, in the order it should read on the page.
SOURCES = ["BBU", "MO & CO", "PIPERS", "RALY", "RALY III", "RALY IV"]
PER_PROJECT = 10
MAX_EDGE = 1600
QUALITY = 82
CARD = (800, 600)


def env() -> dict:
    cfg = pathlib.Path("/root/.config/r2/tstowx-images.env")
    vals = {}
    for line in cfg.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"').strip("'")
    e = dict(os.environ)
    e.update({
        "RCLONE_CONFIG_R2_TYPE": "s3",
        "RCLONE_CONFIG_R2_PROVIDER": "Cloudflare",
        "RCLONE_CONFIG_R2_ACCESS_KEY_ID": vals["AWS_ACCESS_KEY_ID"],
        "RCLONE_CONFIG_R2_SECRET_ACCESS_KEY": vals["AWS_SECRET_ACCESS_KEY"],
        "RCLONE_CONFIG_R2_ENDPOINT": vals["R2_ENDPOINT"],
        "RCLONE_CONFIG_R2_ACL": "private",
        "RCLONE_CONFIG_R2_NO_CHECK_BUCKET": "true",
    })
    return e


def spread(files: list[pathlib.Path], want: int) -> list[pathlib.Path]:
    """Evenly sample the project rather than taking the first N (which can cluster on one moment)."""
    if len(files) <= want:
        return files
    step = len(files) / want
    return [files[int(i * step)] for i in range(want)]


def build_images() -> list[dict]:
    STAGE.mkdir(parents=True, exist_ok=True)
    for old in STAGE.glob("*.webp"):
        old.unlink()
    made: list[dict] = []
    n = 0
    for project in SOURCES:
        folder = PROJECTS / project
        files = sorted([p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])
        if not files:
            print(f"WARN no images in {folder}")
            continue
        for src in spread(files, PER_PROJECT):
            n += 1
            name = f"{GALLERY}-{n:03d}.webp"
            out = STAGE / name
            with Image.open(src) as im:
                im = im.convert("RGB")
                im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
                w, h = im.size
                im.save(out, "WEBP", quality=QUALITY, method=6)
            made.append({"name": name, "w": w, "h": h, "src": str(src), "bytes": out.stat().st_size})
    # Card: centre crop of the first frame.
    with Image.open(pathlib.Path(made[0]["src"])) as im:
        im = im.convert("RGB")
        tw, th = CARD
        scale = max(tw / im.width, th / im.height)
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        left = (im.width - tw) // 2
        top = (im.height - th) // 2
        im.crop((left, top, left + tw, top + th)).save(STAGE / "card.webp", "WEBP", quality=QUALITY, method=6)
    return made


def upload(e: dict) -> None:
    r = subprocess.run(["rclone", "copy", str(STAGE), f"{BUCKET}/galleries/{GALLERY}",
                        "--include", "*.webp", "--transfers", "8", "--stats", "0", "--log-level", "ERROR"],
                       env=e, capture_output=True, text=True)
    print(f"upload {GALLERY}: exit={r.returncode} {r.stderr.strip()[:300]}")
    if r.returncode:
        raise SystemExit(1)


def verify(e: dict, made: list[dict]) -> None:
    remote = subprocess.run(["rclone", "lsf", "-R", "--format", "sp", f"{BUCKET}/galleries/{GALLERY}"],
                            env=e, capture_output=True, text=True).stdout
    sizes = {}
    for line in remote.splitlines():
        if ";" in line:
            size, path = line.split(";", 1)
            sizes[path] = int(size)
    bad = [f"{m['name']}: remote={sizes.get(m['name'])} local={m['bytes']}"
           for m in made if sizes.get(m["name"]) != m["bytes"]]
    if "card.webp" not in sizes:
        bad.append("card.webp missing")
    if bad:
        print("VERIFY FAILED")
        for b in bad[:10]:
            print("  " + b)
        raise SystemExit(1)
    print(f"verified {len(made)} images + card on {BUCKET}/galleries/{GALLERY}")


def update_data(made: list[dict]) -> None:
    data = REPO / "data/galleries.yaml"
    lines = data.read_text().splitlines()
    # Drop any previous commercial block so reruns stay idempotent.
    out, skipping = [], False
    for line in lines:
        if line.startswith(f"{GALLERY}:"):
            skipping = True
            continue
        if skipping:
            if line.startswith("  ") or not line.strip():
                continue
            skipping = False
        out.append(line)
    out.append(f"{GALLERY}:")
    out.append("  card: card.webp")
    out.append("  files:")
    for m in made:
        out.append(f"    - name: {m['name']}")
        out.append(f"      w: {m['w']}")
        out.append(f"      h: {m['h']}")
    data.write_text("\n".join(out) + "\n")
    print(f"data/galleries.yaml: {GALLERY} = {len(made)} images")


def ensure_page(made: list[dict]) -> None:
    page = REPO / "content/photos" / GALLERY / "index.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    if page.exists():
        print(f"kept existing {page.relative_to(REPO)}")
        return
    page.write_text(
        "---\n"
        'title: "Commercial"\n'
        "date: 2026-11-24\n"
        "draft: false\n"
        'description: "Client work — brands, hospitality and events, shot in the UK and on the road."\n'
        "---\n\n"
        "Photographs made for brands and businesses: RALY, PIPERS, MO & CO. and Bristol Basketball "
        "United, plus the events that came with them.\n"
    )
    print(f"wrote {page.relative_to(REPO)} ({len(made)} images)")


def main() -> int:
    made = build_images()
    total_mb = sum(m["bytes"] for m in made) / 1e6
    print(f"built {len(made)} webp, {total_mb:.1f} MB from {len(SOURCES)} projects")
    e = env()
    upload(e)
    verify(e, made)
    update_data(made)
    ensure_page(made)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
