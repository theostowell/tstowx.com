# Site content system

This vault is also the Hugo site. All standalone writing and timeline entries live directly in `content/` as individual Markdown notes.

Use Obsidian’s Templates command and choose one of the `Templates/site-*.md` templates. `Templates/` is configured as this vault’s template folder and is stored in the repository.

## Required frontmatter

```yaml
title: "The human-readable title"
date: 2026-07-26
draft: true
timeline: true
timeline_type: writing
timeline_summary: "One clear sentence for the timeline card."
description: "A slightly longer description for search and social previews."
```

`timeline: true` is the switch that places a new note on the homepage timeline. Set `draft: false` when it is ready to publish. Files without `timeline: true` are not added automatically.

## Timeline types

| Type | Obsidian template | Extra frontmatter | What it is for |
| --- | --- | --- | --- |
| `writing` | `site-article` | — | Essays, articles and standalone writing. |
| `project` | `site-project` | `external_url`, `external_label` | A permanent page for something you have made. |
| `place` | `site-article` | `timeline_type: place` | Travel and place-based entries. |
| `note` | `site-article` | `timeline_type: note` | Shorter personal updates. |
| `link` | `site-link` | `external_url`, optional `timeline_image` | A link worth preserving, with an on-page Open Graph-style card. |
| `video` | `site-video` | `youtube_id` | A YouTube video; it plays inline on its page and receives a YouTube thumbnail preview in the timeline. |
| `social` | `site-x-post` / `site-instagram-post` | Platform fields below | An embedded X or Instagram post. |
| `image` | `site-image` | `timeline_image` | A photograph or image-led entry. |

The timeline uses `timeline_summary` first, then `description`, then the beginning of the note. `timeline_image` is an optional image displayed in the timeline card; use a site-relative path such as `/attachments/photo.jpg`.

## Embeds

Hugo shortcodes keep embeds portable and readable in Markdown. For a video note, fill in `youtube_id` in the front matter and use the local shortcode; this also powers its timeline preview:

```md
{{< youtube-video >}}
{{< tweet USERNAME STATUS_ID >}}
{{< instagram USERNAME SHORTCODE >}}
```

For ordinary links, use the local `og-card` shortcode. It does not scrape third-party pages at build time: enter the title, description and optional image deliberately so the card remains stable.

```md
{{< og-card url="https://example.com" title="Title" description="Why this is worth opening." site="example.com" image="/attachments/cover.jpg" >}}
```

## Projects and URLs

Each project gets one dedicated Markdown note. Write the project story in the note and put the live destination in `external_url`; the homepage card will offer both the permanent project page and the external project link.

The existing project pages remain in `content/projects/` so their current `/projects/.../` URLs keep working. New timeline notes can be created directly in `content/` as described above.

## Editable homepage copy

The homepage heading and introduction are configured in [`hugo.yaml`](../hugo.yaml), under `params.timelineHome`:

```yaml
timelineHome:
  title: "A life in projects, places and words."
  content: |
    First paragraph.

    Second paragraph.
```

Edit those two fields to change the homepage intro without touching a template.
