# Site content system

This vault is also the Hugo site, and the site is an index. Notes in `content/` describe something published elsewhere and point at it; the site itself renders no post bodies. `external_url` is therefore the field that matters.

The day-to-day version of this document is `TIMELINE-GUIDE.md`.

## Required frontmatter

```yaml
title: "The human-readable title"
date: 2026-07-26
draft: true
timeline: true
timeline_type: writing
timeline_summary: "One clear sentence for the card."
external_url: "https://tstowx.substack.com/p/the-post"
```

`timeline: true` is the switch that places a note on the homepage. `draft: false` publishes it. A note with no `external_url`, `youtube_id` or `website_url` falls back to a page on this site — allowed, but it means you are hosting a copy here.

## How the outbound URL is decided

`layouts/partials/outbound.html` is the only rule. Priority:

1. `youtube_id` → `https://www.youtube.com/watch?v={id}`
2. `platform: x` + `author_handle` + `post_id` → `https://x.com/{handle}/status/{id}`
3. `timeline_type: project` + `website_url` → that site
4. `external_url` → verbatim
5. `.RelPermalink` (this site)

It returns `dict "url" "external" "platform" "label"`, and everything that renders a link consumes it: the dashboard cards, the films row, the essays list, the archive grid, the `/timeline/` cards, list pages and the RSS items.

## Redirects

`hugo.yaml` adds a `redirects` output format for the home page (`mediaType: text/netlify`, `baseName: _redirects`, `isPlainText: true`). `layouts/index.redirects` ranges over every page, asks `outbound.html`, and emits a forced 301 for `{RelPermalink}`, the slashless variant and every alias:

```
/bro-text/  https://tstowx.substack.com/p/bro-text  301!
/bro-text  https://tstowx.substack.com/p/bro-text  301!
/writing/bro-text/  https://tstowx.substack.com/p/bro-text  301!
```

The `!` makes Netlify override the file Hugo still writes at that path. That file is `layouts/_default/single.html` + `partials/go.html`: a short "this one lives on Substack" page, used by local previews. `layouts/partials/head.html` also emits `noindex` and a canonical pointing at the platform for the same pages.

## Timeline types

| Type | Extra frontmatter | What it is for |
| --- | --- | --- |
| `writing` | `external_url` | An essay, wherever it was published. |
| `substack` | `external_url`, `opengraph_image` | A Substack post; the card uses the post's own Open Graph image. |
| `place` | `external_url` | Travel and place-based pieces. |
| `note` | `external_url` | Shorter personal updates. |
| `video` | `youtube_id` | A YouTube film; the card uses the YouTube thumbnail. |
| `social` | `platform`, `author_handle`, `post_id` | An X post, embedded in the card archive. |
| `project` | `website_url`, `external_url`, `trustmrr_embed`, `dashboard_accent` | A venture or product. |
| `link` | `external_url` | A link worth keeping. |
| `image` | `timeline_image` | A photograph or image-led entry. |

The card uses `timeline_summary`, then `description`, then the opening of the note. `timeline_image` is an optional card image (`/attachments/photo.jpg`).

## Embedding

The shortcodes still exist for the rare note whose body is worth writing here. They read the same frontmatter:

```md
{{< youtube-video >}}
{{< x-post >}}
{{< og-card url="https://example.com" title="Title" description="Why it is worth opening." site="example.com" image="/attachments/cover.jpg" >}}
```

`og-card` never scrapes third-party pages at build time; the metadata you type is what renders.

## Editable homepage copy

The hero heading, intro, Now status, photography blurb and socials live in [`hugo.yaml`](../hugo.yaml) under `params.dashboard`. The intro copy on the chronological index lives under `params.timelineHome`.
