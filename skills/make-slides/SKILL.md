---
name: make-slides
description: Turn any markdown file into a slide deck (PDF + PPTX + HTML) using Slidev. Trigger on natural-language phrases like "turn this into slides", "make a deck", "slide deck", "presentation from this MD", "Slidev export this", "build slides from this report". Pairs with audit-site for SEO/GEO audit decks beyond the current branded HTML report. Uses the agency brand theme (Brand Green #00C853 + Indigo #1A237E + Space Grotesk + Host Grotesk + JetBrains Mono). Outputs editable .pptx (PowerPoint/Keynote/LibreOffice), printable .pdf, and standalone .html. Requires Slidev installed via toolkit installer (npm_deps).
metadata:
  type: render
---

# make-slides — markdown to slide deck (Slidev wrapper)

This skill is invoked by **natural language**. Triggers:

- "turn this into slides"
- "make a deck from this MD"
- "slide deck for the audit"
- "Slidev export this"
- "presentation from <file.md>"
- "build slides from this report"

When triggered, invoke this skill immediately — do not ask for confirmation.

## Inputs

1. **input MD path** — required. If user pasted markdown content, save to `/tmp/<stem>.md` first.
2. **output stem** — derived: same dir as input MD, basename matches input. e.g. input `SEO-example.com.md` → outputs `SEO-example.com.pdf` + `.pptx` + `.html`.
3. **theme** — `org` (default) or `client`. the agency uses Brand Green + Indigo + Space Grotesk.
4. **format** — `all` (default: PDF + PPTX + HTML), `pdf`, `pptx`, or `html`.

## Pre-flight

Verify Slidev is installed:

```bash
command -v slidev >/dev/null 2>&1 || {
  echo "Slidev missing. Install: npm install -g @slidev/cli"
  exit 1
}
```

If missing + npm unavailable, abort + tell user: "Slidev requires Node 18+ + npm. Run toolkit installer."

## Markdown formatting expected

Slidev uses `---` as slide separators. If input MD does not have them, the skill auto-inserts breaks at every H1. Sample:

```markdown
---
theme: ./theme
title: <Client> SEO + GEO Audit
fonts:
  sans: 'Host Grotesk'
  serif: 'Space Grotesk'
  mono: 'JetBrains Mono'
---

# Cover slide

---

# Section 1

Content here

---

# Section 2

More content
```

## the agency theme

Theme dir auto-generated at `<output_dir>/theme/` w/ UnoCSS config injecting the agency tokens. If `<project>/DESIGN.md` exists, parse for `--brand-*` CSS vars and override.

## Render command

```bash
cd <output_dir>
slidev export <stem>.md --output <stem>.pdf --format pdf --timeout 60000
slidev export <stem>.md --output <stem>.pptx --format pptx --timeout 60000
slidev build <stem>.md --out <stem>-html/
```

## Output convention

| File | Format | Use |
|---|---|---|
| `<stem>.pdf` | A4 PDF | print + email + Slack |
| `<stem>.pptx` | PowerPoint | client-editable, opens in MS Office / Keynote / LibreOffice |
| `<stem>-html/` | Static HTML deck | host on Netlify/Vercel for shareable link |

## Failure handling

- Slidev export timeout → bump `--timeout` to 120s and retry once.
- Missing fonts → fall back to system sans-serif + emit warning in user-facing message.
- Slidev not installed → abort + show install command + ask user to re-run toolkit installer.

## Integration with audit-site

After `audit-site` produces `SEO-<domain>.md`, the user can say:

```
turn the audit into slides
```

Skill picks up the most recent `SEO-*.md` in the active project's `audits/<date>/` dir + renders all 3 formats. Drops in same audit dir.

## Final user-facing message

```
Slide deck ready:
- PDF:  <output_dir>/<stem>.pdf
- PPTX: <output_dir>/<stem>.pptx
- HTML: <output_dir>/<stem>-html/index.html
Open PPTX in PowerPoint/Keynote/LibreOffice to edit.
```

## When NOT to use this skill

- User wants a **report**, not a deck → use `audit-site` (branded HTML report + A4 PDF).
- User wants a **PDF only** of long-form markdown → use `make-pdf` (gstack skill, Playwright-based).
- User wants a **single page mockup**, not slides → use `design-html` (gstack skill).

`make-slides` = specifically slide-format output (one major idea per slide, designed for presentation projection).
