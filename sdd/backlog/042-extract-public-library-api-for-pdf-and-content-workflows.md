# 042 - Extract public library API for PDF and content workflows

## Status
Completed

## Context
`hirepaper` is already a valid Python package and several internals are
importable today, but the real product surface is still CLI-first.

That creates an awkward mismatch:

- `load_candidate()`, `generate_latex()`, and `check_pdf()` are importable;
- the main user workflows still live behind Typer commands and `typer.Exit`;
- `pdf generate` orchestration is effectively CLI-only;
- content-oriented commands such as `content match`, `content tailor`, and
  `linkedin generate` expose reusable logic, but their public contract is not
  shaped as a stable library API;
- stdout/stderr rendering, file I/O, orchestration, and business logic are
  still mixed in ways that make embedding harder than it should be.

The new `docs/library.md` currently documents this limitation honestly:
library consumers can reuse parts of the pipeline, but the final PDF
generation path and several higher-level workflows are not yet first-class
library APIs.

This task exists to fix that product gap.

## Goal
Make the same high-value workflows currently available through the CLI usable
through a supported Python library API.

The required outcome is:

1. consumers can call PDF/content workflows through importable functions;
2. CLI commands become thin adapters over the same library layer;
3. file-path based usage remains supported, but core business logic no longer
   depends on Typer or terminal printing;
4. the library contract is documented as public and stable enough for normal
   application embedding.

## Why This Task Exists
The project is now useful beyond direct terminal use:

- web backends may want to generate resumes on demand;
- automation scripts may want to lint, tailor, and render without shelling out;
- tests would be more precise against structured return values than terminal
  output;
- future integrations should not need to depend on CLI parsing semantics.

Today, forcing library consumers to call the CLI for the most important flows
is the wrong abstraction boundary.

## Product Decision
The CLI remains an official interface, but it must stop being the only
first-class orchestration layer.

The intended architecture after this task:

```text
public library API -> shared workflow services -> formatters / renderers / file I/O
CLI commands -> thin adapter over public library API
```

The library API should be the authoritative execution layer.
The CLI should primarily:

- parse arguments;
- translate CLI options into typed library requests;
- render human-readable output;
- convert typed errors into exit codes.

It should not remain the place where core workflow orchestration only exists.

## Workflows In Scope
The following commands must gain supported library equivalents.

### Required
1. `hirepaper pdf generate`
2. `hirepaper content lint`
3. `hirepaper content match`
4. `hirepaper content tailor`
5. `hirepaper linkedin generate`

### Strongly Recommended in the same task
6. `hirepaper content init`
7. `hirepaper init`
8. `hirepaper pdf check`

These are recommended because they are simple file-oriented operations that fit
the same library boundary and would otherwise leave the public API oddly
incomplete.

### Explicitly Out of Scope
- `hirepaper doctor`
- `hirepaper llm health`
- `hirepaper llm usage`
- changing result semantics, ATS rules, density rules, prompts, or schemas
- redesigning the resume model itself

## Scope
This task may update:

- `src/hirepaper/cli.py`
- `src/hirepaper/generator.py`
- `src/hirepaper/ats_check.py`
- `src/hirepaper/content_lint.py`
- `src/hirepaper/content_match.py`
- `src/hirepaper/content_tailor.py`
- `src/hirepaper/linkedin_generate.py`
- `src/hirepaper/__init__.py`
- `README.md`
- `project.md`
- `docs/library.md`
- `docs/content.md`
- `docs/pdf.md`
- `docs/file-map.md`
- `agents.md` if verification guidance needs alignment
- `sdd/history/`

This task may add:

- a stable public API module such as `src/hirepaper/api.py` or
  `src/hirepaper/api/`
- typed request/response dataclasses for workflow execution
- formatter helpers separated from execution helpers
- shared file-writing helpers where duplication is real

This task should not:

- introduce a second competing orchestration layer with duplicated logic;
- preserve `print()`/`typer.Exit` as the only behavior contract for library use;
- make the CLI depend on undocumented private internals more than it already
  does.

## Design Requirements

### 1. Separate core execution from CLI rendering
Every in-scope workflow must be split conceptually into:

- input loading / normalization;
- workflow execution;
- output formatting / file writing;
- CLI presentation and exit handling.

The library path must stop at typed results and normal exceptions.
It must not:

- call `typer.echo`;
- raise `typer.Exit`;
- depend on terminal-only progress behavior as its return contract.

### 2. Provide a stable public import surface
The project needs one documented public surface for embedding.

Recommended direction:

```python
from hirepaper.api import (
    generate_pdf,
    check_pdf_file,
    lint_candidate_file,
    match_candidate_to_vacancy,
    tailor_candidate_to_vacancy,
    generate_linkedin_report,
    bootstrap_candidate_file,
    bootstrap_config_file,
)
```

The exact module path may differ only if there is a strong reason.
If a different public namespace is chosen, document it clearly.

### 3. Use typed request/response objects for non-trivial workflows
For workflows with multiple options, raw positional arguments become brittle.

Preferred pattern:

- request dataclass with explicit options;
- response dataclass with typed fields and artifacts;
- optional helpers for file writing and report rendering.

Examples:

- `PDFGenerateRequest` / `PDFGenerateResult`
- `ContentMatchRequest` / `ContentMatchResult`
- `ContentTailorRequest` / `ContentTailorResult`
- `LinkedInGenerateRequest` / `LinkedInGenerateResult`

This improves both readability and future compatibility.

### 4. Support both object-first and file-first integration
The codebase already has a structured `Candidate` dataclass model.
Library consumers should not be forced through path-only APIs.

Preferred contract:

- core workflow functions accept already-loaded domain objects and text where it
  makes sense;
- convenience wrappers accept file paths and perform file I/O;
- CLI uses the file-oriented wrappers.

Examples:

- object-first:
  - `generate_pdf(candidate: Candidate, ..., output_path=...)`
  - `lint_candidate_data(candidate: Candidate) -> LintResult`
  - `match_candidate(candidate: Candidate, vacancy_text: str, ...) -> ...`

- file-first wrappers:
  - `generate_pdf_file(candidate_path: Path | str, ...)`
  - `lint_candidate_file(candidate_path: Path | str) -> ...`

The final design does not need these exact names, but it should preserve both
usage modes.

### 5. Standardize error behavior
Public library functions should raise normal Python exceptions defined in the
package rather than terminating process flow.

Examples of valid public behavior:

- `ValueError` for clearly malformed caller inputs when appropriate;
- domain-specific exceptions such as `PDFGenerateError`,
  `ContentMatchError`, `ContentTailorError`, `LinkedInGenerateError`;
- file read/write and subprocess failures wrapped or translated with
  user-meaningful context.

The CLI should be responsible for mapping those exceptions to terminal messages
and exit codes.

### 6. Separate formatting from structured result production
Several current workflows blend:

- generating a structured result;
- formatting that result as `text`, `md`, or `json`;
- saving files;
- printing to the terminal.

The library contract should distinguish these concerns.

Required direction:

- workflow execution returns structured data first;
- formatting helpers convert structured data to `text` / `md` / `json`;
- file-writing helpers persist those renderings when requested.

For example, `content match` should not require a terminal format choice just to
obtain its structured result programmatically.

### 7. Extract PDF build orchestration out of the CLI
This is the central gap.

The orchestration currently inside `_cmd_generate()` / `_build_pdf()` should
move behind a supported library function.

The public library path for PDF generation must include:

- candidate loading or direct `Candidate` input;
- locale resolution;
- density/layout validation;
- LaTeX rendering;
- icon conversion;
- temporary cache/env setup;
- `lualatex` execution;
- artifact validation;
- optional log archive creation.

The CLI command should call that function instead of owning the orchestration.

### 8. Preserve existing user-visible CLI behavior
This task is a boundary refactor, not a product redesign.

Unless explicitly justified, the CLI should preserve:

- command names;
- flags and option meanings;
- output artifact shapes;
- exit code behavior;
- current validation and grounding rules.

## Required Public Contract

### A. PDF generation
The project must expose a supported library path equivalent to:

```bash
hirepaper pdf generate <candidate.json> --output <pdf> [options]
```

Minimum required capabilities:

- generate from `Candidate` object or candidate JSON path;
- choose `locale`, `density`, `layout`, and optional log archive path;
- return a typed result containing at least:
  - output path;
  - build status;
  - validation status;
  - diagnostic message when failed.

The existing `PDFBuildResult` is a starting point, but it is currently CLI-local
and too narrowly placed. It may be promoted or replaced.

### B. Content lint
The project must expose a supported library path equivalent to:

```bash
hirepaper content lint <candidate.json>
```

Required behavior:

- support `Candidate` object input and file path input;
- return structured lint counts and messages;
- retain a rendering helper for terminal output.

Returning only an exit code is insufficient for the public library API.

### C. Content match
The project must expose a supported library path equivalent to:

```bash
hirepaper content match <candidate.json> <vacancy.txt> [options]
```

Required behavior:

- accept `Candidate` object input plus raw vacancy text;
- return the validated structured result independent of terminal format;
- allow callers to render `text`, `md`, or `json` afterward;
- keep config resolution behavior compatible with the current CLI policy.

### D. Content tailor
The project must expose a supported library path equivalent to:

```bash
hirepaper content tailor <candidate.json> <vacancy.txt> --output <tailored.json> [options]
```

Required behavior:

- accept `Candidate` object input plus raw vacancy text;
- return the structured tailoring report and the tailored candidate data;
- allow writing the tailored candidate JSON and optional report via helpers;
- preserve current conservative/rewrite semantics.

### E. LinkedIn generate
The project must expose a supported library path equivalent to:

```bash
hirepaper linkedin generate <candidate.json> --output <report> --format txt|md|json
```

Required behavior:

- accept `Candidate` object input;
- return the validated structured report;
- allow rendering into `txt`, `md`, or `json`;
- keep file-output helpers separate from the core generation function.

### F. Bootstrap helpers
If `content init` and `hirepaper init` are included, they should expose simple
file helpers equivalent to:

- copy bundled example candidate JSON to a destination path;
- copy bundled config template to a destination path;
- support overwrite control without Typer dependencies.

## API Shape Guidance
The exact names may differ, but the public API should read like library code,
not CLI plumbing.

Prefer:

```python
result = generate_pdf_file(
    "data/candidate.json",
    output_path="output/resume.pdf",
    locale="en",
    density="compact",
)
```

or:

```python
candidate = load_candidate("data/candidate.json")
result = generate_pdf(
    candidate,
    output_path="output/resume.pdf",
    locale="en",
    density="compact",
)
```

Avoid forcing callers into contracts shaped like CLI wrappers, such as:

- `ctx` objects;
- Typer option defaults as the primary abstraction;
- functions whose only result is terminal text.

## Documentation Requirements
When this task is implemented, update documentation to reflect that the library
path is now first-class rather than partial.

Required docs to review:

- `docs/library.md`
- `README.md`
- `project.md`
- `docs/file-map.md`
- command docs where a workflow now clearly maps to a library API

The documentation should show at least one end-to-end Python example that
generates a PDF without shelling out to `hirepaper`.

## Acceptance Criteria
This task is complete only if all of the following are true:

1. `pdf generate` orchestration is callable through a supported importable API.
2. `content lint`, `content match`, `content tailor`, and `linkedin generate`
   are callable through a supported importable API.
3. CLI commands delegate to the shared library execution layer rather than
   duplicating orchestration.
4. Public library functions no longer depend on `typer.Exit` or terminal output
   as their only contract.
5. Structured results are returned for non-trivial workflows instead of only
   process-style exit codes.
6. Existing CLI behavior remains materially compatible.
7. Documentation clearly presents the new library API.

## Recommended Verification
The implementing agent should verify both library and CLI paths.

Suggested verification examples:

```bash
PYTHONPATH=src python3 - <<'PY'
from pathlib import Path

from hirepaper.api import generate_pdf_file, lint_candidate_file

lint_result = lint_candidate_file("data/candidate.json")
assert lint_result.fail == 0

pdf_result = generate_pdf_file(
    "data/candidate.json",
    output_path="output/library-resume.pdf",
    locale="en",
    density="compact",
)
assert pdf_result.exit_code == 0
assert Path("output/library-resume.pdf").exists()
PY

./hirepaper-dev pdf generate data/candidate.json -o output/cli-resume.pdf --locale en --density compact
./hirepaper-dev pdf check output/library-resume.pdf
./hirepaper-dev pdf check output/cli-resume.pdf
```

For LLM-backed workflows, verify at minimum:

- library function argument validation;
- structured result routing;
- format rendering helpers;
- CLI delegation to the same execution path.

If no LLM endpoint is configured, document exactly what was and was not
verified.

## Notes For The Implementing Agent
- Prefer extracting the current implementation into reusable services over
  rewriting the workflows from scratch.
- Avoid creating a fake “public API” that merely wraps private CLI functions
  without cleaning the boundary.
- Keep the public namespace small and coherent.
- Treat `docs/library.md` as a user contract, not as an aspirational sketch.
