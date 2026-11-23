---
tags:
  - category/notes
agent/description: Content Kanban contract for the tstowx.com repo. One note per piece of content, driven by its status; the script turns cards into site entries.
---

# Content Kanban

Drop a card in this folder to park a piece of content. Move it along by changing `status`; the
script writes the matching note into `content/`. Nothing is committed or pushed by an agent —
Theo reviews the files in Obsidian and pushes when he wants them live.

## Fields

`status`, `type`, `date`, `summary`, `external_url`, `slug`, `notes`. Optional: `featured` for
the card image, `source` for where the piece lives.

Write values bare — `status: ready`, never `status: "ready"`.

## Stages

| `status` | Meaning | What the script does |
|---|---|---|
| `backlog` | Captured, not agreed | nothing |
| `ready` | Approved to enter the timeline | writes `content/<slug>.md` with `draft: true` |
| `timeline` | Should appear in the timeline | writes/updates the note with `draft: false`, `timeline: true` |
| `frontpage` | Should sit above the archive on the homepage | as `timeline`, plus `timeline_featured: true` |
| `shipped` | Live, checked | nothing; the note is the record |

Only Theo sets `timeline`, `frontpage`, `shipped`. The script never changes `status`; it appends
one `## Log` line so the card records what it produced.

## Card shape

```markdown
---
tags:
  - category/content
status: backlog
type: writing
date: 2026-11-23
summary: One sentence that belongs on the card.
external_url:
slug:
---

## Request

What this piece is, in Theo's words.

## Notes

Whatever the writer needs.
```

`type` maps to the site's `timeline_type`: `writing`, `film`, `project`, `photo`.

A card with `external_url` publishes as an index entry (the site sends readers there). No
`external_url` means the body is hosted: paste it under `## Body` and the script uses it.

## Running it

```bash
python3 scripts/kanban-publish.py            # dry run: what would be written
python3 scripts/kanban-publish.py --write    # write into content/
python3 scripts/kanban-publish.py --card kanban/<card>.md --write
```

Then verify the build (`hugo-site-operations`), and tell Theo which files landed. He commits and
pushes.
