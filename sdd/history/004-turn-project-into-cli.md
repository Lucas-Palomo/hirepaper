# 004 — Turn the project into a CLI

**Date:** 2026-05-27
**Agent:** opencode (deepseek-v4-flash)

---

## Context

The pipeline existed as a plain Python script (`generate.py`). The project needed
a proper command-line interface with subcommands, help output, environment
diagnostics, and clean separation between final artifacts and build logs.

## Changes

### 1. CLI framework (`typer`)

Added `typer` as a dependency. Created `src/cli.py` with a Typer app exposing
two commands:

**`generate`** — Primary resume generation command.
- `--input` (required): path to candidate JSON.
- `--locale` (default: `en`): output locale (`en`, `pt-BR`).
- `--output` (required): path for the generated PDF.
- `--engine` (default: `pdflatex`): LaTeX engine.
- `--log` (flag): persist build artifacts to `logs/`.

**`doctor`** — Environment diagnostics.
- Checks Python version (>=3.10).
- Checks LaTeX availability (`pdflatex`, `xelatex`).
- Checks write permissions for `output/` and `logs/`.
- Reports results clearly, exits non-zero on failures.

### 2. Compilation refactor

Replaced in-place compilation (writing `.tex`/`.cls` to `output/`) with a
`tempfile.TemporaryDirectory` build approach:

1. Write `.tex` and `.cls` to a temp directory.
2. Run `pdflatex` inside the temp dir.
3. On success: copy only `.pdf` to `output/`.
4. If `--log` is set: copy all build artifacts (`.tex`, `.log`, `.aux`,
   `.out`, `.cls`) to `logs/` before the temp dir is destroyed.
5. On failure with `--log`: also persist stderr/stdout logs.

This ensures `output/` contains only the final PDF, and build diagnostics are
kept out of the deliverable path.

### 3. Entry points

- `python -m src` — runs the CLI via `src/__main__.py`.
- `pyproject.toml` defines a `curriculum-gen` console_scripts entry point
  for installed usage.

### 4. Housekeeping

- `logs/` added to `.gitignore`.
- `requirements.txt` updated to include `typer`.

## Verified Behavior

```bash
$ python -m src doctor
== curriculum-gen doctor ==
[OK] Python 3.14.5
[OK] pdflatex: pdfTeX 3.14...
[OK] xelatex: XeTeX 3.14...
[OK] output is writable
[OK] logs is writable
[OK] example data: data/candidate.json

$ python -m src generate --input data/candidate.json --locale en --output output/resume.pdf
Generated: output/resume.pdf

$ python -m src generate --input data/candidate.json --locale pt-BR --output output/curriculo.pdf --log
Generated: output/curriculo.pdf
# logs/ contains resume.tex, resume.log, resume.aux, resume.out, resume.cls

$ python -m src --help
$ python -m src generate --help
$ python -m src doctor --help
```

`output/` contains only `.pdf`. No `.tex`, `.log`, `.aux` leak into the
deliverable path.
