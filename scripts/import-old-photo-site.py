#!/usr/bin/env python3
"""Pull the rest of the old photo site (photos.tstowx.com) into the four galleries.

The first pass (build-commercial-gallery.py, build-galleries.py) took 10 frames per client
project and the whole Hong Kong project. This adds what was left behind:

  * every remaining client frame -> commercial (exact/near duplicates of frames already in the
    gallery, or of each other, are skipped; so is the RALY IV contact sheet)
  * Italia '25 -> street (Venice and town scenes) and landscape (Dolomites, incl. the cows and
    horse, which are farm animals in mountain scenes rather than wildlife)

Frames are numbered on from the highest existing number in each gallery. Images are converted to
1600px webp, uploaded to R2 under galleries/<gallery>/, verified by size, and only then appended
to data/galleries.yaml, so the live site never points at a file that isn't there.

    uv run --with pillow scripts/import-old-photo-site.py --build-only   # stage + preview only
    uv run --with pillow scripts/import-old-photo-site.py                # stage, upload, write data

Needs rclone and the R2 env file (R2_ENV, default ~/.config/r2/tstowx-images.env) to upload.
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

from PIL import Image

HOME = pathlib.Path.home()
REPO = pathlib.Path(__file__).resolve().parent.parent
PROJECTS = pathlib.Path(os.environ.get("PHOTO_PROJECTS", HOME / "photos.tstowx.com/content/projects"))
STAGE = pathlib.Path(os.environ.get("GALLERY_STAGE", "/tmp/gallery-import"))
R2_ENV = pathlib.Path(os.environ.get("R2_ENV", HOME / ".config/r2/tstowx-images.env"))
DATA = REPO / "data/galleries.yaml"
BUCKET = "R2:tstowx-images"
MAX_EDGE = 1600
QUALITY = 82

CLIENT_PROJECTS = ["BBU", "MO & CO", "PIPERS", "RALY", "RALY III", "RALY IV"]
ALREADY_PER_PROJECT = 10  # what build-commercial-gallery.py sampled from each
SKIP = {("RALY IV", "IMG_2065.jpeg")}  # a contact sheet of thumbnails, not a photograph
DUP_DISTANCE = 24  # average-hash bits (of 256); burst frames and re-exports land well under this

ITALIA = "Italia '25"
ITALIA_STREET = ["IMG-1.jpg", "IMG-2.jpg", "IMG-3.jpg", "IMG-4.jpg", "IMG-5.jpg"]
ITALIA_LANDSCAPE = ["IMG-6.jpg", "IMG-7.jpg", "IMG-8.jpg", "IMG-9.jpg", "IMG-10.jpg",
                    "IMG-11.jpg", "IMG-12.jpg", "IMG-13.jpg", "IMG-14.jpg", "IMG-15.jpg"]


def images_in(project: str) -> list[pathlib.Path]:
    folder = PROJECTS / project
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})


def spread(files: list[pathlib.Path], want: int) -> list[pathlib.Path]:
    """Same sampler as build-commercial-gallery.py, to know which frames are already up."""
    if len(files) <= want:
        return files
    step = len(files) / want
    return [files[int(i * step)] for i in range(want)]


def ahash(p: pathlib.Path) -> list[bool]:
    with Image.open(p) as im:
        im.draft("L", (64, 64))
        px = list(im.convert("L").resize((16, 16)).tobytes())
    m = sum(px) / len(px)
    return [x > m for x in px]


def distance(a: list[bool], b: list[bool]) -> int:
    return sum(x != y for x, y in zip(a, b))


def plan() -> dict[str, list[pathlib.Path]]:
    out: dict[str, list[pathlib.Path]] = {"commercial": [], "street": [], "landscape": []}
    for project in CLIENT_PROJECTS:
        files = images_in(project)
        used = spread(files, ALREADY_PER_PROJECT)
        kept = [ahash(p) for p in used]
        for p in files:
            if p in used or (project, p.name) in SKIP:
                continue
            h = ahash(p)
            if min(distance(h, k) for k in kept) <= DUP_DISTANCE:
                continue
            kept.append(h)
            out["commercial"].append(p)
    out["street"] = [PROJECTS / ITALIA / n for n in ITALIA_STREET]
    out["landscape"] = [PROJECTS / ITALIA / n for n in ITALIA_LANDSCAPE]
    return out


def next_number(gallery: str) -> int:
    nums = [int(n) for n in re.findall(rf"name: {gallery}-(\d+)\.webp", DATA.read_text())]
    return max(nums, default=0) + 1


def build(sources: dict[str, list[pathlib.Path]]) -> dict[str, list[dict]]:
    made: dict[str, list[dict]] = {}
    for gallery, files in sources.items():
        folder = STAGE / gallery
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob("*.webp"):
            old.unlink()
        n = next_number(gallery)
        made[gallery] = []
        for src in files:
            name = f"{gallery}-{n:03d}.webp"
            n += 1
            out = folder / name
            with Image.open(src) as im:
                im = im.convert("RGB")
                im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
                w, h = im.size
                im.save(out, "WEBP", quality=QUALITY, method=6)
            made[gallery].append({"name": name, "w": w, "h": h, "src": str(src), "bytes": out.stat().st_size})
        mb = sum(m["bytes"] for m in made[gallery]) / 1e6
        print(f"built {gallery}: {len(made[gallery])} webp ({made[gallery][0]['name']}..{made[gallery][-1]['name']}), {mb:.1f} MB")
    return made


def r2_env() -> dict:
    if not R2_ENV.exists():
        raise SystemExit(f"No R2 credentials at {R2_ENV} (set R2_ENV). Staged files are in {STAGE}.")
    vals = {}
    for line in R2_ENV.read_text().splitlines():
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


def upload_and_verify(e: dict, made: dict[str, list[dict]]) -> None:
    for gallery, items in made.items():
        r = subprocess.run(["rclone", "copy", str(STAGE / gallery), f"{BUCKET}/galleries/{gallery}",
                            "--include", "*.webp", "--transfers", "8", "--stats", "0", "--log-level", "ERROR"],
                           env=e, capture_output=True, text=True)
        print(f"upload {gallery}: exit={r.returncode} {r.stderr.strip()[:300]}")
        if r.returncode:
            raise SystemExit(1)
        remote = subprocess.run(["rclone", "lsf", "--format", "sp", f"{BUCKET}/galleries/{gallery}"],
                                env=e, capture_output=True, text=True).stdout
        sizes = {}
        for line in remote.splitlines():
            if ";" in line:
                size, path = line.split(";", 1)
                sizes[path] = int(size)
        bad = [m["name"] for m in items if sizes.get(m["name"]) != m["bytes"]]
        if bad:
            raise SystemExit(f"VERIFY FAILED for {gallery}: {bad[:10]}")
        print(f"verified {len(items)} on {BUCKET}/galleries/{gallery}")


def update_data(made: dict[str, list[dict]]) -> None:
    lines = DATA.read_text().splitlines()
    for gallery, items in made.items():
        start = lines.index(f"{gallery}:")
        end = start + 1
        while end < len(lines) and (lines[end].startswith(" ") or not lines[end].strip()):
            end += 1
        while not lines[end - 1].strip():  # insert before any trailing blank lines
            end -= 1
        new = []
        for m in items:
            new += [f"    - name: {m['name']}", f"      w: {m['w']}", f"      h: {m['h']}"]
        lines[end:end] = new
        print(f"data/galleries.yaml: +{len(items)} {gallery}")
    DATA.write_text("\n".join(lines) + "\n")


def main() -> int:
    sources = plan()
    made = build(sources)
    if "--build-only" in sys.argv:
        print(f"build only: staged in {STAGE}, nothing uploaded, data untouched")
        return 0
    upload_and_verify(r2_env(), made)
    update_data(made)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
