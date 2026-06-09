# 037 - Explicit help subcommands and clearer `doctor` label

**Date:** 2026-06-08
**Agent:** Codex (GPT-5)

---

## Context

The CLI already had acceptable help behavior when invoked without a subcommand,
thanks to Typer group callbacks that printed scoped help for:

- `curriculum-gen`
- `curriculum-gen content`
- `curriculum-gen pdf`
- `curriculum-gen llm`

However, task `037` was broadened to cover two related CLI ergonomics issues in
one coherent change:

- the command tree did not expose explicit `help` subcommands, so flows such as
  `curriculum-gen help` or `curriculum-gen pdf help` were unavailable even
  though the underlying help behavior already existed;
- the top-level `doctor` command was functionally correct but too reliant on
  its name alone in help output, and its environment-diagnostics role needed a
  clearer label/description.

## Changes Made

### 1. Added explicit `help` subcommands to major CLI entrypoints

Updated [`src/curriculum_gen/cli.py`](/home/palomo/Projects/Personal/curriculum-gen/src/curriculum_gen/cli.py) to add explicit `help` subcommands for:

- `curriculum-gen help`
- `curriculum-gen content help`
- `curriculum-gen pdf help`
- `curriculum-gen llm help`

Implementation details:

- introduced `_show_explicit_help(ctx)` as a small shared helper;
- each explicit `help` command delegates to the parent context’s `get_help()`;
- no help text was hardcoded or duplicated;
- existing callback-based empty-entrypoint help behavior was preserved.

### 2. Clarified the `doctor` command label

Updated the top-level `doctor` command registration to include a clearer help
description:

- top-level label now describes it as environment diagnostics and dependency
  checks;
- command-level help for `doctor --help` now communicates the same role more
  explicitly.

This was done without renaming the command or changing runtime behavior.

### 3. Updated project documentation

Updated [`project.md`](/home/palomo/Projects/Personal/curriculum-gen/project.md) to reflect:

- explicit `help` subcommands in the CLI structure;
- that the CLI supports both `--help` and command-style `help` on the main
  entrypoints;
- clearer wording for `curriculum-gen doctor` as the canonical environment
  diagnostics and dependency-check command.

## Verification

### Source mode

```bash
./curriculum-gen-dev help
./curriculum-gen-dev content help
./curriculum-gen-dev pdf help
./curriculum-gen-dev llm help
./curriculum-gen-dev doctor --help
./curriculum-gen-dev content
```

Results:

- all explicit `help` subcommands executed successfully;
- each printed the expected scoped help output;
- `doctor --help` showed the new clearer description;
- empty group invocation still showed help correctly.

### Packaged build

```bash
.venv/bin/python build.py
```

Result:

- build completed successfully;
- PyInstaller emitted an existing warning about Pydantic V1 on Python 3.14, but
  the artifact was still produced successfully.

### Packaged binary verification

```bash
./curriculum-gen help
./curriculum-gen content help
./curriculum-gen pdf help
./curriculum-gen llm help
./curriculum-gen doctor --help
./curriculum-gen pdf
./curriculum-gen llm
```

Results:

- packaged binary supports the same explicit `help` subcommands;
- `doctor --help` shows the clearer diagnostic description;
- empty grouped entrypoints still show help;
- source and packaged behavior are aligned.

## Decisions & Tradeoffs

- Reused existing help rendering paths instead of duplicating help text.
- Kept `--help` as the canonical standard path while adding `help` as a
  convenience alias.
- Limited explicit `help` subcommands to the top-level app and major groups.
  Leaf-command `help` aliases were intentionally left out of scope.
- Kept `doctor` as the command name and improved only its presentation.

## Residual Risks

- The top-level CLI help now lists `help` as a visible command. That is the
  intended behavior for discoverability, but it does add one more entry to the
  command list.
- Leaf commands still rely on standard `--help`; explicit `help` aliases were
  not added below the major group level.
