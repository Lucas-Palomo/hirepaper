# 013 — Layout refinement for ATS safety

**Date:** 2026-05-29
**Agent:** opencode (deepseek-v4-flash)

---

## Context

After task 012 made LuaLaTeX the single engine and hardened ATS validation, the
generated PDF was technically compatible but still needed layout refinement.
The header was crowded, contact labels were hardcoded in English, links mixed
layout concerns into the data model, and entry blocks needed clearer visual and
extractable separation.

The task split the remaining layout work from the engine migration so the
project could provide ATS-safe headline variants without changing the LuaLaTeX
metadata path.

## Changes

### CLI

- **`src/curriculum_gen/cli.py`**
  - Reworked `_LAYOUT_MAP` to support multiple template pairs (`.tex` +
    `.cls`).
  - Added `cls_stem` handling so each layout keeps the matching class filename
    during PDF generation.
  - Added `_convert_icons()` to convert local SVG icons to PDF assets at build
    time via `rsvg-convert`.
  - Updated `doctor` to check `rsvg-convert`.

### Generator

- **`src/curriculum_gen/generator.py`**
  - Updated `_render_links()` to spread headline links with `\hfill` and keep
    visible labels.
  - Added `_render_links_section()` for extra links in a dedicated
    "Online"/"Links" section.
  - Added `LINK0`, `LINK1`, and `LINK2` replacements for the tabular headline
    layout.
  - Added locale-aware replacements for `LABEL_EMAIL`, `LABEL_PHONE`, and
    `LABEL_LOCATION`.
  - Inserted `\resumeEntrySep` only between experience and project entries,
    never after the last item.

### Data Model

- **`src/curriculum_gen/models.py`**
  - Removed `header: bool` from `Link`.
  - Added `extra_links: list[Link]` to `Personal`.
- **`src/curriculum_gen/loader.py`**
  - Parses `extra_links` separately from headline `links`.
- **`src/curriculum_gen/density.py`**
  - Removed `max_links`; layout placement is now schema-driven.

### Locale

- **`locale/en/LC_MESSAGES/messages.po`**
  - Added `label.email`, `label.phone`, `label.location`, and
    `section.links`.
- **`locale/pt_BR/LC_MESSAGES/messages.po`**
  - Added `label.email` (`E-mail`), `label.phone` (`Telefone`),
    `label.location` (`Localização`), and `section.links` (`Links`).
- Recompiled both `.mo` files.

### Assets

- **`assets/icons/envelope.svg`**, **`phone.svg`**, **`pin.svg`**,
  **`link.svg`**
  - Added monochrome decorative icons using accent color `#1a6b8a`.
  - Icons are converted to PDFs and do not add extractable text to
    `pdftotext`.

### Templates

- **`templates/standard-headline-inline.tex`** /
  **`templates/standard-headline-inline.cls`**
  - Default layout. Contact info and links are rendered in a single flow,
    spread with `\hfill`; name and headline are centered.
- **`templates/standard-headline-tabular.tex`** /
  **`templates/standard-headline-tabular.cls`**
  - Tabular headline layout. Each row pairs one contact item on the left with
    one link on the right.
- Both:
  - Use `DejaVu Sans` via `fontspec`.
  - Disable hyphenation with `\usepackage[none]{hyphenat}`.
  - Move the separator rule below the headline.
  - Add centered dashed entry separators at 55% width with 4pt vertical
    margins.
  - Use `0.65\textwidth + 0.35\textwidth` for entry and volunteer tabulars.
  - Use `0.60\textwidth + 0.40\textwidth` for the tabular contact table.
  - Reset separator style with `\normalsize\normalcolor` to prevent font or
    size leakage.

### Data Files

- **`data/candidate.json`**
  - `links` now contains three headline links; `extra_links` contains the
    portfolio link.
- **`data/example.json`**
  - Added an `extra_links` example.

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Both headline layouts compile | ✓ |
| Both layouts pass `ats-check` | ✓ |
| FontAwesome garbage is absent from extracted text | ✓ |
| `[link]` and `[credential]` are absent from extracted text | ✓ |
| Contact labels respect `en` and `pt-BR` locales | ✓ |
| Fonts are limited to DejaVu Sans, with no Type 3 fonts | ✓ |
| SVG icons are decorative only in extracted text | ✓ |
| Dashed separators appear only between entries | ✓ |
| Tabular layout produces paired contact/link rows | ✓ |

## Verification

### ATS (standard-headline-inline)

```
Result: PASS (15 checks passed)
```

### ATS (standard-headline-tabular)

```
Result: PASS (15 checks passed)
```

### pdftotext — inline

```
João Silva
Senior Software Engineer — Distributed Systems & Platform Architecture
Email: joao.silva@email.com
LinkedIn: linkedin.com/in/joaosilva
...
Phone: +55 11 99999-9999
GitHub: github.com/joaosilva
...
Location: São Paulo, SP
StackOverflow: stackoverflow.com/users/~joaosilva
```

### pdftotext — tabular (paired rows)

```
Email: joao.silva@email.com      | LinkedIn: linkedin.com/in/joaosilva
Phone: +55 11 99999-9999         | GitHub: github.com/joaosilva
Location: São Paulo, SP          | StackOverflow: stackoverflow.com/users/~joaosilva
```

### Locale pt-BR

```
E-mail: joao.silva@email.com
LinkedIn: linkedin.com/in/joaosilva
...
Localização: São Paulo, SP
Links
Portfolio: joaosilva.dev
```

### Fonts

Only `DejaVuSans` and `DejaVuSans-Bold` — single family, Identity-H encoding, embedded, Unicode mapped. No Type 3 fonts.
