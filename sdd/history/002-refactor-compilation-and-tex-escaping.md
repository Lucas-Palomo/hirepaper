# 002 — Refactor compilation validation and TeX escaping

**Date:** 2026-05-27
**Agent:** opencode (deepseek-v4-flash)

---

## Context

Task `001` established the first working pipeline. Two implementation risks remained:

1. **Compilation success detection** checked only `returncode != 0 or not pdf_path.exists()`, which is logically flawed — a stale PDF from a previous run would cause a false success even if the current compilation failed.
2. **TeX escaping** covered `& % $ # _ { }` but missed `\`, `~`, and `^`, which are all special characters in LaTeX and may appear in real resume data.

## Changes

### 1. Compilation validation (`generate.py`)

**Before:**
```python
if result.returncode != 0 or not pdf_path.exists():
```

This used `or`: if the PDF existed (even from a prior run), the check passed regardless of the return code.

**After:**
- Stale artifacts (`.pdf`, `.aux`, `.log`, `.out`) are removed before compilation.
- Success requires `returncode == 0 AND pdf exists AND size > 0`.

```python
for f in [pdf_path, aux_path, log_path, out_path]:
    f.unlink(missing_ok=True)

if result.returncode == 0 and pdf_path.exists() and pdf_path.stat().st_size > 0:
    return 0
```

This makes success detection tie directly to the current run: no PDF before compile means no false positive from a stale file.

### 2. TeX escaping (`src/generator.py`)

**Before:** 7 characters handled.
**After:** 10 characters handled. `{` and `}` are escaped **first** (so the braces in
command strings like `\textbackslash{}` are not double-escaped), then `\`, `~`, `^`,
followed by `& % $ # _`.

| Character | Escaped form |
|-----------|-------------|
| `\`       | `\textbackslash{}` |
| `~`       | `\textasciitilde{}` |
| `^`       | `\textasciicircum{}` |
| `&`       | `\&` |
| `%`       | `\%` |
| `$`       | `\$` |
| `#`       | `\#` |
| `_`       | `\_` |
| `{`       | `\{` |
| `}`       | `\}` |

Brace escaping must precede `\`, `~`, `^` escaping so that the `{}` characters
inside `\textbackslash{}`, `\textasciitilde{}`, `\textasciicircum{}` are not
themselves escaped. If braces were replaced after these commands, the result
would be `\textbackslash\{\}` instead of `\textbackslash{}`.

### 3. Cleanup

Removed unused `from string import Template` import from `generator.py`.

## Verified Behavior

```
$ python generate.py --input data/candidate.json --output output/resume
Generated: output/resume.tex
Generated: output/resume.pdf
```

Pipeline generates correctly. Escaped characters compile without LaTeX errors.
Stale artifact removal verified by confirming output directory is clean before each run.
