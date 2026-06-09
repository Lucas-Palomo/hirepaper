# 004 - Turn the project into a CLI

## Status
Completed

## Context
The project already implements the core resume generation pipeline, but it now needs a clearer command-line interface as the main user entry point.

The CLI should make the pipeline easier to run, configure, and operate without exposing internal project details unnecessarily.

## Goal
Provide a proper CLI for generating resumes and managing execution behavior in a predictable way.

## Scope
Convert the project entry flow into a user-facing command-line interface that:
- accepts the main generation inputs;
- controls locale and output behavior;
- optionally persists execution logs;
- keeps final artifacts and operational artifacts separated.

## Requirements
### 1. CLI entry point
The project should expose a clear CLI entry point for resume generation.

The CLI should provide at least:
- a primary `generate` command;
- a `doctor` command for environment diagnostics;
- a `help` command or equivalent help output for usage instructions.

The main generation flow must require these flags:
- `--input`
- `--locale`
- `--output`

The CLI should also support operational flags related to logging and execution behavior.

### 1.1 Expected command shape
The expected primary command is:

```bash
curriculum-gen generate --input <file> --locale <locale> --output <file>
```

The CLI should also provide an environment diagnostic command, for example:

```bash
curriculum-gen doctor
```

The CLI must also provide help output, for example:

```bash
curriculum-gen --help
curriculum-gen generate --help
curriculum-gen doctor --help
```

### 1.2 Required flags
The `generate` command must require:
- `--input`: path to the candidate JSON input file;
- `--locale`: output locale, limited to supported project locales;
- `--output`: path to the final generated PDF.

### 1.3 Doctor command responsibilities
The `doctor` command should inspect whether the local environment is ready to generate resumes.

It should verify at least:
- required Python runtime assumptions;
- availability of the LaTeX toolchain needed by the project;
- any required project directories or writable paths that affect execution.

The command should report actionable diagnostics clearly.

### 2. Output directory rules
The `output/` directory should keep only the final generated `.pdf`.

The CLI should avoid leaving temporary or operational files in `output/`, including examples such as:
- `.tex`
- `.log`
- `.aux`
- compilation diagnostics
- other transient generation artifacts

### 3. Log directory rules
If the CLI is configured to persist logs, those files should be written to a dedicated `logs/` directory.

This includes, when applicable:
- execution logs;
- LaTeX compilation logs;
- diagnostic files useful for debugging failed runs.

If log persistence is disabled, the CLI may keep execution output ephemeral.

### 4. Logging mode
The task should define a simple logging behavior, for example:
- default mode without persisted logs;
- optional flag to save logs to disk;
- predictable log file naming and placement.

### 5. User experience
The CLI should provide:
- clear help output;
- clear error messages;
- explicit success/failure reporting;
- predictable argument naming and defaults.

## Constraints
- Preserve the current generation pipeline as much as possible.
- Avoid mixing final deliverables with debugging artifacts.
- Keep the CLI simple and focused on the actual project workflow.
- Do not add unnecessary command complexity before multiple workflows actually exist.

## Recommended Direction
Implement a small but solid CLI around the existing generator, with:
- one primary command for resume generation;
- one `doctor` command for environment checks;
- explicit required flags for input, locale, and output;
- an optional flag for log persistence;
- a dedicated `logs/` directory for persisted diagnostics;
- internal cleanup rules so `output/` contains only the generated PDF artifact.

For the CLI framework, `typer` is the recommended direction.

Rationale:
- it is idiomatic for modern Python CLIs;
- it provides good help output by default;
- it keeps argument declaration readable;
- it is widely used and aligns with the project's dependency guidance.

## Expected Outcome
- the project can be used through a proper command-line interface;
- the final PDF generation workflow becomes easier to operate;
- `output/` remains clean and focused on the generated document;
- logs and diagnostics are separated into `logs/` when requested.

## Notes
This task is about operationalizing the current pipeline as a usable CLI, not redesigning the generator architecture.
