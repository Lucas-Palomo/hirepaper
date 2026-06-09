# 006 — Polish CLI command behavior and UX

**Date:** 2026-05-27
**Agent:** opencode (deepseek-v4-flash)

---

## Context

The CLI existed but had rough edges: `--input` as a required flag, no short
flag aliases, `doctor` checking runtime paths it doesn't own, and no help
screen when `generate` was invoked without arguments.

## Changes

### 1. `generate` — positional INPUT argument

`--input` replaced with a positional argument. Accepts `Path`, validates
existence and readability.

```bash
./curriculum-gen generate data/candidate.json -o output/resume.pdf
```

### 2. Short flag aliases

- `--output` / `-o` — both accepted
- `--locale` / `-l` — both accepted

### 3. Help on missing arguments

When `generate` is invoked without required arguments (INPUT or `-o`), the
full `generate` help screen is displayed instead of a bare error.

### 4. `doctor` cleanup

Removed writability checks for `output/` and `logs/`. Those are runtime
concerns specific to `generate`. `doctor` now only checks:
- Python version (>=3.10)
- LaTeX engine availability (pdflatex, xelatex)
- example data presence (informational)

### 5. `generate` — runtime path validation

- Checks that INPUT exists and is readable.
- Checks that the output directory is writable.
- Checks locale exists before starting the build.
- Clear error messages for each failure case.

## Acceptance Criteria Verification

| Criterion | Status |
|-----------|--------|
| INPUT as positional argument | ✓ `generate <input>` |
| `-o` short form for `--output` | ✓ |
| `-l` short form for `--locale` | ✓ |
| `generate` with no args shows help | ✓ help screen displayed |
| `doctor` no longer checks runtime paths | ✓ removed |
| `generate` validates runtime paths | ✓ input exists, output writable |
| Help output is clear | ✓ root, generate, doctor |

```bash
./curriculum-gen generate                      # → help screen
./curriculum-gen generate data/candidate.json -o output/resume.pdf -l en
./curriculum-gen generate data/candidate.json -o output/curriculo.pdf -l pt-BR --log
./curriculum-gen doctor
```
