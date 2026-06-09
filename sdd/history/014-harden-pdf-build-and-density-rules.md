# 014 -- Harden PDF build validation and density rules

**Date:** 2026-05-29
**Agent:** opencode (deepseek-v4-flash)

## Context
PDF generation could report success for a partially built artifact when LuaLaTeX failed silently (e.g., unwritable font cache, missing fonts). Density policies were not aggressive enough about optional sections, and ATS diagnostics had several gaps.

## Changes

### `src/curriculum_gen/density.py`
- Added `show_languages: bool` to `DensityPolicy` — controls whether the Languages section renders.
- Added `min_extra_links_for_section: int` — minimum extra\_links count needed to render the Online section.
- `COMPACT`: `show_languages=False`, `min_extra_links_for_section=2`
- `FULL`: `show_languages=True`, `min_extra_links_for_section=1`

### `src/curriculum_gen/generator.py`
- **Metadata sanitization**: Unified the `escape()` inner function to use `_sanitize_for_pdf()` so `Keywords` and `X-Keywords-*` fields use identical escaping, eliminating false ATS warnings.
- **Education GPA/honors**: Moved from degree column to a separate `\resumeEntrySub{}` line after the main education entry.
- **Extra links density**: `_render_links_section()` now checks `policy.min_extra_links_for_section` — single extra\_links items are hidden in compact mode.
- **Languages density**: `_render_languages()` now accepts a `DensityPolicy` parameter and respects `show_languages`.
- Updated the sections list in `generate_latex()` to pass `policy` to `_render_languages()`.
- **Dynamic tabular header**: Replaced hardcoded `\resumeContactTable{...}{LINK0}{LINK1}{LINK2}` in the tabular template with `{CONTACT_TABLE}`. Added `_render_contact_table()` that generates the full tabular environment dynamically, pairing each contact row (email/phone/pin) with its corresponding link and appending extra rows for links beyond the third. Also added `Link` to imports.

### `templates/standard-headline-tabular.tex`
- Replaced the fixed 3-slot `\resumeContactTable{}{}{}{LINK0}{LINK1}{LINK2}` with a single `{CONTACT_TABLE}` placeholder, allowing any number of header links to render correctly.

### `src/curriculum_gen/cli.py`
- **Build hardening**: Added `_validate_pdf_artifact()` function that checks:
  - `pdftotext` returns non-empty text
  - `pdffonts` lists at least one font
  - No Type 3 fonts present
- Called after PDF copy in `_build_pdf()`. Returns exit code 2 for artifact validation failures. Error messages point to logs and likely font/cache issues.
- **Doctor hardening**: After checking binary existence, compiles a minimal LuaLaTeX document using `fontspec` and `DejaVu Sans`, validates text extraction, font embedding, and Unicode mapping. Reports actionable failure messages for font cache or compilation issues.

### `src/curriculum_gen/ats_check.py`
- **Required sections**: Replaced `["Summary", "Profile", ...]` with `["Profile", ...]` as canonical. Falls back to `Summary` as an alias for `Profile`.
- **Decimal percentages**: Changed regex from `\b\d+%` to `\b\d+(?:\.\d+)?%` to match `99.9%` correctly.
- **Empty extraction diagnostics**: Added diagnostic hints in the failure message (LaTeX failure, font loading, pdffonts check, log inspection).
- **Bullet length warning**: Added a warning (not failure) when extracted text lines exceed 180 characters, flagged as a scanability concern.

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Generation fails when LuaLaTeX produces a PDF with empty `pdftotext` output | Pass |
| 2 | Generation fails when `pdffonts` reports no fonts | Pass |
| 3 | Generation does not silently accept fatal `luaotfload`/`fontspec` failures | Pass |
| 4 | `doctor` compiles and validates a minimal `fontspec` + `DejaVu Sans` PDF | Pass |
| 5 | `doctor` reports actionable cache/font-loading failures | Pass |
| 6 | `ats-check` reports decimal percentages correctly | Pass |
| 7 | `ats-check` treats `Profile` as the canonical required section | Pass |
| 8 | Metadata keyword comparison no longer warns for escaping-only differences | Pass |
| 9 | `compact` renders a more essential resume (languages hidden, single extra link hidden) | Pass |
| 10 | GPA and honors render on a separate education sub-line | Pass |
| 11 | Single `extra_links` item does not create a standalone section in compact output | Pass |
| 12 | `full` still renders a single `extra_links` item when present | Pass |
| 13 | `ats-check` warns, but does not fail, when a bullet is unusually long | Pass |
| 14 | All 4 validation combinations (compact/full × inline/tabular) pass after changes | Pass |

## Verification

```text
== curriculum-gen doctor ==
[OK] Python 3.14.5
[OK] lualatex: This is LuaHBTeX, Version 1.24.0 (TeX Live 2026/Arch Linux)
[OK] luaotfload: found
[OK] rsvg-convert: available (for icon conversion)
[OK] pdftotext is available
[OK] pdffonts is available
[OK] exiftool is available

-- LuaLaTeX + fontspec + DejaVu Sans compilation test --
[OK] Minimal LuaLaTeX compilation succeeded
[OK] Text extraction from minimal PDF works
[OK] Fonts embedded in minimal PDF
[OK] Fonts expose Unicode mapping

All checks passed.

4/4 generation combos succeeded (compact/full × inline/tabular).
All 4 pass ATS check with 15/15 OK and Keywords match.
```
