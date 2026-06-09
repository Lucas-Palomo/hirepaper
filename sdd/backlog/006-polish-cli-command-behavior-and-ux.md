# 006 - Polish CLI command behavior and UX

## Status
Completed

## Context
The CLI already exists, but some command behaviors are still awkward or misplaced.

Two issues stand out:
- `doctor` currently checks writable access for output/log paths in a way that feels operational rather than diagnostic;
- `generate` is not yet shaped like a natural command-line workflow.

This task exists to improve CLI usability without changing the underlying resume generation purpose.

## Goal
Refine the CLI so it behaves more naturally for day-to-day usage and follows clearer command responsibility boundaries.

## Scope
This task covers:
- `generate` command ergonomics;
- `help` behavior;
- `doctor` command responsibility cleanup;
- small argument and UX improvements for the existing CLI.

It does not require redesigning the generation pipeline itself.

## Required Changes
### 1. `generate` should accept the input file as a positional argument
The main generation command should no longer require `--input`.

Preferred shape:

```bash
curriculum-gen generate <input_json_file> -o <output_pdf_file>
```

The input file should be accepted as a positional argument.

### 2. `--output` must support the short form `-o`
The output argument should keep a clear long form and also provide a short alias:
- `--output`
- `-o`

This should become the normal ergonomic way to specify the destination PDF.

### 3. `--locale` must support the short form `-l`
The locale argument should keep a clear long form and also provide a short alias:
- `--locale`
- `-l`

This should make the command easier to type while preserving explicit locale selection.

### 4. `generate` help behavior
Running the command without the required generation arguments should guide the user clearly.

Expected behavior:

```bash
curriculum-gen generate
```

should display the help screen for the `generate` command instead of failing with an opaque error.

The normal help paths should also continue to work:

```bash
curriculum-gen --help
curriculum-gen generate --help
```

### 5. Re-evaluate `doctor` responsibilities
The current `doctor` behavior is checking write permissions for output/log-related directories.

That behavior is not the best fit for an environment diagnostic command.

The task should refactor `doctor` so it focuses on environment-level diagnostics, for example:
- Python runtime compatibility;
- presence of the required LaTeX engine(s);
- other stable environment prerequisites.

Checks that are specific to the actual output path chosen by the user should be handled during `generate`, because only `generate` knows the real runtime target.

### 6. Move runtime path validation into `generate`
Validation related to the actual requested run should happen in `generate`, not in `doctor`.

This includes, when applicable:
- verifying that the provided input path exists and is readable;
- verifying that the chosen output path can be created or written;
- verifying log persistence paths if the command is run in a mode that saves logs.

The command should fail clearly and specifically when one of these runtime conditions is not satisfied.

### 7. Keep locale handling coherent
This task should preserve the locale behavior already introduced by the CLI and localization work.

If `--locale` remains required, that should be reflected clearly in help output.
If it has a default, the default should be clearly documented.

## Recommended Direction
Refactor the CLI toward a more conventional command-line UX:
- positional input file for `generate`;
- `-o`/`--output` for destination;
- `-l`/`--locale` for locale selection;
- `doctor` limited to environment diagnostics;
- runtime file-system concerns handled inside `generate`;
- explicit and friendly help behavior when `generate` is invoked incorrectly or incompletely.

## Constraints
- Preserve the current CLI purpose and command set unless a small rename is clearly justified.
- Avoid expanding `doctor` into a catch-all operational command.
- Keep the CLI simple.
- Do not add new complexity that is unrelated to usability and command responsibility.

## Acceptance Criteria
The task should be considered complete only if all of the following are true:

1. `generate` accepts the input JSON path as a positional argument.
2. `generate` supports `-o` as a short form of `--output`.
3. `generate` supports `-l` as a short form of `--locale`.
4. `curriculum-gen generate` with no required arguments shows the `generate` help screen.
5. `doctor` no longer performs output/log writability checks that belong to runtime execution.
6. `generate` performs the path and writability checks needed for the actual requested run.
7. Help output remains clear for both the root command and subcommands.

## Suggested Verification
The implementing agent should verify at least:

```bash
curriculum-gen --help
curriculum-gen generate --help
curriculum-gen generate
curriculum-gen doctor
curriculum-gen generate data/candidate.json -o output/resume.pdf -l en
```

## Notes For The Implementing Agent
- The example shown by the user uses a positional input path and short flags. Treat that as the desired UX.
- The command generates a PDF, so the output example should point to a `.pdf` file, even if prior wording accidentally says `output_json_file`.
- Keep `doctor` focused on stable environment checks, not per-run execution details.
