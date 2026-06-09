# 041 - Add Markdown report output for human-readable report commands

**Date:** 2026-06-09

**Context:** The project's human-readable report commands (`content match`, `content tailor`, `linkedin generate`) needed a third output format — Markdown — alongside existing `text`/`txt` and `json`.

## Changes Made

### `content_match.py`
- Updated `_VALID_FORMATS` to `{"text", "md", "json"}`
- Added `render_markdown_report()` function with Markdown sections:
  - `# ATS Compatibility Analysis` title
  - `## Disclaimer`, `## Summary`, `## Score`, `## Strengths`, `## Gaps`
  - `## Matched Requirements`, `## Unmatched Requirements`, `## Inferences`
- Updated format branching in `run_match` to route `md` to the new renderer

### `content_tailor.py`
- Updated `_VALID_REPORT_FORMATS` to `{"text", "md", "json"}`
- Added `render_markdown_report()` function with Markdown sections:
  - Mode/Inference, Executive Summary, Target Role, Key Changes
  - Rewrites, Removed/Deprioritized Sections, Lint Status, Warnings
- Updated format branching in `run_tailor` to route `md` to the new renderer

### `linkedin_generate.py`
- Added `render_markdown_report()` function with Markdown sections:
  - Disclaimer, Profile Strategy, Headline, About/Summary
  - Top Skills, Experience/Project Emphasis Guidance, Keywords
  - Cautions, Grounding Notes
- Updated format branching in `run_generate` to route `md`
- Updated format validation tuple to include `"md"`
- Updated log archive filename logic to use `.md` extension for Markdown reports

### `cli.py`
- Updated format validation in `_cmd_linkedin_generate` to accept `md`
- Updated help text for `--format` on content match and linkedin generate
- Updated help text for `--report-format` on content tailor

### Documentation
- `docs/content-match.md`: Added `md` to format option, added Markdown example
- `docs/content-tailor.md`: Added `md` to report-format option, added Markdown example
- `docs/content.md`: Updated format option values in tables

## Design Decisions

1. **Markdown renderers are local per module**: Each module has its own `render_markdown_report()` function placed alongside the existing text renderer, keeping section parity easy to maintain.

2. **Format naming preserved**: `content match` uses `text`/`md`/`json`, `content tailor` uses `text`/`md`/`json`, `linkedin generate` uses `txt`/`md`/`json`. No existing format names were changed.

3. **Logging adapted**: LinkedIn generate's log archive condition was updated from `format == "txt"` to `format in ("txt", "md")` to correctly save Markdown artifacts in logs.

## Verification

```bash
# All three commands accept 'md' format
./hirepaper-dev content match data/candidate.json data/vacancy.txt --format md
./hirepaper-dev content tailor data/candidate.json data/vacancy.txt --output /tmp/t.json --report-format md
./hirepaper-dev linkedin generate data/candidate.json --output /tmp/l.md --format md

# Backward compatibility preserved
./hirepaper-dev content match data/candidate.json data/vacancy.txt --format text
./hirepaper-dev content match data/candidate.json data/vacancy.txt --format json

# Bad formats correctly rejected
./hirepaper-dev content match data/candidate.json data/vacancy.txt --format yaml      # -> fail
./hirepaper-dev content tailor data/candidate.json data/vacancy.txt --report-format yaml  # -> fail
./hirepaper-dev linkedin generate data/candidate.json --output /tmp/l.md --format yaml    # -> fail

# Packaged binary
.venv/bin/python build.py
./hirepaper content match data/candidate.json data/vacancy.txt --format yaml  # -> fail
./hirepaper content tailor data/candidate.json data/vacancy.txt --report-format yaml  # -> fail
./hirepaper linkedin generate data/candidate.json --output /tmp/l.md --format yaml  # -> fail
```

Note: Full LLM-based rendering was not verified (no LLM endpoint configured). Format acceptance and routing were confirmed through validation logic tests.

## Residual Risks
- Markdown renderers cannot be visually verified without an LLM response. They follow the same structure as text renderers, so correctness depends on the underlying validated report data being well-formed.
- The `content match` Markdown renderer uses HTML entities (`&rarr;`) for arrows, which may not render in all Markdown viewers.
