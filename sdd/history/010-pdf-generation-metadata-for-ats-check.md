# 010 — PDF generation metadata for ats-check

**Date:** 2026-05-28
**Agent:** opencode (deepseek-v4-flash)

---

## Context

`ats-check` validated PDFs as standalone artifacts but had no knowledge of whether
the PDF was produced by `curriculum-gen`, which engine was used, or which keywords
were expected. Keywords were hardcoded instead of being derived from the actual
candidate data.

## Changes

### 1. PDF metadata embedding (`generator.py`)

`_render_metadata()` generates a `\hypersetup{...}` block stored in the preamble
via the `{METADATA}` placeholder. Three standard PDF metadata fields are set:

- **`Author`**: candidate's name (e.g., `João Silva`).
- **`Subject`**: candidate's headline (e.g., `Senior Software Engineer — Distributed Systems & Platform Architecture`).
- **`Keywords`**: unified, deduplicated, comma-separated list of all rendered keywords.

Keywords are extracted during generation from:
- `skills.categories[].items` (capped by `max_skills_per_category`)
- `experience[].technologies` (capped by `max_experience_items`)
- `projects[].technologies` (capped by `max_projects`)

The keyword extraction respects the **active `DensityPolicy`** so that metadata
keywords match only what is actually rendered in the PDF, preventing false
negatives in `ats-check`.

### Custom X fields via `\special`

The backlog specified fields using the naming convention `X *` (space-separated,
e.g. `X App`, `X Engine`). During implementation, these were changed to
`X-*` (hyphen-separated, e.g. `X-App`, `X-Engine`) because PDF metadata keys
use hyphenated naming conventions and `exiftool` normalizes them to this format
when reading. The change is cosmetic — the data content and purpose are unchanged.

Custom metadata (`X-App`, `X-Engine`, `X-Keywords-Skills`, `X-Keywords-Experience`,
`X-Keywords-Projects`) are embedded via engine-conditional LaTeX:

- **pdflatex**: `\pdfinfo{ /X-App (curriculum-gen) ... }`
- **xelatex**: `\special{pdf: docinfo << /X-App (curriculum-gen) ... >>}`

The `\ifpdf` conditional (from `hyperref`) selects the correct syntax automatically.
Fields are visible via `exiftool` in both engines.

Special characters (`#`, `%`, `&`, `_`, `{`, `}`, `^`, `~`) in X field values are
TeX-escaped or replaced with safe alternatives to avoid compilation errors across
both engines. `\` is stripped (diagnostic fields do not need to preserve it).

### Code cleanup

The `x_meta` dict returned by `generate_latex()` was a leftover from an abandoned
approach (injecting metadata via `exiftool` post-processing). Since metadata is
fully embedded via LaTeX at generation time, `x_meta` was always empty. Removed:
- `x_meta` return value from `generate_latex()` and `_render_metadata()`
- `x_metadata` parameter from `_build_pdf()`
- `generate_latex()` now returns a plain `str` (not a tuple)

### `ats-check` message and validation fixes

Two issues corrected in `ats_check.py`:

**1. Imprecise message when `X-App` exists with a different value.**
Previously, any case where `x_app != "curriculum-gen"` emitted:
```
X-App metadata not found (PDF may not be from curriculum-gen)
```
even when `X-App` was present with a non-`curriculum-gen` value. Now
distinguishes three states:
- `X-App=curriculum-gen` → OK
- `X-App` present but different → `"X-App is '{value}', expected 'curriculum-gen'"`
- `X-App` absent → `"X-App metadata not found (PDF may not be from curriculum-gen)"`

**2. Missing warning for absent `Keywords` when `X-App=curriculum-gen`.**
Inside the `is_curriculum_gen` block, validation now checks `kw_raw` and
emits a warning when the canonical `Keywords` field is missing or empty,
regardless of whether `X-Keywords-*` fields are present.

### 2. `ats-check` metadata-driven validation

- Reads metadata via `exiftool` instead of using hardcoded keyword lists.
- `X-App=curriculum-gen` → enables project-specific validation.
- `X-Engine` → identifies the LaTeX engine used.
- `Author` and `Subject` → displayed as informational "Candidate:" and "Headline:".
- `Keywords` → used as aggregated list.
- `X-Keywords-*` → used as source-specific groups for comparison.
- Validates that `Keywords` aggregation matches the union of `X-Keywords-*` fields.
- Keyword preservation check uses metadata-provided keywords, deduplicated via
  `dict.fromkeys()`.
- Keywords from `X-Keywords-*` are deduplicated before display and comparison.

### 3. `doctor` updated

Added check for `exiftool` availability (install `perl-image-exiftool`).

### 4. Template change

Added `{METADATA}` placeholder in `resume.tex` preamble for the `\hypersetup` block.

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| PDFs include `X-App=curriculum-gen` | ✓ |
| PDFs include `X-Engine` with engine name | ✓ |
| PDFs include candidate name as `Author` | ✓ |
| PDFs include candidate headline as `Subject` | ✓ |
| PDFs include `Keywords` as clean deduplicated list | ✓ |
| Keywords derived deterministically from candidate data, density-aware | ✓ |
| `ats-check` reads metadata via `exiftool` | ✓ |
| `ats-check` continues generic validation when metadata absent | ✓ |
| `ats-check` applies project-specific checks when `X-App=curriculum-gen` | ✓ |
| `ats-check` uses metadata-provided keywords | ✓ |
| `doctor` checks for `exiftool` | ✓ |

## Verification

```bash
./curriculum-gen generate data/candidate.json -o output/resume.pdf
exiftool output/resume.pdf  # Author (name), Subject (headline), Keywords, X-App, X-Engine, X-Keywords-*
./curriculum-gen ats-check output/resume.pdf
./curriculum-gen doctor
```
