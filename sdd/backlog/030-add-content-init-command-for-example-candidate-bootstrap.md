# 030 - Add `content init` command for example candidate bootstrap

## Status
Completed

## Context
The project already provides:

- a canonical candidate data model and loader;
- `content lint` for validating candidate JSON quality;
- a bundled candidate JSON Schema at `assets/schemas/candidate.schema.json`;
- example candidate fixtures under `data/`;
- a top-level `init` command for bootstrapping `config.toml`.

What is still missing is an explicit onboarding path for candidate content itself.

Today, a user who wants to start authoring resume content must discover the
example fixture manually, copy it by hand, and infer which file should become
their working `candidate.json`.

That is inconsistent with the current CLI direction, where bootstrap workflows
should be explicit and reproducible.

A dedicated `content init` command should make that path first-class.

## Goal
Add a `curriculum-gen content init` command that writes a starter candidate JSON
file for the user from the canonical example candidate asset.

The command should generate an editable example candidate structure derived from
this project’s canonical example candidate, so a user can start from a valid
shape instead of assembling JSON manually.

## Product Decision
In this task, `content init` should bootstrap a valid example candidate JSON
file, not dump the raw JSON Schema contract.

Rationale:

- end users need a working editable example more often than a JSON Schema file;
- the project already has `assets/schemas/candidate.schema.json` for machine
  validation and LLM contracts;
- an example candidate JSON is a better authoring starting point for the CLI’s
  core workflow.

If the project later needs a separate command to export the raw JSON Schema,
that should be handled by another backlog item rather than overloading this
command.

## Scope
This task may update:

- `src/curriculum_gen/cli.py`
- `src/curriculum_gen/_resources.py`
- `build.py` or packaging/resource inclusion if needed
- `project.md`
- `agents.md` only if command examples or execution guidance need to mention the
  new bootstrap path
- `sdd/history/`

This task may add:

- a canonical bundled example candidate asset path if the current location is
  not suitable for packaged runtime access
- helper functions for locating or copying the example candidate template
- focused command-level tests or verification fixtures if the repo already uses
  that pattern

This task should not:

- redesign the candidate JSON shape
- redesign `candidate.schema.json`
- add interactive question flows
- invent multiple starter templates
- silently overwrite existing files
- blur the distinction between a starter example and the validation schema

## Command Surface
Target command:

```bash
curriculum-gen content init
```

### Options

- `--output <path>`
  - optional output path
  - default: `./candidate.json`
- `--force`
  - overwrite the destination file if it already exists
  - default: false

Alias support is not required.

## Template Source
The command must not hardcode the example JSON inline in Python.

It should read from a single canonical bundled asset that is available in both:

- source execution
- packaged binary execution

If `data/example.json` is currently only a development fixture, the task should
promote or mirror the canonical runtime template into a bundled asset path such
as:

```text
assets/examples/candidate.example.json
```

The implementation should avoid maintaining divergent copies of the starter
candidate template.

Required policy:

- one canonical example template source for runtime bootstrap;
- packaged binary must be able to read it;
- docs should point to that canonical source and to `content init` as the
  preferred user workflow.

## Required Behavior

### 1. Default output path

When the user runs:

```bash
curriculum-gen content init
```

The command should write:

```text
./candidate.json
```

using the bundled example candidate content.

### 2. Existing file protection

If the output file already exists and `--force` is not provided:

- the command must fail clearly
- exit non-zero
- explain that the file already exists
- suggest `--force` or `--output`

Example error style:

```text
Error: candidate file already exists: ./candidate.json
Use --force to overwrite it or --output to choose another path.
```

### 3. Forced overwrite

If `--force` is provided:

- overwrite the output file
- exit zero on success

### 4. Alternate output path

If `--output` is provided, write to that path instead of `./candidate.json`.

The command should create parent directories when reasonable, consistent with
other project commands that write files.

### 5. Success output

On success, print a short confirmation that includes:

- where the file was written
- that the file is a starter example candidate
- that the file can be validated with `curriculum-gen content lint`

Example:

```text
Created: ./candidate.json
This is a starter example candidate. Edit it and validate with `curriculum-gen content lint`.
```

## Relationship With Existing Schema
The project already ships `assets/schemas/candidate.schema.json`.

This command should generate a candidate example/template that conforms to the
current loader expectations and is suitable for immediate editing.

Required implementation behavior:

- the bootstrapped JSON must be valid input for the canonical loader
- the bootstrapped JSON should pass `content lint` with either a clean result or
  only clearly documented non-blocking warnings
- the command should not output the raw JSON Schema file instead of the example
  candidate JSON

## Error Handling
The command must fail clearly for:

- example asset missing
- example asset unreadable
- example asset invalid JSON
- output path unwritable
- output path already exists without `--force`

Do not emit Python tracebacks for expected user errors.

## Resource Handling
Because the command must work in the packaged binary, the example asset must be
included in bundled resources.

This task must verify that:

- the example template can be found from source execution
- the example template can be found from packaged execution

If `_resources.py` needs a helper such as `example_candidate_path()`, add it
there.

## Documentation Updates
Update `project.md` to include:

- `curriculum-gen content init` in the CLI structure
- the purpose of the command
- the canonical example candidate asset location if relevant
- the preferred onboarding path for creating a new candidate JSON

Update `agents.md` only if command examples or verification guidance should
mention this command explicitly.

Any documentation that currently points users directly to manually copying an
example fixture should be aligned to the new bootstrap command.

## Verification
Minimum verification should include:

```bash
./curriculum-gen-dev content init --output /tmp/curriculum-gen-candidate-init.json
./curriculum-gen-dev content lint /tmp/curriculum-gen-candidate-init.json
./curriculum-gen-dev content init --output /tmp/curriculum-gen-candidate-init.json
./curriculum-gen-dev content init --output /tmp/curriculum-gen-candidate-init.json --force

.venv/bin/python build.py

./curriculum-gen content init --output /tmp/curriculum-gen-candidate-init-packaged.json
./curriculum-gen content lint /tmp/curriculum-gen-candidate-init-packaged.json
```

Expected outcomes:

1. first command creates the file successfully
2. lint confirms the bootstrapped JSON is structurally valid
3. second init command fails because the file already exists
4. forced overwrite succeeds
5. packaged binary also creates a valid starter candidate file

If the environment prevents writing to `/tmp`, use another writable path and
document that change in history.

## Acceptance Criteria
1. `curriculum-gen content init` exists.
2. By default it writes `./candidate.json`.
3. It uses a bundled example candidate asset, not an inline hardcoded JSON
   string.
4. It refuses to overwrite an existing file unless `--force` is used.
5. It supports `--output <path>`.
6. The generated file is valid for the canonical candidate loader.
7. The generated file is appropriate as an editable starter template for users.
8. It works in both source execution and packaged binary execution.
9. Documentation is updated.
10. A history entry records what changed and how it was verified.

## Notes For The Implementing Agent
- Keep the command behavior parallel to the existing top-level `init` command.
- Prefer reuse of existing resource-loading helpers over introducing a separate
  resource lookup pattern.
- If `data/example.json` and the bundled runtime template would otherwise drift,
  consolidate them around a single canonical source of truth.
- Do not widen scope into schema redesign or template personalization.
