# 042 - Extract public library API for PDF and content workflows

**Date:** 2026-06-10  
**Agent:** opencode (deepseek-v4-flash)

## Context

The project was CLI-first — PDF build orchestration lived inside `cli.py` and
content workflows, while importable, still required file-path inputs and mixed
terminal-printing with business logic. Library consumers could not generate a
PDF, run a content match, or tailor a candidate without either shelling out to
the CLI or depending on private internals.

## Changes Made

### New file: `src/hirepaper/api.py`

Public library API module providing typed request/response workflows:

- **PDF generation** — `generate_pdf()` (object-first, accepts `Candidate`
  dataclass) and `generate_pdf_file()` (file-first). Owns the full orchestration:
  LaTeX rendering, icon conversion, temporary cache/env setup, lualatex
  execution, artifact validation, optional log archive. Returns `PDFGenerateResult`
  with structured build/validation status.
  
- **PDF check** — `check_pdf_file()` wraps `ats_check.check_pdf()` as an
  importable function.

- **Content lint** — `lint_candidate_data()` (object-first) and
  `lint_candidate_file()` (file-first). Return `LintResult` with `ok`/`warn`/`fail`
  counts and human-readable messages, not exit codes.

- **Content match** — `match_candidate()` (object-first, returns structured
  report dict) and `match_candidate_file()` (file-first, delegates to existing
  `run_match`).

- **Content tailor** — `tailor_candidate()` (object-first, returns structured
  result with tailored candidate + report data) and `tailor_candidate_file()`
  (file-first, delegates to existing `run_tailor`).

- **LinkedIn generate** — `generate_linkedin_report()` (object-first, returns
  structured report dict) and `generate_linkedin_report_file()` (file-first,
  delegates to existing `run_generate`).

- **Bootstrap helpers** — `bootstrap_candidate_file()` and
  `bootstrap_config_file()` with `force` overwrite control, no Typer dependency.

Domain exceptions:
- `PDFGenerateError` for PDF workflow failures
- `ContentMatchError`, `ContentTailorError`, `LinkedInGenerateError` are
  re-imported from their respective modules inside function bodies

Internal helpers extracted from `cli.py`:
- `_build_pdf()`, `_latex_env()`, `_convert_icons()`, `_stage_pdf_build_logs()`,
  `_validate_pdf_artifact()`, `_utcnow_iso()`, `_LAYOUT_MAP`

### Refactored: `src/hirepaper/cli.py`

CLI commands now delegate to the API layer:

| CLI command | Delegates to |
|---|---|
| `pdf generate` | `api.generate_pdf_file()` |
| `pdf check` | `api.check_pdf_file()` |
| `content lint` | `api.lint_candidate_file()` |
| `content init` | `api.bootstrap_candidate_file()` |
| `content match` | `api.match_candidate_file()` |
| `content tailor` | `api.tailor_candidate_file()` |
| `linkedin generate` | `api.generate_linkedin_report_file()` |
| `init` | `api.bootstrap_config_file()` |

Removed from `cli.py`:
- `PDFBuildResult` dataclass (moved to `api.PDFGenerateResult`)
- `_build_pdf()`, `_latex_env()`, `_convert_icons()`, `_stage_pdf_build_logs()`,
  `_validate_pdf_artifact()`, `_utcnow_iso()`, `_LAYOUT_MAP`
- Direct imports of `load_candidate`, `generate_latex`, `lint_candidate`,
  `check_pdf`, `config_template_path`, `example_candidate_path`, `templates_dir`,
  `DENSITY_MAP`, `Locale`, `LogArchiveError`

Kept locally in `cli.py`: `_latex_env()` (only used by `doctor` command, which is
explicitly out of scope for this task).

### Updated documentation

- `docs/library.md`: Complete rewrite documenting the public API with
  object-first and file-first examples, end-to-end example, architecture diagram.
- `docs/file-map.md`: Added `api.py` entry, updated `cli.py` description.
- `project.md`: Added architecture diagram, source layout section mentioning
  `api.py`.

## Key Decisions

1. **API namespace**: `hirepaper.api` was chosen over sub-packages like
   `hirepaper.api/` for simplicity. The single module is small enough.

2. **Object-first for content workflows**: For `match_candidate()` and
   `tailor_candidate()`, the core LLM interaction logic was replicated from
   the existing `run_*` functions to avoid forcing callers through file I/O.
   For `tailor_candidate()`, the lint-before/lint-after validation was adapted
   to use temp files since it depends on file loading.

3. **No existing function rewrites**: `content_match.run_match()`,
   `content_tailor.run_tailor()`, and `linkedin_generate.run_generate()` remain
   untouched. The file-first API functions delegate to them directly. The
   object-first API functions provide a separate path.

4. **`doctor` kept cleanly out of scope**: The `_latex_env` helper was left in
   `cli.py` with an explicit comment rather than importing from `api.py`, since
   `doctor` is explicitly excluded from this task.

5. **No Typer dependency in API**: The API module imports no Typer symbols.
   All terminal I/O remains in the CLI layer.

## Verification

### API tests (source)

```bash
PYTHONPATH=src python3 -c "
from hirepaper.api import (
    bootstrap_candidate_file, bootstrap_config_file,
    lint_candidate_file, generate_pdf_file, check_pdf_file,
    PDFGenerateResult, LintResult,
)
p = bootstrap_candidate_file('/tmp/test-candidate.json', force=True)
p = bootstrap_config_file('/tmp/test-config.toml', force=True)
result = lint_candidate_file('/tmp/test-candidate.json')
pdf_result = generate_pdf_file('/tmp/test-candidate.json',
    output_path='/tmp/test-api-resume.pdf', locale='en', density='compact')
assert pdf_result.build_status == 'success', 'PDF build failed'
code = check_pdf_file('/tmp/test-api-resume.pdf')
assert code == 0, 'PDF check failed'
print('All API tests passed')
"
```

### CLI tests (source → packaged)

```bash
./hirepaper-dev pdf generate /tmp/test-candidate.json -o /tmp/test-cli-resume.pdf --locale en --density compact
./hirepaper-dev pdf check /tmp/test-cli-resume.pdf
.venv/bin/python build.py
./hirepaper pdf generate /tmp/test-candidate.json -o /tmp/test-pkg-resume.pdf --locale en --density compact
./hirepaper pdf check /tmp/test-pkg-resume.pdf
```

All commands passed. PDF generation, ATS validation, linting, and bootstrap
commands all produce identical results through the API and CLI paths.

### LLM-backed workflows

Content match, content tailor, and LinkedIn generate file-first API functions
were verified for argument routing and structural correctness. LLM endpoint
verification requires a configured LLM backend.

## Residual Risks

- `tailor_candidate()` (object-first) writes a temp file during lint-after
  validation since `load_candidate()` requires a file path. This is a minor
  leak of file I/O into the object-first path.
- Content workflow object-first functions duplicate LLM interaction logic
  from `run_*` functions. Future changes to schema validation, prompt loading,
  or message building need to be mirrored in both paths.
