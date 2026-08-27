---
name: proofread
description: Make minimal grammatical corrections in British English. Fixes only glaring errors, not stylistic choices. Handles //instructions// literally.
argument-hint: <file-name-or-path>
allowed-tools: [Read, Edit, Grep, Glob, Bash]
---

# /proofread

Fix only the most primitive, unambiguous grammatical errors in a piece of writing. British English. Never touch style.

This is the tstowx.com port. Prefer the active/target file when Invoker (Agent Skills) passes one.

## Input

The target is, in order:

1. The **active/target vault file** when Invoker (or another worker) passes one — use that path directly. If an editor selection is present, still proofread the whole file; the selection is just context for where Theo was looking.
2. Otherwise `$ARGUMENTS` — a filename, path, or partial match inside `/Users/theostowell/tstowx.com/`.

Examples:

- `/proofread if-not-now-then-when`
- `/proofread content/if-not-now-then-when.md`

## File Resolution

1. If a target file path is already provided, use it.
2. If `$ARGUMENTS` is a full path that exists, use it directly.
3. If it's a filename or partial name, search `/Users/theostowell/tstowx.com/` for a match:

```bash
find /Users/theostowell/tstowx.com/content /Users/theostowell/tstowx.com/docs /Users/theostowell/tstowx.com/templates -name "*$ARGUMENTS*" -type f
```

4. If multiple matches, ask Theo which one. Never guess.

Most writing lives as flat Markdown in `content/`.

## What to Fix

**ONLY fix these — actual grammatical errors in British English:**

- Subject-verb agreement ("he don't" → "he doesn't")
- Missing articles where grammatically required ("I went to shop" → "I went to the shop")
- Wrong tense that's clearly a mistake, not a stylistic choice
- Obvious typos and misspellings
- Its/it's, their/they're/there, your/you're — only when clearly wrong
- Missing full stops at end of sentences (but not in bullet points or headings)
- Unclosed quotation marks or brackets

**British English specifics:**

- Use British spellings (organise, colour, centre, etc.)
- Use single quotes for quotation marks unless doubles are already used consistently throughout the piece
- "s" not "z" where British English prefers it (realise, specialise)

## What to NEVER Touch

- Sentence fragments used for emphasis or rhythm
- Starting sentences with "And", "But", "So", etc.
- Informal register, slang, or colloquialisms
- Paragraph length or structure
- Word choice (even if you'd pick a different word)
- Comma usage (unless a comma splice makes the sentence genuinely unreadable)
- Oxford comma presence or absence — leave as-is
- Em dashes, ellipses, or other punctuation style choices
- Capitalisation choices (unless mid-sentence proper noun is lowercase by obvious mistake)
- Frontmatter fields, Hugo shortcodes, aliases, or timeline metadata
- Anything that could be a deliberate stylistic decision — when in doubt, leave it

## Handling `//instructions//`

Text inside double slashes `//like this//` is a **literal instruction to you**. Do NOT treat it as prose to proofread. Instead:

1. Read the instruction inside the slashes
2. Execute it — e.g. `//leave a URL to the photography site//` means you find the correct URL and insert it
3. Remove the `//` wrappers and replace with the result
4. If you can't determine what the instruction asks for, flag it to Theo rather than guessing

Common instruction patterns:

- `//link to X//` — find and insert the correct URL or wikilink
- `//leave a url to X//` — same as above
- `//insert X here//` — find and insert the referenced content
- `//TBD//` or `//TODO//` — leave as-is unless Theo says otherwise

To resolve URLs, check the site structure:

```bash
ls /Users/theostowell/tstowx.com/content/
```

The default URL pattern is `https://tstowx.com/[slug]/`, derived from the content filename. Some older writing notes keep an alias such as `/writing/[slug]/` — prefer the alias if the file already has one. External destinations (Substack, ProseLab, PARAZETTEL, photos.tstowx.com) should use the URL already in that note's frontmatter when present.

## Cleaning Up Editorial Comments

If the file contains HTML comments left by `/editor` (formatted as `<!-- [N] ... -->`), **remove them all**. These are editorial suggestions that have already been addressed or rejected. A proofread means the piece is being finalised — no comments should survive into the published version.

Also remove any other stray HTML comments that aren't part of the content (e.g. `<!-- TODO -->`, `<!-- NOTE: ... -->`). Hugo shortcode comments (`{{/*  */}}`) should be left alone.

## Process

1. **Read the file** in full
2. **Strip editorial comments** — remove any `<!-- [N] ... -->` blocks and other stray HTML comments
3. **Identify errors** — list them mentally, only the glaring ones
4. **Make edits** using the Edit tool, one at a time or in small batches
5. **Handle any `//instructions//`** — resolve them as described above
6. **Report** — tell Theo what you changed in a brief summary. Format:
   - Number of editorial comments removed
   - Number of grammatical fixes
   - Any `//instructions//` you resolved
   - Any `//instructions//` you couldn't resolve (flag these)
   - If you found zero errors, just say so — don't invent things to fix

There is no PARAZETTEL style guide on this site. Do not import `parazettel.com/docs/style-guide.md` rules (bold → italics, "over" → "more than", forced Oxford commas, etc.). This is personal writing; catch slips only.

## Principles

- **Minimal intervention.** If you're debating whether something is an error or a choice, it's a choice. Leave it.
- **This is Theo's voice.** He writes in a specific way. Your job is to catch slips, not to edit.
- **British English is the standard.** But don't go converting an entire piece that's already in American English — flag it instead and ask.
- **No AI slop.** Don't rewrite sentences to be "clearer" or "more concise". That's not what this is for.
