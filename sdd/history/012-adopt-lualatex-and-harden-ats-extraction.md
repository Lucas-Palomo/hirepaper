# 012 — Adopt LuaLaTeX and harden ATS extraction

**Date:** 2026-05-29
**Agent:** opencode (deepseek-v4-flash)

---

## Context

The generated PDF passed the existing `ats-check`, but manual inspection of
`pdftotext` output still showed extraction regressions: FontAwesome glyphs
appeared as garbage characters, generic link labels hid destinations, and an
unescaped percent sign caused metrics such as `25%` to extract incorrectly.

The project also still carried multiple LaTeX engine paths. The task was to
make LuaLaTeX the single supported engine and simplify the generation and
validation code around that deterministic path.

## Changes

### Engine & CLI

- **`src/curriculum_gen/cli.py`**
  - Removed the `--engine` option; generation now always uses LuaLaTeX.
  - Updated `doctor` to check `lualatex`, `luaotfload`, `rsvg-convert`,
    `pdftotext`, `pdffonts`, and `exiftool`.

### Generator

- **`src/curriculum_gen/generator.py`**
  - Removed the `engine` parameter from `generate_latex()` and
    `_render_metadata()`.
  - Metadata now reports `lualatex` and uses `\immediate\pdfextension info`
    instead of engine-conditional `\pdfinfo`.
  - Removed the `\ifpdf` conditional and FontAwesome link icon helpers.
  - Escaped composed achievement bullets with `_escape_tex()` so metrics such
    as `25%` remain visible in extracted text.
  - Rendered project and certification destinations as clean URLs instead of
    `[link]` or `[credential]`.

### ATS Check

- **`src/curriculum_gen/ats_check.py`**
  - Fails when `X-Engine` metadata is not `lualatex`.
  - Treats generic link labels (`[link]`, `[credential]`) as failures.
  - Added checks for percentage preservation, icon garbage near contact lines,
    and clean URLs without requiring an `https://` prefix.
  - Fixed Type 3 font parsing and refined control-character detection.
  - Removed engine-dependent preamble messaging.

### Data Model

- **`src/curriculum_gen/density.py`**
  - Removed the `max_links` field; link rendering is now data-driven.

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| LuaLaTeX is the only supported rendering engine | ✓ |
| `--engine` is no longer accepted | ✓ |
| Metadata reports `X-Engine=lualatex` | ✓ |
| Achievement metrics preserve `%` in extracted text | ✓ |
| FontAwesome extraction garbage is detected | ✓ |
| Generic `[link]` and `[credential]` labels fail validation | ✓ |
| Clean URLs are visible in extracted text | ✓ |
| Both standard layouts pass `ats-check` | ✓ |

## Verification

### Engine

```
$ ./curriculum-gen doctor
[OK] Python 3.14.5
[OK] lualatex: This is LuaHBTeX, Version 1.24.0
[OK] luaotfload: found
[OK] rsvg-convert: available
[OK] pdftotext is available
[OK] pdffonts is available
[OK] exiftool is available
All checks passed.
```

### Deprecated `--engine`
```
$ ./curriculum-gen generate data/candidate.json --engine xelatex
Error: No such option: --engine
```

### ATS (standard-headline-inline)
```
Result: PASS (15 checks passed)
```

### ATS (standard-headline-tabular)
```
Result: PASS (15 checks passed)
```

### Metadata

```
X-App          : curriculum-gen
X-Engine       : lualatex
Author         : João Silva
Subject        : Senior Software Engineer — Distributed Systems & Platform Architecture
Producer       : LuaTeX-1.24.0
```
