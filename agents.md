# Agent Instructions

## Role
You are working on `hirepaper`, an existing Python CLI that generates an
ATS-safe resume PDF from structured JSON input.

Act as a pragmatic software engineer maintaining a real codebase. Read the
current implementation before making assumptions, keep changes scoped to the
task, and preserve working behavior unless the task explicitly changes it.

## Mission
Improve and maintain a deterministic resume generation pipeline:

```text
JSON -> LaTeX -> PDF -> ATS validation
```

The generated resume must:
- be factually grounded in the input JSON;
- remain machine-readable by ATS parsers;
- remain readable and professional for humans;
- avoid invented, exaggerated, or unsupported content;
- preserve visible contact information, URLs, sections, dates, metrics, and
  technical keywords.

## Required Workflow
For every task:

1. Read the relevant backlog item in `sdd/backlog/`.
2. Inspect the current code and templates before editing.
3. Implement the smallest coherent change that satisfies the task.
4. Run a focused test derived from the task scope.
5. Build the packaged binary after the task is implemented.
6. Run a small smoke test against the relevant entry point.
7. Document the completed work and development decisions in `sdd/history/`.

Do not mark a task complete only because code was changed. A task is complete
when the implementation, build, smoke test, and history entry are all done.

## Entry Points
The project has two root-level entry points:

- `./hirepaper-dev`: source-based development entry point. Use this while
  implementing and testing code changes before packaging.
- `./hirepaper`: packaged binary entry point. It delegates to
  `dist/hirepaper` and is the artifact users are expected to run after a
  build.

After each task execution, rebuild the binary and verify the behavior relevant
to the task through the appropriate entry point.

Typical commands:

```bash
./hirepaper-dev --help
./hirepaper-dev doctor
./hirepaper-dev content init --output /tmp/hirepaper-candidate-init.json
./hirepaper-dev content lint /tmp/hirepaper-candidate-init.json
./hirepaper-dev linkedin --help
./hirepaper-dev linkedin help
./hirepaper-dev linkedin generate data/candidate.json -o /tmp/linkedin-report.txt --format txt
./hirepaper-dev linkedin generate data/candidate.json -o /tmp/linkedin-report.json --format json
./hirepaper-dev pdf generate data/candidate.json -o output/dev-resume.pdf --density compact --locale en
./hirepaper-dev pdf check output/dev-resume.pdf
./hirepaper-dev content lint data/candidate.json

.venv/bin/python build.py

./hirepaper --help
./hirepaper doctor
./hirepaper content init --output /tmp/hirepaper-candidate-init.json --force
./hirepaper content lint /tmp/hirepaper-candidate-init.json
./hirepaper linkedin --help
./hirepaper linkedin help
./hirepaper linkedin generate data/candidate.json -o /tmp/linkedin-report-packaged.txt --format txt
./hirepaper linkedin generate data/candidate.json -o /tmp/linkedin-report-packaged.json --format json
./hirepaper pdf generate data/candidate.json -o output/packaged-resume.pdf --density compact --locale en
./hirepaper pdf check output/packaged-resume.pdf
./hirepaper content lint data/candidate.json
```

If environment restrictions prevent a command from running, document the exact
failure and what was not verified.

## LLM Config Policy

LLM-oriented commands resolve configuration in this order:

1. CLI flag override such as `--timeout-seconds` / `--max-tokens`
2. `--config <path>` TOML file, or `./config.toml` when present
3. environment variables
4. command fallback for `content match` / `content tailor`
5. built-in global defaults

Do not assume `--config` is mandatory. The CLI must work from environment
variables alone when no `config.toml` is present.

Use `hirepaper init` to bootstrap a local `config.toml`.
The bundled template lives at `assets/examples/config.example.toml`.

Environment variables currently supported:
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_TEMPERATURE`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_TOKENS`
- `LLM_CONTENT_MATCH_TIMEOUT_SECONDS`
- `LLM_CONTENT_MATCH_MAX_TOKENS`
- `LLM_CONTENT_TAILOR_TIMEOUT_SECONDS`
- `LLM_CONTENT_TAILOR_MAX_TOKENS`
- `LLM_LINKEDIN_GENERATE_TIMEOUT_SECONDS`
- `LLM_LINKEDIN_GENERATE_MAX_TOKENS`

## Engineering Rules
- Keep the data model explicit and deterministic.
- Keep content generation separate from presentation/layout rules.
- Prefer structured parsing and rendering over ad hoc string manipulation.
- Preserve source execution and packaged binary execution.
- Keep templates reusable and layout-specific behavior isolated where practical.
- Fail clearly on invalid input, broken PDF generation, missing external tools,
  or ATS-unsafe artifacts.
- Do not add dependencies unless they materially improve correctness,
  maintainability, or packaging.
- Do not rewrite stable code without a task-driven reason.

## Resume Content Rules
- Do not invent experience, skills, achievements, certifications, dates, links,
  or metrics.
- Do not distort candidate data to make the resume look stronger.
- Prefer measurable, specific bullets only when supported by source data.
- Keep optional sections density-aware.
- Treat ATS safety as the first-order constraint and visual polish as the
  second-order constraint.

## Validation Expectations
Use validation proportional to the task. For generation, layout, density,
metadata, or packaging changes, at minimum verify:

```bash
./hirepaper-dev pdf generate data/candidate.json -o output/resume.pdf --density compact --locale en
./hirepaper-dev pdf check output/resume.pdf
.venv/bin/python build.py
./hirepaper pdf generate data/candidate.json -o output/resume-packaged.pdf --density compact --locale en
./hirepaper pdf check output/resume-packaged.pdf
```

For layout or density changes, also test both densities:

```bash
./hirepaper-dev pdf generate data/candidate.json -o output/compact-standard.pdf --density compact --locale en
./hirepaper-dev pdf generate data/candidate.json -o output/full-standard.pdf --density full --locale en
```

Run `pdf check` on every generated PDF that is part of the task verification.

For layout or density changes, visual inspection is also required. Render the
generated PDFs to image files and inspect the pages for:
- overflow or overlapping text;
- broken spacing or hierarchy;
- awkward page breaks;
- nearly empty final pages;
- crowded headers;
- obvious regressions between layouts or densities.

Suggested command:

```bash
pdftoppm -png output/compact-inline.pdf output/compact-inline
```

Use image rendering as a complement to `pdf check`, `pdftotext`, `pdffonts`,
and metadata checks.

## Documentation Requirements
When a task is completed, create or update the corresponding file in
`sdd/history/`.

The history entry should include:
- date;
- agent/model if known;
- context;
- changes made;
- relevant decisions and tradeoffs;
- verification commands and results;
- any residual risks or follow-up items.

Keep backlog files in `sdd/backlog/` as the source of pending task intent.
History files should record what was actually done.

## Project Context
Technical project details live in [project.md](project.md). Read it when touching:
- generation pipeline;
- templates or layout;
- density policies;
- PDF/ATS validation;
- binary packaging;
- runtime resource paths.

For the project file map and important paths, see [docs/file-map.md](docs/file-map.md).
