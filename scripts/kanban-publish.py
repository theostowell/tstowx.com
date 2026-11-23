#!/usr/bin/env python3
"""Turn content-Kanban cards in the tstowx.com repo into site entries.

Cards live in /root/tstowx.com/kanban/*.md with a `status` (see kanban/README.md). This reads
them and writes `content/<slug>.md`:

  ready      -> draft: true                    (enters the timeline as a draft)
  timeline   -> draft: false, timeline: true   (visible in the timeline)
  frontpage  -> the above + timeline_featured  (above the dated archive on the homepage)

Dry run by default; --write creates/updates the files. It never runs git, never edits a card's
status, and appends one `## Log` line per card it acted on.

A card with `external_url` becomes an index entry (frontmatter only). A card without one is
hosted: the body under `## Body` is copied in.
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import sys
import unicodedata

REPO = pathlib.Path("/root/tstowx.com")
CARDS = REPO / "kanban"
CONTENT = REPO / "content"
ACTIVE = {"ready", "timeline", "frontpage"}
# The site's own vocabulary (PUBLISHING.md): the homepage rows are type-driven, so the card
# type has to land in one of them.
TYPE_MAP = {"writing": "writing", "essay": "writing", "article": "writing",
            "film": "video", "video": "video", "youtube": "video",
            "place": "place", "travel": "place", "note": "note",
            "project": "project", "venture": "project", "book": "project",
            "photo": "note", "photography": "note", "link": "link"}


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    parts = text.split("---", 2)
    return (parts[1], parts[2].lstrip("\n")) if len(parts) == 3 else ("", text)


def fm(frontmatter: str, key: str) -> str:
    # [ \t]* rather than \s*: \s swallows the newline and captures the next key as the value.
    m = re.search(rf"^{re.escape(key)}:[ \t]*(.*)$", frontmatter, re.M)
    if not m:
        return ""
    value = m.group(1).strip()
    if value in ("|", "|-", ">", ">-", "|+", ">+"):
        block = []
        for line in frontmatter[m.end():].splitlines()[1:]:
            if line.startswith((" ", "\t")):
                block.append(line.strip())
            elif not line.strip():
                block.append("")
            else:
                break
        return " ".join(x for x in block if x).strip()
    return value.strip().strip('"').strip("'")


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return re.sub(r"-{2,}", "-", value)


def section(body: str, name: str) -> str:
    m = re.search(rf"^##\s*{name}\s*$(.*?)(?=^##\s|\Z)", body, re.M | re.S)
    return m.group(1).strip() if m else ""


def card_paths(explicit: str | None) -> list[pathlib.Path]:
    if explicit:
        p = pathlib.Path(explicit)
        return [p if p.is_absolute() else REPO / p]
    return sorted(p for p in CARDS.glob("*.md") if p.name != "README.md")


def build(card: pathlib.Path) -> tuple[str, str, dict] | None:
    text = card.read_text(errors="ignore")
    front, body = split_frontmatter(text)
    status = fm(front, "status").lower()
    if status not in ACTIVE:
        return None
    title = fm(front, "title") or card.stem
    summary = fm(front, "summary") or fm(front, "description") or ""
    external = fm(front, "external_url")
    kind = TYPE_MAP.get(fm(front, "type").lower(), "writing")
    slug = slugify(fm(front, "slug") or title)
    date = fm(front, "date") or dt.date.today().isoformat()
    date = date[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", date) else dt.date.today().isoformat()

    lines = ["---", f'title: "{title}"', f"date: {date}", f"draft: {'false' if status != 'ready' else 'true'}",
             "timeline: true", f"timeline_type: {kind}"]
    if summary:
        lines.append('timeline_summary: "' + summary.replace('"', "'") + '"')
    if external:
        lines.append(f'external_url: "{external}"')
    # Only ventures have a slot above the archive; timeline_featured on anything else makes the
    # note vanish (the layout drops featured items out of $rest and only renders ventures).
    if status == "frontpage" and kind == "project":
        lines.append("timeline_featured: true")
    image = fm(front, "featured")
    if image:
        lines.append(f'timeline_image: "{image}"')
    lines.append("---")

    body_text = ""
    if not external:
        pasted = section(body, "Body") or section(body, "Request")
        if pasted:
            body_text = "\n\n" + pasted + "\n"
    note = "\n".join(lines) + "\n" + body_text
    return note, slug, {"status": status, "title": title, "words": len(body_text.split())}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--card")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--force", action="store_true", help="overwrite an existing content note")
    args = ap.parse_args()

    acted = 0
    for card in card_paths(args.card):
        built = build(card)
        if not built:
            continue
        note, slug, meta = built
        target = CONTENT / f"{slug}.md"
        exists = target.exists()
        if exists and not args.force and not args.write:
            print(f"{'exists':12s} {slug:40s} {target}")
            continue
        state = "would write" if not args.write else ("updated" if exists else "written")
        if args.write:
            CONTENT.mkdir(parents=True, exist_ok=True)
            target.write_text(note)
            target.chmod(0o644)
            log = card.read_text(errors="ignore").rstrip()
            stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
            entry = f"\n| {stamp} | {meta['status']} | `content/{slug}.md` |"
            if "## Log" not in log:
                log += "\n\n## Log\n\n| When | Status | Wrote |\n|---|---|---|"
            card.write_text(log + entry + "\n")
            acted += 1
        print(f"{state:12s} {slug:40s} {target}  ({meta['status']}, {meta['words']} body words)")

    if not acted and not args.write:
        print("(dry run — nothing written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
