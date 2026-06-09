# 005 — Refactor Python package structure and entrypoints

**Date:** 2026-05-27
**Agent:** opencode (deepseek-v4-flash)

---

## Context

The project used `src/` as both the source root AND the package namespace
(e.g., `src.cli:app`, `python -m src`). This is poor practice for a packaged
Python application. Additionally, `generate.py` at the repository root was a
competing entrypoint inconsistent with the CLI direction.

## Changes

### 1. Real package under `src/`

All application code moved from `src/*.py` to `src/curriculum_gen/*.py`:

```
src/
  curriculum_gen/
    __init__.py
    __main__.py      ← python -m curriculum_gen
    cli.py           ← curriculum-gen CLI (typer)
    generator.py
    loader.py
    locale.py
    models.py
```

Imports now use the real package name: `curriculum_gen.cli:app`.

### 2. Path resolution updated

Since the package is one level deeper, all `parent.parent` references became
`parent.parent.parent`:

| File | Old path | New path |
|------|----------|----------|
| `generator.py` | `__file__.parent.parent / "templates"` | `parent.parent.parent` |
| `locale.py` | `__file__.parent.parent / "locale"` | `parent.parent.parent` |
| `cli.py` | `__file__.parent.parent` | `parent.parent.parent` |

### 3. `pyproject.toml` updated

- Entry point: `curriculum-gen = "curriculum_gen.cli:app"`
- Package discovery: `[tool.setuptools.packages.find]` with `where = ["src"]`

### 4. `generate.py` removed

The root-level `generate.py` was removed. The official entrypoints are now:
- `curriculum-gen ...` (installed CLI)
- `python -m curriculum_gen ...` (module execution)

### 5. Old artifacts cleaned

- `src/__init__.py` removed (no longer a package).
- `src/__pycache__/` removed.

## Acceptance Criteria Verification

| Criterion | Status |
|-----------|--------|
| Code under real package inside `src/` | ✓ `src/curriculum_gen/` |
| `src` no longer the package namespace | ✓ |
| `pyproject.toml` points to real package | ✓ `curriculum_gen.cli:app` |
| `python -m curriculum_gen` works | ✓ |
| CLI still works after refactor | ✓ generate, doctor, --help |
| `generate.py` removed | ✓ |
| Imports and paths work | ✓ |

### 6. Root-level entry point script

Added `curriculum-gen` (executable shell script) at the project root that:
- auto-discovers the project directory from its own location;
- sets `PYTHONPATH` to include `src/`;
- prefers the venv Python (where `typer` is installed);
- works from any working directory.

Usage: `./curriculum-gen generate --input ... --locale en --output ...`

## Post-refactor fix: Root entry point

After the refactor, `python -m curriculum_gen` only worked with `PYTHONPATH=src`
or when run from inside `src/`. Created `curriculum-gen` shell script at the
project root that auto-discovers the project directory, sets `PYTHONPATH`, and
prefers the venv Python (where `typer` is installed).

```bash
./curriculum-gen --help
./curriculum-gen doctor
./curriculum-gen generate --input data/candidate.json --locale en --output output/resume.pdf
```

Works from any working directory.
