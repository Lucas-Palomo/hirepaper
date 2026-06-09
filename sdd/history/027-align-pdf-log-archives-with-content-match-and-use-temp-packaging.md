# 027 - Align `pdf generate` log archives with `content match` and use temporary packaging

**Date:** 2026-06-06
**Agent:** Codex GPT-5

---

## Context

`content match` already persisted logs as a ZIP archive through `--log <path>`,
but `pdf generate` still exposed `--log` as a boolean switch and wrote loose
diagnostic files into a repository-level `logs/` directory.

That behavior created three concrete problems:

- inconsistent CLI contract between two user-facing commands;
- persisted runtime diagnostics depended on a project-relative writable path;
- log persistence did not use a temporary staging lifecycle before archive
  creation.

The task was to align `pdf generate` with the `content match` log contract and
move persisted logging to a shared temporary staging + final ZIP packaging
model.

## Changes

### Added: `src/curriculum_gen/log_archive.py`

- Introduced `StagedLogArchive` as a shared helper for persisted logs.
- The helper:
  - creates a per-run temporary staging directory with `tempfile`;
  - writes staged files as normal files;
  - packages the staged contents into the requested ZIP destination;
  - cleans the temporary directory on exit;
  - raises `LogArchiveError` on staging/finalization failures.

### Modified: `src/curriculum_gen/cli.py`

- Changed `pdf generate --log` from a boolean flag to `--log <path>`.
- Updated help text to state that persisted logs are written as a ZIP archive
  and may contain sensitive candidate/build data.
- Added `PDFBuildResult` to make build outcome and artifact-validation outcome
  explicit.
- Reworked PDF log persistence so the command:
  - stages `candidate.json`, `resume.tex`, effective class file, generated icon
    PDFs, `resume.*`, and engine stdout/stderr in a temporary directory;
  - writes a structured `meta.json`;
  - packages the final ZIP archive to the user-provided destination;
  - removes staging residues automatically.
- Aligned runtime messaging with `content match` by printing:
  - `Generated: <pdf>`
  - `Log archive saved: <path>`
  - a sensitivity warning
- On failed generation or failed artifact validation, the command now still
  saves the requested archive before exiting, as long as archive creation
  succeeds.

### Modified: `src/curriculum_gen/content_match.py`

- Replaced direct `ZipFile.writestr(...)` archive creation with the shared
  `StagedLogArchive` lifecycle.
- Kept the public `--log <path>` behavior unchanged while aligning internal
  staging and cleanup behavior with `pdf generate`.

### Modified: `src/curriculum_gen/_resources.py`

- Removed the now-unused `logs_dir()` helper because persisted runtime logs no
  longer target a repository-relative `logs/` directory.

### Modified: `project.md`

- Updated the command surface and PDF-generation notes to reflect
  `pdf generate --log <archive.zip>`.
- Documented that persisted PDF logs are staged in a temporary directory and
  then packaged into a ZIP archive at the requested destination.

## Decisions and Tradeoffs

- **One log contract per concept:** `--log` now consistently means
  `--log <path>` for persisted archives rather than a command-specific mix of
  boolean/log-directory behavior.
- **Temporary staging instead of direct final writes:** this keeps operational
  residues out of the repository tree and behaves better for packaged
  execution.
- **Shared helper over duplicated ZIP logic:** `content match` and
  `pdf generate` now use the same lifecycle for archive staging/finalization,
  reducing drift.
- **Keep PDF log contents file-oriented:** for PDF generation, normal files such
  as `resume.tex`, `resume.log`, and engine logs are easier to inspect after
  extraction than trying to encode everything into synthetic JSON-only payloads.
- **No migration cleanup of pre-existing `logs/`:** the repository may still
  contain old loose logs from previous runs. The task removed the active code
  path, but it did not delete historical artifacts from the workspace.

## Verification

```bash
python3 -m py_compile src/curriculum_gen/*.py src/curriculum_gen/llm/*.py
./curriculum-gen-dev pdf generate --help
./curriculum-gen-dev content match --help
./curriculum-gen-dev pdf generate data/candidate.json -o output/resume.pdf --density compact --locale en --log output/pdf-generate-log.zip
./curriculum-gen-dev pdf check output/resume.pdf
.venv/bin/python build.py
./curriculum-gen pdf generate data/candidate.json -o output/resume-packaged.pdf --density compact --locale en --log output/pdf-generate-packaged-log.zip
./curriculum-gen pdf check output/resume-packaged.pdf
PYTHONPATH=src python3 - <<'PY'
import zipfile
from curriculum_gen.content_match import save_log_zip

save_log_zip(
    log_path='output/content-match-log-smoke.zip',
    meta={'command': 'smoke', 'timestamp_utc': '2026-06-06T00:00:00Z'},
    result_schema={'$id': 'smoke-schema'},
    prompt_text='prompt',
    candidate_payload={'personal': {'name': 'Smoke'}},
    vacancy_text='vacancy',
    raw_response='{"score": 100}',
    validated_result={'score': 100},
    usage={'prompt_tokens': 1, 'completion_tokens': 1},
)

with zipfile.ZipFile('output/content-match-log-smoke.zip') as zf:
    print('\n'.join(i.filename for i in zf.infolist()))
PY
```

### Results

- `py_compile` passed.
- `pdf generate --help` now shows `--log TEXT` with ZIP-archive wording.
- `content match --help` remains `--log <path>` and keeps ZIP wording.
- Source-based PDF generation succeeded and saved `output/pdf-generate-log.zip`.
- `./curriculum-gen-dev pdf check output/resume.pdf` returned `PASS (15 checks passed)`.
- PyInstaller build succeeded. During build, PyInstaller emitted a warning about
  Pydantic v1 compatibility on Python 3.14+, but the build completed.
- Packaged PDF generation succeeded and saved
  `output/pdf-generate-packaged-log.zip`.
- `./curriculum-gen pdf check output/resume-packaged.pdf` returned
  `PASS (15 checks passed)`.
- ZIP inspection confirmed the PDF archives contain:
  - `candidate.json`
  - `resume.tex`
  - `standard.cls`
  - generated icon PDFs
  - `resume.aux`
  - `resume.log`
  - `resume.out`
  - `resume.pdf`
  - `engine-stdout.log`
  - `engine-stderr.log`
  - `meta.json`
- Direct smoke invocation of `save_log_zip()` confirmed that `content match`
  now also stages and packages its archive members successfully through the
  shared helper.

## Residual Risks

- The project still contains a pre-existing `logs/` directory from older runs.
  The runtime path is no longer used for new persisted archives, but the task
  did not delete historical workspace artifacts.
- `content match` archive validation was exercised through a focused helper
  smoke test rather than a live LLM run.
- The command string stored in PDF `meta.json` is intentionally simple and does
  not shell-quote paths with spaces.
