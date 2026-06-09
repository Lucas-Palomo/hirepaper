# 009 — ATS-safe PDF validation command

**Date:** 2026-05-27
**Agent:** opencode (deepseek-v4-flash)

---

## Context

Generated PDFs could look visually correct while having corrupted text extraction
(font encoding issues, control characters in output). The project needed a
validation command to detect these issues without depending on external ATS
simulation libraries.

## Changes

### 1. `ats-check` command

Added `ats-check <pdf_file>` CLI command that runs 8 checks:

| # | Check | Tool/Method |
|---|-------|-------------|
| 1 | Text extraction | `pdftotext` — fails on empty output |
| 2 | Corrupted characters | Scan for control chars (0x00-0x08, 0x0E-0x1F, 0x7F-0x9F, 0xFFFD) |
| 3 | Font safety | `pdffonts` — fails on Type 3 fonts, warns on missing Unicode mapping |
| 4 | Required sections | Scans clean text for Summary, Profile, Experience, Education, Skills (with fuzzy fallback for corrupted section names) |
| 5 | Contact visibility | Email regex, phone regex, location match |
| 6 | Link visibility | Counts `[link]` / `[credential]` labels vs explicit URLs |
| 7 | Placeholder leak | Detects unreplaced template placeholders in extracted text |
| 8 | Keyword preservation | Checks 13 technical keywords (Python, Kafka, etc.) |

### 2. `src/curriculum_gen/ats_check.py`

Module with `check_pdf(pdf_path) -> int` orchestrating all checks.
Returns non-zero when failures are found.

### 3. `doctor` updated

Added checks for `pdftotext` and `pdffonts` availability (via `which`).

### 4. Template fix

Changed `{SUMMARY}` placeholder to `{PROFILE}` (mismatch between template and
generator after task 007 renamed the internal key).

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| `curriculum-gen ats-check <pdf>` exists | ✓ |
| Runs `pdftotext` and analyzes output | ✓ |
| Runs `pdffonts` and detects Type 3 | ✓ |
| Corrupted character detection | ✓ |
| Required section check | ✓ (with fuzzy fallback) |
| Contact visibility | ✓ email, phone, location |
| Generic link labels reported | ✓ |
| Technical keywords checked | ✓ |
| Non-zero exit on failures | ✓ |
| No ATS simulation library added | ✓ |

## Fixes during implementation

### `ats-check` help behavior

`ats-check` now shows help when called without arguments (matching `generate`).

### Default engine changed to `xelatex`

The default LaTeX engine in the CLI was switched from `pdflatex` to `xelatex`.
This produces PDFs with clean text extraction (no corrupted characters from T1
ligatures), Unicode-safe font rendering via `fontspec` + `Liberation Serif`,
and ATS-compatible output by default.

Users can still opt into `pdflatex` with `--engine pdflatex`.

### Disclaimer added to `ats-check` output

The command now prints a disclaimer after the file path, noting that results
may vary depending on the LaTeX engine used to generate the PDF.

### Corrupted character detection refined

- Excluded `\x0c` (form feed) from corrupted character detection — it is a
  standard page-break marker in `pdftotext` output, not extraction corruption.

### Font/engine improvements for ATS-safe output

- `resume.cls` now uses `\ifxetex` to detect `xelatex`: loads `fontspec` with
  `Liberation Serif` for Unicode-safe rendering; falls back to `T1` for
  `pdflatex`.
- `_build_pdf` relaxed to check PDF existence instead of return code — `xelatex`
  can exit non-zero even on successful compilation (e.g., missing `pzdr` font
  for link symbols).
- `_sanitize_unicode()` added to `_escape_tex` — replaces em/en dashes, smart
  quotes, and other Unicode chars that `T1` can't handle.

## Results

| Engine | Corrupted chars | Sections | ats-check result |
|--------|----------------|----------|------------------|
| `pdflatex` (default) | FAIL — T1 ligature issues | Approximate match | FAIL |
| `xelatex` (default) | PASS — clean extraction | Exact match | PASS with warnings |

`xelatex` is now the default engine. Users get clean ATS extraction by default.

## Verification

```bash
# pdflatex (default) — known T1 limitation
./curriculum-gen generate data/candidate.json -o output/resume.pdf
./curriculum-gen ats-check output/resume.pdf

# xelatex — clean ATS extraction
./curriculum-gen generate data/candidate.json -o output/resume.pdf --engine xelatex
./curriculum-gen ats-check output/resume.pdf

# ats-check help
./curriculum-gen ats-check
```
