# Publishing to tstowx.com

This vault is the source for `tstowx.com`, and `tstowx.com` is an **index**, not a publishing platform. Nothing is hosted here. Essays live on Substack, films on YouTube, posts on X, ventures on their own sites and photographs on `photos.tstowx.com`.

So a note in `content/` is a pointer: a title, a date, a card summary and the URL the thing actually lives at. The site sends readers straight there, and its own `/slug/` URL 301s to the same place, so there is no second copy to keep in sync and nothing to maintain twice.

## The normal workflow

1. Publish the thing where it belongs — Substack, YouTube, X, a venture site.
2. In Obsidian, create a note in `content/`. The filename becomes the local URL (`content/building-proselab.md` → `/building-proselab/`), so use a simple, lower-case filename with hyphens.
3. Fill in the frontmatter below and paste the URL into `external_url`. You do not need to write a body.
4. Keep `draft: true` while you think about it; set `draft: false` when it should appear on the site.

That is the whole job. If the thing is a film, put the YouTube ID in `youtube_id` instead of a URL and the site works out the rest.

## The frontmatter

```yaml
---
title: "The title readers should see"
date: 2026-07-26
draft: true
timeline: true
timeline_type: writing
timeline_summary: "One crisp sentence for the card."
external_url: "https://tstowx.substack.com/p/the-post"
---
```

| Field | What it controls | Rules of thumb |
| --- | --- | --- |
| `title` | Card and page title | Write it for a reader, not as a filename. |
| `date` | Order and displayed month | `YYYY-MM-DD`. Newest first. |
| `draft` | Whether the entry appears | `true` until you want it live. |
| `timeline` | Whether the note is on the homepage | `true` for every entry. |
| `timeline_type` | The card’s label and behaviour | One of the types below. |
| `timeline_summary` | The card copy | One useful sentence. Preferred over `description`. |
| `external_url` | Where the entry actually lives | The platform URL. This is the important one. |
| `description` | Search and social previews, fallback card copy | Slightly longer is fine. |
| `timeline_featured` | Keeps a flagship entry above the dated archive | Optional. Ventures only. |
| `timeline_date_label` | Date text on the card | Optional, for ranges: `"March 2026 — Present"`. |
| `timeline_card_color` | Card background | Optional hex, e.g. `"#E9E4FA"`. |
| `timeline_image` | Card image | Optional site path, e.g. `/attachments/photo.jpg`. |
| `opengraph_image` | Share image, and card image when `timeline_image` is empty | Optional. Put the file in `static/opengraph/`. |

If `timeline_summary` is blank the site uses `description`, then the opening of the note. Fill it in deliberately — it is what the homepage reads like.

## Where the card links

Every card, list item and single page asks `layouts/partials/outbound.html` where to send the reader. It checks, in this order:

1. `youtube_id` → `https://www.youtube.com/watch?v=…`
2. `platform: x` with `author_handle` and `post_id` → the post on X
3. `timeline_type: project` with `website_url` → the project’s own site
4. `external_url` → exactly as pasted
5. nothing → the entry stays on this site (the safe fallback, but not what you want)

So: paste a URL into `external_url` and the card goes there.

## Types at a glance

| What you published | `timeline_type` | Fields that matter |
| --- | --- | --- |
| Essay or article on Substack | `writing` or `substack` | `external_url` (add `opengraph_image` for a richer card) |
| Travel or place-based piece | `place` | `external_url` |
| Short personal update | `note` | `external_url` |
| Film or vlog on YouTube | `video` | `youtube_id` |
| Post on X | `social` | `platform: x`, `author_handle`, `post_id` |
| A venture | `project` | `website_url`, plus `external_url` for its TrustMRR page, `trustmrr_embed`, `dashboard_accent` |
| A book or other product | `project` | `external_url` to the product page |
| A link worth keeping | `link` | `external_url` |

## Redirects and old links

The build writes `_redirects` from the same rule, so every entry’s own URL is a real 301 to its platform home — including the legacy `/writing/…` aliases:

- `https://tstowx.com/bro-text/` → the Substack post
- `https://tstowx.com/wild/` → the film on YouTube
- `https://tstowx.com/parazettel/` → `parazettel.com`

Those pages also carry `noindex` and a canonical pointing at the platform, so search results consolidate there instead of competing with a copy here. The RSS feed links items to the platform too and never mirrors a body that lives elsewhere.

## What does still live here

- The homepage dashboard (`layouts/partials/home_dashboard.html`). Its hero, "Now" status, photography blurb and socials live in `hugo.yaml` under `params.dashboard`.
- The chronological index at `/timeline/`.
- `/now`, `/signup` and `/cv` (a redirect to the PDF).

Adding entries never means touching a template: the dashboard, the archive, the filters and the timeline all read the same notes.

## Before you publish

- Is the thing itself already live on its platform?
- Is `external_url` (or `youtube_id`) filled in — and correct?
- Is `date` right, `timeline: true` set, and `timeline_type` right?
- Does `timeline_summary` make sense on its own?
- Have you changed `draft` to `false`?
