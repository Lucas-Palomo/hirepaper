# 031 - Fix header link wrap consistency and alignment in `standard` layout

**Date:** 2026-06-08
**Agent:** opencode (deepseek-v4-flash)

---

## Context

The `standard` layout rendered header links inline in the contact block via `_render_links()`, joining items with `\hfill`. Each item rendered as `Label: \href{url}{display}`. Two problems existed:

1. **Intra-item wrapping:** Under tighter widths LaTeX could wrap between the label and the URL (e.g., `LinkedIn:` on one line and the URL on the next), breaking atomicity.
2. **Justified spacing:** `\hfill` between items inside `\centering` caused links to be distributed with justified spacing instead of left-aligned, which looked inconsistent when links wrapped to multiple lines.

## Changes Made

### 1. Atomic link items via `\mbox`

Wrapped each header link item in `\mbox{}` in three places in `src/curriculum_gen/generator.py`:

- **`_render_links()`** — wraps each `\iconLink\ {label}: \href{url}{display}` in `\mbox{}` so the label and URL form an unbreakable unit.
- **`_render_contact_table()` `fmt()` helper** — same fix for the tabular contact rendering path.
- **`generate_latex()` inline `LINK{i}` replacements** — same fix for per-link template variables.

### 2. Left-aligned links separated from centered contact

- **`templates/standard.tex`:** Moved `{LINKS}` out of `\resumeContact{...}` into its own `\resumeLinks{...}` block.
- **`templates/standard.cls`:** Added `\resumeLinks` command using `\raggedright` for left alignment.
- **`_render_links()`:** Replaced `\hfill` separator between items with `\quad` (fixed 1em space) to prevent justification while preserving readability.
- **`_render_contact_table()`:** Replaced `\hfill` with `\quad` for the same reason.

### 3. Atomic contact items via `\mbox` (perfumaria)

Wrapped each contact item (email, phone, location) in `\mbox{}` in `templates/standard.tex`:

```latex
\mbox{\iconEmail\ {LABEL_EMAIL}: {EMAIL}}\hfill
\mbox{\iconPhone\ {LABEL_PHONE}: {PHONE}}\hfill
\mbox{\iconPin\ {LABEL_LOCATION}: {LOCATION}}
```

This prevents line breaks between the icon, label, and value of each contact item — consistent with the link `\mbox` protection.

### 4. Resulting behavior

- Contact info (email, phone, location) remains centered with `\hfill` spacing.
- Header links are rendered below in a separate left-aligned block.
- Each `Label: visible-url` item is atomic — no line break between label and URL.
- Items wrap at `\quad` boundaries as whole units.

## Verification

### Source-mode (dev entry point)

```bash
./curriculum-gen-dev pdf generate data/candidate.json -o /tmp/header-wrap-standard.pdf --density compact --locale en
./curriculum-gen-dev pdf check /tmp/header-wrap-standard.pdf           # PASS (15 checks)
pdftotext /tmp/header-wrap-standard.pdf -     # All labels+URLs intact, contact then links

./curriculum-gen-dev pdf generate data/candidate.json -o /tmp/header-wrap-full.pdf --density full --locale en
./curriculum-gen-dev pdf check /tmp/header-wrap-full.pdf               # PASS with warnings (1 warn, 15 ok)

# Stress fixture (5 links, long labels + long URLs)
./curriculum-gen-dev pdf generate /tmp/curriculum-gen-stress-header.json -o /tmp/header-wrap-stress.pdf --density compact --locale en
./curriculum-gen-dev pdf check /tmp/header-wrap-stress.pdf             # PASS with warnings (1 warn, 14 ok)
```

### Packaged mode

```bash
.venv/bin/python build.py

./curriculum-gen pdf generate data/candidate.json -o /tmp/header-wrap-packaged.pdf --density compact --locale en
./curriculum-gen pdf check /tmp/header-wrap-packaged.pdf               # PASS (15 checks)
```

### Extracted text (default candidate)

```
Email: joao.silva@email.com
Phone: +55 11 99999-9999
Location: São Paulo, SP
LinkedIn: linkedin.com/in/joaosilva
GitHub: github.com/joaosilva
StackOverflow: stackoverflow.com/users/~joaosilva
```

All header link labels and URLs on single lines, contact info followed by links.

## Decisions & Tradeoffs

- Chose `\mbox` (non-breaking box) over tabular/multiline approaches — simplest fix for intra-item break protection.
- Chose `\quad` over `\hfill` for link spacing — `\hfill` combined with `\raggedright` still produces partial justification since both use `\fill`-order glue, while `\quad` gives fixed spacing with true left alignment.
- Chose separate `\resumeLinks` command over inline fix — `\\` inside `\centering` cannot be overridden per-line by `\raggedright`, so separating the block was necessary for reliable left alignment.
- All three link-rendering paths were updated for consistency.

## Residual Risks

- With an extremely long email (40+ chars) the centered contact line may overflow, causing Location text to appear after links in PDF text extraction. This is a cosmetic text-extraction artifact limited to extreme edge cases.
- Visual inspection of rendered PDF images was not performed due to tool limitations; only text extraction and ATS check results are available.
