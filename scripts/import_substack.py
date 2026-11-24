#!/usr/bin/env python3
"""Bring a Substack post's full text onto tstowx.com.

The site hosts its own writing: a note whose external_url is a Substack post
renders here once it has a body, with "read on Substack / subscribe" links
underneath. This script fills that body in from Substack.

  note  Fill in an existing note's body from its own external_url.
        Images go to static/attachments/essays/<note-name>/.

          python3 scripts/import_substack.py note content/hate.md

  fm    Create a Fundamentalised issue bundle at content/fm/<NNN>/ (served at
        /fm/NNN/), images saved alongside. Pass a Substack URL or post id, or
        --from-note to adopt an existing timeline note: its front matter moves
        into the bundle, its old URL becomes an alias, and the note can then be
        deleted.

          python3 scripts/import_substack.py fm 1 209224286
          python3 scripts/import_substack.py fm 1 --from-note content/substack-001-digital-minimalism.md

  polish  Re-run the clean-up (local images, dead embeds, links to old homes of
          this writing pointed at the copies here) over existing files.

          python3 scripts/import_substack.py polish content/fm/*/index.md

Add --force to overwrite a body or bundle that already has text. Needs pandoc.
"""
from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (tstowx.com importer)"}
PUBLICATION = "https://tstowx.substack.com"


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


def fetch_post(ref: str) -> dict:
    """Accepts a post id, substack.com/@tstowx/p-<id> or tstowx.substack.com/p/<slug>."""
    m = re.search(r"(?:^|p-)(\d+)$", ref.strip().rstrip("/"))
    if m:
        url = f"https://substack.com/api/v1/posts/by-id/{m.group(1)}"
    else:
        m = re.search(r"/p/([^/?#]+)", ref)
        if not m:
            sys.exit(f"can't tell which Substack post this is: {ref}")
        url = f"{PUBLICATION}/api/v1/posts/{m.group(1)}"
    data = json.loads(fetch(url))
    return data.get("post", data)


# --- front matter -----------------------------------------------------------

def split_note(path: str) -> tuple[str, str]:
    text = open(path).read()
    m = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.S)
    if not m:
        sys.exit(f"{path} has no front matter")
    return m.group(1), m.group(2)


def get_field(front: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*(.*)$", front, re.M)
    return m.group(1).strip().strip("\"'") if m else ""


def set_field(front: str, key: str, value: str) -> str:
    line = f"{key}: {value}"
    if re.search(rf"^{key}:", front, re.M):
        return re.sub(rf"^{key}:.*$", lambda _: line, front, count=1, flags=re.M)
    return front + "\n" + line


def drop_field(front: str, key: str) -> str:
    # a scalar line, or a key followed by an indented list
    return re.sub(rf"^{key}:.*\n?(?:[ \t]+-.*\n?)*", "", front, flags=re.M).rstrip("\n")


# --- body -------------------------------------------------------------------

def original_image_url(url: str) -> str:
    """Substack CDN URLs wrap the real S3 URL; unwrap it."""
    url = html.unescape(url)
    m = re.search(r"(https?%3A%2F%2F.+)$", url)
    return urllib.parse.unquote(m.group(1)) if m else url


def save_image(src: str, image_dir: str, url_prefix: str) -> str:
    """Download an image next to the page (once) and return its site URL."""
    src = original_image_url(src)
    name = os.path.basename(urllib.parse.urlparse(src).path) or "image"
    name = re.sub(r"[^A-Za-z0-9._-]", "-", name)
    os.makedirs(image_dir, exist_ok=True)
    path = os.path.join(image_dir, name)
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(fetch(src))
    return url_prefix + name


_LINKS: dict[str, str] | None = None


def site_links() -> dict[str, str]:
    """slug -> local URL for every note, from its file name, aliases and Substack URL."""
    global _LINKS
    if _LINKS is None:
        _LINKS = {
            # old slugs from fundamentalised.com / theostowell.me
            "short-form-paradox": "/short-form/",
            "on-receiving-hate": "/hate/",
            "action-is-oxygen": "/purposeful-action/",
            "twenty-observations-from-20-years-on-earth": "/twenty/",
        }
        content = os.path.join(ROOT, "content")
        for f in sorted(os.listdir(content)):
            if not f.endswith(".md") or f.startswith("_"):
                continue
            name = f[:-3]
            url = f"/{name}/"
            front, _ = split_note(os.path.join(content, f))
            keys = [name] + [a.strip("/").split("/")[-1] for a in re.findall(r"^\s+-\s*\"?([^\"\n]+)", front, re.M)]
            m = re.search(r"/p/([^/?#\"]+)", get_field(front, "external_url"))
            if m:
                keys.append(m.group(1))
            for k in keys:
                _LINKS.setdefault(k, url)
    return _LINKS


def local_url(url: str, text: str) -> str:
    """Point links at old homes of this writing (Fundamentalised sites, theostowell.me,
    the Substack posts) at the copies on this site. Drops email tracking params."""
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.urlencode([(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if not k.startswith("utm_")])
    url = urllib.parse.urlunsplit(parts._replace(query=query))
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path
    issue = re.match(r"^/(?:issues|p)/(\d{3})(?:[-/]|$)", path)
    if host in ("fundamentalised.com", "tstowx.substack.com", "fundamentalised.substack.com") and issue:
        return f"/fm/{issue.group(1)}/"
    if host == "fundamentalised.com" and path.rstrip("/") in ("", "/issues"):
        return "/fm/"
    if host in ("fundamentalised.com", "theostowell.me") and path.rstrip("/") in ("/t/essays", "/essays"):
        return "/writing/"
    m = re.match(r"^/(?:essays|p)/([^/]+)", path)
    if m and host in ("fundamentalised.com", "theostowell.me", "tstowx.substack.com"):
        return site_links().get(m.group(1), url)
    num = re.match(r"^\s*(\d{3})\s*•", text)
    if num and host == "assets.buttondown.email":
        return f"/fm/{num.group(1)}/"
    return url


def polish(md: str, image_dir: str, url_prefix: str) -> str:
    """Clean-up shared by fresh imports and the `polish` command."""
    # Dead embeds that pandoc captured as their error pages (Spotify, etc.).
    md = re.sub(r'<div class="iframe">.*?</div>\n*', "", md, flags=re.S)
    # Thumbnails broken in the Buttondown migration (no file extension).
    md = re.sub(r'<img src="https://assets\.buttondown\.email/[^".]+"[^>]*>\n*', "", md)
    # Gallery images still on Substack's CDN: save them locally.
    md = re.sub(
        r'<img src="(https://[^"]*(?:substackcdn\.com|substack-post-media)[^"]*)"[^>]*>',
        lambda m: f'<img src="{save_image(m.group(1), image_dir, url_prefix)}" alt="" loading="lazy">', md,
    )
    md = re.sub(
        r"!\[([^\]]*)\]\((https://[^)]*(?:substackcdn\.com|substack-post-media)[^)]*)\)",
        lambda m: f"![{m.group(1)}]({save_image(m.group(2), image_dir, url_prefix)})", md,
    )
    # Buttondown link cards: an empty image link plus an excerpt "heading".
    md = re.sub(r'<a href="[^"]*" class="image-link[^"]*"[^>]*></a>\n*', "", md)
    md = re.sub(r"^#{1,6} \[([^\]]+)\]\(https://assets\.buttondown\.email/[^)]*\)$", r"*\1*", md, flags=re.M)
    # Any link titled "NNN • ..." is a reference to that issue, whatever state its URL is in.
    md = re.sub(r"(?<!!)\[((\d{3})\s*•[^\]]*)\]\([^)\s]*\)", r"[\1](/fm/\2/)", md)
    md = re.sub(
        r"(?<!!)\[([^\]]*)\]\((https?://[^)\s]+)\)",
        lambda m: f"[{m.group(1)}]({local_url(m.group(2), m.group(1))})", md,
    )
    return re.sub(r"\n{3,}", "\n\n", md)


def body_markdown(post: dict, image_dir: str, url_prefix: str) -> str:
    def save(src: str) -> str:
        return save_image(src, image_dir, url_prefix)

    def figure(m: re.Match) -> str:
        inner = m.group(1)
        src = re.search(r'<a[^>]+class="image-link[^"]*"[^>]+href="([^"]+)"', inner) or re.search(
            r'<img[^>]+src="([^"]+)"', inner
        )
        if not src:
            return ""
        alt = re.search(r'<img[^>]+alt="([^"]*)"', inner)
        cap = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", inner, re.S)
        out = f'<figure><img src="{save(src.group(1))}" alt="{alt.group(1) if alt else ""}" loading="lazy">'
        if cap:
            out += f"<figcaption>{cap.group(1)}</figcaption>"
        return out + "</figure>"

    body = post.get("body_html") or ""
    # YouTube embeds become Hugo's youtube shortcode (via a placeholder pandoc leaves alone).
    body = re.sub(
        r'<div id="youtube2-([\w-]+)" class="youtube-wrap".*?</iframe></div></div>',
        r"<p>YOUTUBEEMBED:\1</p>", body, flags=re.S,
    )
    body = re.sub(r'<div class="captioned-image-container"><figure>(.*?)</figure></div>', figure, body, flags=re.S)
    # Substack furniture: subscribe/share buttons and widgets. The site adds its own.
    body = re.sub(r'<p class="button-wrapper".*?</p>', "", body, flags=re.S)
    body = re.sub(r'<div class="subscription-widget-wrap.*?</form></div></div>', "", body, flags=re.S)
    body = re.sub(r'<div class="(?:subscription-widget|share-dialog|captioned-button)[^"]*".*?</div>', "", body, flags=re.S)
    md = subprocess.run(
        ["pandoc", "-f", "html-native_divs-native_spans", "-t", "gfm", "--wrap=none"],
        input=body, capture_output=True, text=True, check=True,
    ).stdout
    md = re.sub(r"^YOUTUBEEMBED:([\w-]+)$", r"{{< youtube \1 >}}", md, flags=re.M)
    return polish(md, image_dir, url_prefix).strip() + "\n"


def has_body(text: str) -> bool:
    return bool(text.strip()) and "The timeline card links directly" not in text


# --- commands ---------------------------------------------------------------

def cmd_note(path: str, force: bool) -> None:
    front, body = split_note(path)
    if has_body(body) and not force:
        sys.exit(f"{path} already has a body (use --force to replace it)")
    url = get_field(front, "external_url")
    if "substack.com" not in url:
        sys.exit(f"{path}: external_url is not a Substack post")
    post = fetch_post(url)
    name = os.path.splitext(os.path.basename(path))[0]
    md = body_markdown(post, os.path.join(ROOT, "static", "attachments", "essays", name), f"/attachments/essays/{name}/")
    front = set_field(front, "external_url", json.dumps(post.get("canonical_url") or url))
    with open(path, "w") as f:
        f.write(f"---\n{front}\n---\n\n{md}")
    print(f"filled {os.path.relpath(path, ROOT)}")


def cmd_fm(number: int, ref: str | None, note: str | None, force: bool) -> None:
    slug = f"{number:03d}"
    bundle = os.path.join(ROOT, "content", "fm", slug)
    index = os.path.join(bundle, "index.md")
    if os.path.exists(index) and not force:
        sys.exit(f"{index} already exists (use --force to overwrite)")

    front = ""
    if note:
        front, _ = split_note(note)
        ref = ref or get_field(front, "external_url")
    if not ref:
        sys.exit("give a Substack URL/id or --from-note")
    post = fetch_post(ref)

    title = re.sub(r"^\s*\d+\s*[•·|:-]\s*", "", get_field(front, "title") or post["title"]).strip()
    for key in ("title", "issue", "date", "draft", "external_url", "aliases", "original_url"):
        front = drop_field(front, key)
    description = (post.get("subtitle") or post.get("description") or "").strip()
    if not get_field(front, "description") and description:
        front = set_field(front, "description", json.dumps(description, ensure_ascii=False))
    head = [
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"issue: {number}",
        f"date: {post['post_date'][:10]}",
        "draft: false",
        f"external_url: {json.dumps(post.get('canonical_url') or ref)}",
    ]
    if note:
        old = "/" + os.path.splitext(os.path.basename(note))[0] + "/"
        head.append(f'aliases:\n  - "{old}"')
    front = "\n".join(head) + ("\n" + front.strip() if front.strip() else "")

    md = body_markdown(post, bundle, "")
    os.makedirs(bundle, exist_ok=True)
    with open(index, "w") as f:
        f.write(f"---\n{front}\n---\n\n{md}")
    print(f"wrote {os.path.relpath(index, ROOT)}  ->  /fm/{slug}/")
    if note:
        print(f"  adopted {os.path.relpath(note, ROOT)}; delete it once you've checked the bundle")


def cmd_polish(paths: list[str]) -> None:
    for path in paths:
        front, body = split_note(path)
        if os.path.basename(path) == "index.md":
            image_dir, prefix = os.path.dirname(path), ""
        else:
            name = os.path.splitext(os.path.basename(path))[0]
            image_dir, prefix = os.path.join(ROOT, "static", "attachments", "essays", name), f"/attachments/essays/{name}/"
        new = polish(body, image_dir, prefix)
        if new != body:
            with open(path, "w") as f:
                f.write(f"---\n{front}\n---\n{new}")
            print(f"polished {os.path.relpath(path, ROOT)}")


def main() -> None:
    argv = sys.argv[1:]
    force = "--force" in argv
    argv = [a for a in argv if a != "--force"]
    note = None
    if "--from-note" in argv:
        i = argv.index("--from-note")
        note = argv[i + 1]
        del argv[i : i + 2]
    if len(argv) >= 2 and argv[0] == "polish":
        cmd_polish(argv[1:])
    elif len(argv) >= 2 and argv[0] == "note":
        for path in argv[1:]:
            cmd_note(path, force)
    elif len(argv) in (2, 3) and argv[0] == "fm":
        cmd_fm(int(argv[1]), argv[2] if len(argv) == 3 else None, note, force)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
