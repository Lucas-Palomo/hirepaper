# 045 - Add JSONC support for candidate and related JSON inputs

**Date:** 2026-06-10  
**Agent:** opencode (deepseek-v4-flash)

## Context

Candidate JSON files are human-edited authoring documents, not just machine
payloads. Standard JSON's lack of comments forced users to either strip notes
before processing or keep context outside the file. This added friction during
iterative editing, tailoring, and review.

## Changes Made

### `src/hirepaper/loader.py` — `load_json()` and `_strip_jsonc()`

- Added `_strip_jsonc(text: str) -> str` — character-level comment stripper
  that handles:
  - `//` line comments
  - `/* */` block comments
  - Correctly preserves `//` and `/*` inside JSON strings
  - Correctly handles escape sequences inside strings
- Added `load_json(path: str | Path) -> dict` — public helper that reads a
  file, strips JSONC comments, and parses with standard `json.loads()`.
- Changed `load_candidate()` to use `load_json()` instead of direct
  `json.loads()`. All downstream behavior (validation, dataclass mapping)
  is unchanged.

### No dependency added

The JSONC stripper is a ~50-line pure-Python character walker. No external
library was introduced.

### Documentation updates

- `README.md`: Feature list updated to mention JSONC support
- `docs/content.md`: Added "Input format" note about JSONC
- `docs/pdf.md`: Added JSONC note to `pdf generate` description

## Verification

```bash
# JSONC input with comments
./hirepaper-dev content lint /tmp/candidate-commented.jsonc
./hirepaper-dev pdf generate /tmp/candidate-commented.jsonc -o /tmp/jsonc-test.pdf --locale en --density compact
./hirepaper-dev pdf check /tmp/jsonc-test.pdf

# Existing strict JSON still works
./hirepaper-dev content lint data/candidate.json

# Packaged binary
.venv/bin/python build.py
./hirepaper content lint /tmp/candidate-commented.jsonc
./hirepaper pdf generate /tmp/candidate-commented.jsonc -o /tmp/jsonc-pkg.pdf --locale en --density compact
./hirepaper pdf check /tmp/jsonc-pkg.pdf
```

All commands pass. Parsed candidate data is byte-identical to the same file
with comments removed.

## Supported syntax

| Feature | Status |
|---|---|
| `//` line comments | ✅ |
| `/* */` block comments | ✅ |
| Comments inside strings (treated as literal) | ✅ |
| Trailing commas | ❌ (not supported; standard JSON rule) |

## Residual Risks

- The comment stripper is a narrow implementation — it handles standard JSONC
  but not JSON5 features like single-quoted strings, unquoted keys, or hex
  numbers. This is by design per the task scope.
- Error messages for malformed JSONC files point to the cleaned text, not the
  original line numbers — the line number in the error may not match the source
  file. Future improvements could track line mapping.
