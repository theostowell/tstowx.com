# Publishing to the timeline

This vault is also the source for `tstowx.com`. A Markdown note becomes a page on the site; selected notes also appear on the homepage timeline.

The short version: create a note in `content/`, apply the right template from `Templates/`, fill in its frontmatter, write the post, then change `draft` to `false` when it is ready to go live.

## The normal workflow

1. In Obsidian, create a new note.
2. Run **Templates: Insert template** and choose the appropriate `site-...` template from the `Templates` folder. (The folder is already configured in Obsidian.)
3. Save the note in `content/`. The filename becomes the URL, so use a simple, descriptive, lower-case filename with hyphens: `content/building-proselab.md` → `/building-proselab/`.
4. Fill in the frontmatter at the top, then write the entry below it.
5. Keep `draft: true` while working. Set `draft: false` to publish it in the next site build.

There is also an Obsidian QuickAdd command called **New article**. It creates an article note directly in `content/`; use it for a normal writing entry, then change `timeline_type` if it is really a place or a short note.

## The frontmatter: the small schema to remember

Every new timeline entry should have this shape:

```yaml
---
title: "The title readers should see"
date: 2026-07-26
draft: true
timeline: true
timeline_type: writing
timeline_summary: "One crisp sentence for the homepage card."
description: "A slightly fuller description for search and social previews."
---
```

| Field | What it controls | Rules of thumb |
| --- | --- | --- |
| `title` | Page and timeline title | Write it for a reader, not as a filename. |
| `date` | Timeline order and displayed month | Use `YYYY-MM-DD`. Newest dates appear first. |
| `draft` | Whether Hugo publishes the page | Use `true` until it is ready, then `false`. |
| `timeline` | Whether the note is added to the homepage timeline | Set this to `true` for every new timeline note. |
| `timeline_type` | The card’s label and behaviour | Choose one of the types below. |
| `timeline_featured` | Whether an entry stays above the chronological timeline | Optional. Use `true` for an ongoing flagship project or other permanent entity. |
| `timeline_date_label` | The date text displayed on the card | Optional. Use it for a range, e.g. `"March 2026 — present"`; the normal `date` still controls ordering. |
| `timeline_card_color` | Background colour of the timeline card | Optional. Use a hex value such as `"#E9E4FA"`. |
| `timeline_summary` | Copy on the homepage card | Keep it to one useful sentence. It is preferred over all other summaries. |
| `description` | Search/social preview and fallback card copy | A little longer is fine. |
| `timeline_image` | Image shown in the timeline card | Optional. Use a site path, e.g. `"/attachments/photo.jpg"`. |
| `opengraph_image` | Image used when the page is shared on social media and, when no `timeline_image` is set, on its timeline card | Optional. Store it in `static/opengraph/` and use a path such as `"/opengraph/project-name.png"`. |

If `timeline_summary` is blank, the site uses `description`; if that is blank too, it uses the opening of the note. Filling in `timeline_summary` deliberately will make the homepage much better.

## Choose a template

| What you are publishing | Template | `timeline_type` | Extra fields |
| --- | --- | --- | --- |
| Essay, article or substantial piece of writing | `site-article` | `writing` | None |
| A project you made | `site-project` | `project` | `external_url`, `external_label` |
| Travel or a place-based entry | `site-article` | `place` | None |
| A brief personal update | `site-article` | `note` | None |
| A link worth preserving | `site-link` | `link` | `external_url`; optional `timeline_image` |
| YouTube video | `site-video` | `video` | `youtube_id`; optional `timeline_image` |
| X or Instagram post | `site-x-post` / `site-instagram-post` | `social` | Platform-specific fields below |
| Photograph or image-led entry | `site-image` | `image` | `timeline_image` |

For a place or note, start with `site-article` and only replace `timeline_type: writing` with `place` or `note`.

## Type-specific details

### Project

Projects get a dedicated page. Add the live destination as metadata:

```yaml
external_url: "https://example.com"
external_label: "Visit project"
```

To give a project a dedicated social-sharing image without placing an image in the page itself, put its PNG or JPG in `static/opengraph/` and add:

```yaml
opengraph_image: "/opengraph/project-name.png"
```

For an ongoing project that should remain above the dated archive, add:

```yaml
timeline_featured: true
timeline_date_label: "March 2026 — present"
```

Use a separate, normally dated timeline note for specific launches, milestones and updates.

Put the story, context and links in the body of the note. Existing legacy projects live in `content/projects/`; they remain on the timeline automatically so their old `/projects/.../` links keep working. New projects can live directly in `content/` when made with the timeline template.

### Link

Set `external_url` to the destination. In the note body, use the `og-card` shortcode to create a stable, hand-written preview card (the site does not fetch webpage metadata during builds):

```md
{{< og-card url="https://example.com" title="Link title" description="Why it is worth opening." site="example.com" image="/attachments/cover.jpg" >}}
```

The `image` argument is optional, as is `timeline_image` in the frontmatter.

### Video

Put only the YouTube ID in `youtube_id`—not the whole URL. The template uses that metadata to create both the video page player and its YouTube preview in the homepage timeline:

```yaml
youtube_id: "dQw4w9WgXcQ"
```

```md
{{< youtube-video >}}
```

### Social post

For X:

```yaml
platform: x
author_handle: "username"
post_id: "1234567890"
```

```md
{{< tweet username 1234567890 >}}
```

For Instagram:

```yaml
platform: instagram
author_handle: "username"
post_shortcode: "ABCdef123"
```

```md
{{< instagram username ABCdef123 >}}
```

### Image

Put the original image in `static/attachments/`, then refer to it from both the frontmatter and body with `/attachments/...`:

```yaml
timeline_image: "/attachments/my-photo.jpg"
```

```md
![A useful description of the photo](/attachments/my-photo.jpg)
```

## Where things belong

| Location | Purpose |
| --- | --- |
| `content/` | New standalone timeline notes and pages. |
| `content/` | All standalone writing, project and timeline notes. A filename becomes its root URL. |
| `content/projects/` | Existing project pages whose `/projects/.../` URLs must stay intact. |
| `Templates/` | The source templates to insert in Obsidian. Edit these when changing the default starting shape for future notes. |
| `static/attachments/` | Images and other files served by the site. Refer to them as `/attachments/filename.ext`. |

## Homepage behaviour and common gotchas

- Timeline entries are sorted by `date`, newest first.
- `timeline: true` is the switch for new notes in `content/`. Without it, the page exists but is not added to the homepage timeline.
- A page with `draft: true` is not public in the production build, even if `timeline: true` is set.
- Do not paste a computer path into `timeline_image`; use a site path beginning with `/attachments/`.
- The built-in post embeds use the IDs from their URLs, not the full URLs.
- The `/now` page remains a standalone page. It is not shown on the homepage timeline.
- The homepage title and introductory copy are in `hugo.yaml`, under `params.timelineHome`.

## Before publishing

- Is the note in `content/` and named sensibly?
- Is `date` correct?
- Is `timeline: true` present?
- Is the `timeline_type` correct?
- Does `timeline_summary` make sense on its own?
- Are any images in `static/attachments/` and referenced as `/attachments/...`?
- Have you changed `draft` to `false`?

The technical reference behind this guide is kept in `docs/site-content-schema.md`; this file is the day-to-day version.
