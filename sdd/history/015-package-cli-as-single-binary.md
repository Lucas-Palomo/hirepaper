# 015 -- Package CLI as a single binary

**Date:** 2026-05-29
**Agent:** opencode (claude)

## Context
The CLI ran only from source with PYTHONPATH set. Distribution required cloning the repo and installing Python dependencies. Task 015 packages the tool as a standalone executable that can run anywhere without the source tree.

## Changes

### `src/curriculum_gen/_resources.py` (new)
- Provides `templates_dir()`, `locale_dir()`, `icons_dir()`, `logs_dir()` path resolution helpers.
- Detects PyInstaller bundle via `sys._MEIPASS` at runtime; falls back to source-tree paths (`Path(__file__).parent.parent.parent`) when running from source.

### `src/curriculum_gen/cli.py`
- Replaced module-level `_PROJECT_DIR`, `_TEMPLATES_DIR`, `_LOGS_DIR`, `_ASSETS_ICONS_DIR` constants with calls to the new `_resources` module functions.
- Removed unused `_CLS_PATH` constant.

### `src/curriculum_gen/generator.py`
- Replaced `Path(__file__).parent.parent.parent / "templates"` with `templates_dir()` from `_resources`.

### `src/curriculum_gen/locale.py`
- Replaced `Path(__file__).parent.parent.parent / "locale"` with `locale_dir()` from `_resources`.
- Removed unused `pathlib` import.

### `src/curriculum_gen/__main__.py`
- Changed `from .cli import app` (relative import) to `from curriculum_gen.cli import app` (absolute import) so PyInstaller can resolve the entry point correctly.

### `build.py` (new)
- PyInstaller build script producing a standalone executable.
- Bundles `templates/`, `assets/`, and `locale/` as data files.
- Writes artifact to `dist/curriculum-gen`.

### `pyproject.toml`
- Fixed build backend from `setuptools.backends._legacy:_Backend` (removed in newer setuptools) to `setuptools.build_meta`.

### `.gitignore`
- Added `dist/`, `build/`, `*.spec` entries.

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Documented command builds a single executable | Pass |
| 2 | Executable runs outside the source module import path | Pass |
| 3 | Executable can print `--help` | Pass |
| 4 | Executable can run `doctor` | Pass |
| 5 | Executable can generate a PDF from `data/candidate.json` | Pass |
| 6 | Executable can run `ats-check` on a generated PDF | Pass |
| 7 | Templates, locale files, and icon assets are available to packaged app | Pass |
| 8 | Source execution of `./curriculum-gen` continues to work | Pass |
| 9 | Documentation clearly lists external host dependencies | Pass |

## Verification

```bash
# Build
python3 build.py          # produces dist/curriculum-gen (~13 MB)

# Help
./dist/curriculum-gen --help
# → shows Usage, commands (generate, doctor, ats-check)

# Doctor
./dist/curriculum-gen doctor
# → All 8 checks pass, including real LuaLaTeX+fontspec compilation test

# Generate (from repo root)
./dist/curriculum-gen generate data/candidate.json -o output/packaged-resume.pdf --locale en
# → Generated: output/packaged-resume.pdf

# Generate (from different CWD, proving path independence)
mkdir -p /tmp/test && cd /tmp/test
/path/to/dist/curriculum-gen generate /path/to/data/candidate.json -o /tmp/test/res.pdf
# → Generated: /tmp/test/res.pdf

# ATS check
./dist/curriculum-gen ats-check output/packaged-resume.pdf
# → PASS (15 checks passed)

# Source execution still works
PYTHONPATH=src python3 -m curriculum_gen doctor
# or via the shell script:
./curriculum-gen doctor
```

## External dependencies (not bundled)
- **LuaLaTeX** (TeX Live) — PDF engine
- **luaotfload** (TeX Live) — font loading
- **rsvg-convert** (librsvg) — SVG icon conversion
- **pdftotext, pdffonts** (poppler-utils) — text/font extraction
- **exiftool** (perl-image-exiftool) — PDF metadata inspection
