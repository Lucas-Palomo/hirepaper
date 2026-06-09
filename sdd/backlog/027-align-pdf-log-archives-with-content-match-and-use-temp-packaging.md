# 027 - Align `pdf generate` log archives with `content match` and use temporary packaging

## Status
Completed

## Context
The project currently has two different log persistence behaviors:

- `curriculum-gen content match ... --log <path>` writes a ZIP archive to an
  explicit destination path.
- `curriculum-gen pdf generate ... --log` is only a boolean flag and writes
  loose files into a repository-level `logs/` directory.

This split creates drift in command UX, makes packaged-binary behavior less
predictable, and keeps `pdf generate` tied to a writable project-relative logs
path that may not be appropriate when running from the PyInstaller bundle.

The current `pdf generate` implementation also writes log artifacts directly to
their final persistence location. That is workable for a loose `logs/`
directory, but it is the wrong lifecycle for an archive-oriented logging model.

The project should move to a consistent archive-first logging contract where:

1. commands that persist logs accept `--log <path>`;
2. logs are assembled in a temporary working directory for the current run;
3. the temporary directory is archived into a ZIP file at the user-requested
   destination;
4. temporary logging residues are removed after the archive is created;
5. partial loose logging outside the archive is not treated as a completed log
   persistence flow.

This change should also harden packaged execution because runtime log writes
must no longer depend on repository-relative `logs/` paths or PyInstaller
resource locations.

## Goal
Unify persisted logging behavior for generation and matching workflows so that
the project uses temporary log staging plus ZIP packaging for persisted logs.

The final system must:

- make `pdf generate` use the same `--log <path>` contract shape already used
  by `content match`;
- stage log artifacts in a temporary directory instead of the project tree;
- package persisted logs as a ZIP archive at the original user-specified path;
- clean up temporary artifacts after packaging;
- avoid leaving operational log residues behind on successful or failed runs;
- keep runtime diagnostics clear when archive creation fails.

## Scope
This task may update:

- `src/curriculum_gen/cli.py`
- `src/curriculum_gen/content_match.py`
- `src/curriculum_gen/_resources.py`
- `project.md`
- `agents.md` if execution guidance needs clarification
- `sdd/history/`

This task may add:

- a shared helper module for staged log collection and ZIP packaging;
- PDF-generation log metadata files;
- helper utilities for temporary directory lifecycle management.

This task should not:

- change the PDF generation engine;
- redesign ATS validation behavior unrelated to logging;
- introduce persistent repository-relative log directories as the primary
  archive destination contract;
- keep dual behavior where one command writes ZIP archives and another writes
  loose files for the same `--log` concept.

## Problem Statement

### 1. `pdf generate` has a different `--log` contract
`pdf generate` currently exposes `--log` as a boolean switch rather than an
explicit destination path. This differs from `content match`, which already
uses `--log <path>` and reports a saved archive path.

Required change:

- `curriculum-gen pdf generate` must accept `--log <path>`;
- help text must explicitly say that the output is a ZIP archive;
- runtime messaging must report the saved archive path in the same style as
  `content match`;
- failures must mention archive creation/persistence problems clearly.

### 2. `pdf generate` writes loose files to a project-relative logs directory
The current implementation writes `resume.*`, `engine-stdout.log`, and
`engine-stderr.log` directly to `logs/`. This is inconsistent with the desired
artifact model and can be wrong for packaged execution because runtime writes
should not depend on resource-root behavior.

Required change:

- persisted logs must no longer rely on `logs/` as the final output location;
- runtime staging must use a temporary directory created for the current run;
- the temporary staging directory must be removed after archive packaging;
- the final persisted artifact must be the ZIP file only.

### 3. Log packaging behavior should be shared
The project already has ZIP persistence logic in `content match`, but it writes
archive members directly through `ZipFile.writestr(...)` to the destination
archive path. That works, but the project-level contract requested for this task
is stronger: use a temporary staging directory first, then package and clean it.

Required change:

- shared log packaging behavior should support:
  - create temporary staging directory;
  - write log members as normal files in that directory;
  - package the directory contents into the target ZIP path;
  - delete the staging directory afterward;
- `content match` should be updated to use the same staging/packaging lifecycle;
- the implementation may keep command-specific file contents, but the staging
  and packaging mechanism should be consistent.

## Command Surface

### `pdf generate`
Current contract:

```bash
curriculum-gen pdf generate <candidate.json> --output <pdf> --log
```

Target contract:

```bash
curriculum-gen pdf generate <candidate.json> --output <pdf> --log <path>
```

#### Required behavior
- `--log` is optional.
- When omitted, no persisted log archive is created.
- When provided, the command must create a ZIP archive at the given path.
- The archive path may be outside `output/`; it is chosen by the user.
- The help text must explain:
  - the value is a path;
  - the persisted format is ZIP;
  - the archive may contain source candidate data, LaTeX, and compiler logs.

#### Runtime messaging
On success with `--log`:

- normal generation output still reports the PDF path;
- the command must also report:
  - `Log archive saved: <path>`
- the warning style should be aligned with `content match`, adapted for PDF
  generation data sensitivity.

On failure with `--log`:

- if generation fails but a log archive is requested, the command should still
  try to persist the staged diagnostics archive before surfacing the generation
  error, when enough artifacts exist to package;
- if archive persistence itself fails, that failure must be explicit;
- the command must not silently fall back to loose files.

### `content match`
The visible command shape remains:

```bash
curriculum-gen content match <candidate.json> <vacancy.txt> --log <path>
```

But its internal log persistence must be aligned with the shared temporary
staging + ZIP packaging contract.

## Archive Lifecycle Contract

### 1. Temporary staging directory
When `--log <path>` is provided, the command must:

1. create a dedicated temporary directory for this run;
2. write all intended log members into that directory as regular files;
3. preserve a stable internal file naming layout inside the archive;
4. package the directory contents into the final ZIP archive path;
5. delete the temporary directory after packaging completes or fails.

The temporary directory must not be created under the repository root unless the
system temporary directory resolves there naturally. Prefer `tempfile`.

### 2. Final archive write
The target ZIP file must be written to the exact user-provided `--log` path.

Required behavior:

- create parent directories of the ZIP path when needed;
- overwrite the destination file if it already exists;
- fail clearly if the destination parent cannot be created or written;
- do not leave a partially assembled loose directory beside the destination ZIP.

### 3. Cleanup
After packaging:

- all staged files must be removed with the temporary directory;
- there must be no residual temporary log directories from successful runs;
- there must be no project-root logging residues created solely for this task.

If packaging fails:

- best-effort cleanup must still run;
- the command must fail non-zero;
- the error must say that log archive creation failed.

## Required PDF Log Contents
When `curriculum-gen pdf generate ... --log <path>` is used, the ZIP archive
must contain enough information to diagnose both successful and failed runs.

Minimum required members:

- `meta.json`
- `resume.tex`
- `<layout>.cls` or equivalent effective class file used for the run
- generated icon PDFs that were staged for compilation, if they were created
- `resume.log` when produced by LuaLaTeX
- `resume.aux` when produced by LuaLaTeX
- `engine-stdout.log`
- `engine-stderr.log`

If a PDF artifact was produced during the build directory phase:

- include `resume.pdf` from the build directory in the archive even if the final
  command fails validation.

### `meta.json` for PDF logs
The PDF log archive must include a structured `meta.json` at minimum with:

- `command`
- `timestamp_utc`
- `input_path`
- `output_path`
- `log_path`
- `locale`
- `density`
- `layout`
- `engine`
- `log_archive_format` with value `zip`
- `build_status`
- `artifact_validation_status`

Recommended additional fields:

- `artifacts_included`
- `candidate_name` if cheaply available from already-loaded data
- `packaged_execution` boolean inferred from runtime mode when practical

### PDF status semantics
Suggested values:

- `build_status`: `success` | `failed`
- `artifact_validation_status`: `passed` | `failed` | `not_run`

Exact enum text may vary, but the values must be stable and documented in code.

## Required Content Match Log Contents
`content match` should preserve its current useful artifacts, but they should be
written first into the temporary staging directory and then archived.

Minimum expected members remain:

- `meta.json`
- `result-schema.json`
- `prompt.txt`
- `candidate-payload.json`
- `vacancy.txt`
- `raw-response.json`
- `validated-result.json` when validation succeeds
- `usage.json` when usage metadata is available

## Error Handling

### `pdf generate`
The command must fail clearly when:

- input JSON is missing or invalid;
- output PDF path cannot be written;
- LaTeX compilation fails;
- the produced PDF fails artifact validation;
- the requested log archive path cannot be written;
- the archive cannot be created from staged files.

Important rule:

- if `--log` was explicitly requested, the implementation must treat archive
  persistence as part of task completion for that run;
- it must not silently downgrade to ephemeral logs after the user requested a
  persisted archive.

### `content match`
The command must keep its current clear failures for:

- invalid candidate or vacancy input;
- lint failure aborting the match;
- LLM request failure;
- invalid LLM JSON/schema output;
- output path write failure;
- log archive creation failure.

## Documentation Alignment
Update technical docs so they reflect the new contract.

At minimum:

- `project.md` should describe `pdf generate --log <path>` as a ZIP archive
  output rather than loose logs;
- any CLI or workflow guidance that still implies a repository `logs/`
  directory as the main persistence destination should be revised or clarified;
- `agents.md` examples should use the current command shape when relevant.

## Verification Requirements

Minimum verification for the task:

```bash
./curriculum-gen-dev pdf generate --help
./curriculum-gen-dev content match --help
./curriculum-gen-dev pdf generate data/candidate.json -o output/resume.pdf --density compact --locale en --log output/pdf-generate-log.zip
./curriculum-gen-dev pdf check output/resume.pdf
.venv/bin/python build.py
./curriculum-gen pdf generate data/candidate.json -o output/resume-packaged.pdf --density compact --locale en --log output/pdf-generate-packaged-log.zip
./curriculum-gen pdf check output/resume-packaged.pdf
```

Additional focused verification:

```bash
# Confirm ZIP members exist and no loose project-root log directory is required
unzip -l output/pdf-generate-log.zip
unzip -l output/pdf-generate-packaged-log.zip
```

For `content match`, verification may be performed with a focused unit-style
check if no live LLM environment is available, but the staged ZIP packaging path
must still be exercised in code.

## Acceptance Criteria
1. `pdf generate` changes from `--log` boolean to `--log <path>`.
2. `pdf generate --help` clearly states that `--log` writes a ZIP archive.
3. `content match` and `pdf generate` both persist logs through temporary
   staging directories plus ZIP packaging.
4. Persisted log archives are written to the exact user-provided destination.
5. Temporary log staging directories are cleaned up after packaging.
6. The implementation no longer depends on a repository-relative `logs/`
   directory for persisted runtime diagnostics.
7. `pdf generate` archives include structured metadata plus compiler/build
   diagnostics sufficient for post-failure debugging.
8. When `--log` is requested and archive creation fails, the command exits
   non-zero with a clear error.
9. Source execution and packaged binary execution both preserve the new logging
   behavior.
10. The completed work is documented in `sdd/history/027-...`.
