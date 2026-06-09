# 037 - Add explicit `help` subcommands for CLI groups and clarify `doctor` label

## Status
Completed

## Context
The current CLI already behaves reasonably when invoked without a subcommand.
Each Typer group uses a callback that prints help when no invoked subcommand is
present.

That means these forms already behave like help entrypoints:

```bash
curriculum-gen
curriculum-gen content
curriculum-gen pdf
curriculum-gen llm
```

However, the CLI does not currently expose `help` as an explicit subcommand.

For users who naturally expect command trees such as:

```bash
curriculum-gen help
curriculum-gen content help
curriculum-gen pdf help
curriculum-gen llm help
```

that omission creates unnecessary friction.

Even though `--help` is standard and the empty-group callbacks already show help,
explicit `help` subcommands improve discoverability and make the CLI more
forgiving for users coming from tools that support `help` as a real command.

## Goal
Add explicit `help` subcommands so that top-level and grouped CLI entrypoints
accept `help` as a command alias for showing their corresponding help output,
and improve the CLI label/description for the top-level `doctor` command.

Target outcomes:

- `curriculum-gen help` shows the same top-level help as `curriculum-gen --help`
- `curriculum-gen content help` shows the same group help as
  `curriculum-gen content --help`
- `curriculum-gen pdf help` shows the same group help as `curriculum-gen pdf --help`
- `curriculum-gen llm help` shows the same group help as `curriculum-gen llm --help`
- top-level help presents `doctor` with a clearer diagnostic description
- `curriculum-gen doctor --help` communicates the command’s environment-check role more explicitly
- existing `--help` behavior remains intact
- existing empty-entrypoint callback help behavior remains intact

## Product Decision
The CLI should support both styles:

- flag-based help: `--help`
- explicit command-style help: `help`

This is not a replacement for `--help`.
It is an additional user-facing convenience layer.

Required policy:

- keep `--help` canonical and fully supported;
- keep empty group invocation showing help;
- add explicit `help` commands for the main CLI tree and its major groups.

## Scope
This task may update:

- `src/curriculum_gen/cli.py`
- `project.md`
- `agents.md` only if command examples or execution guidance should mention the
  new help paths
- `sdd/history/`

This task should not:

- redesign the CLI tree;
- rename `doctor`;
- remove `--help` behavior;
- remove the existing callback-based group help behavior;
- add help subcommands to every leaf command unless strictly necessary;
- widen into a broader CLI UX redesign.

## Required Command Surface
The CLI must support these explicit forms:

```bash
curriculum-gen help
curriculum-gen content help
curriculum-gen pdf help
curriculum-gen llm help
```

Required result:

- each command prints the same help text that the corresponding `--help` form
  would show;
- each command exits successfully.

## Required Behavioral Rules

### 1. Top-level explicit help
When the user runs:

```bash
curriculum-gen help
```

The CLI must print the same top-level help output as:

```bash
curriculum-gen --help
```

### 2. Group explicit help
When the user runs one of:

```bash
curriculum-gen content help
curriculum-gen pdf help
curriculum-gen llm help
```

The CLI must print the corresponding group help output, equivalent to:

```bash
curriculum-gen content --help
curriculum-gen pdf --help
curriculum-gen llm --help
```

### 3. Existing entrypoint help behavior remains
These existing forms must keep working:

```bash
curriculum-gen
curriculum-gen content
curriculum-gen pdf
curriculum-gen llm
```

They should continue to show the corresponding help text when invoked without a
subcommand.

### 4. Existing `--help` behavior remains canonical
These forms must continue to work unchanged:

```bash
curriculum-gen --help
curriculum-gen content --help
curriculum-gen pdf --help
curriculum-gen llm --help
```

This task must not degrade or special-case away the standard flag-based help
path.

### 5. Exit status
Explicit `help` subcommands should exit with success status.

They should not be treated as invalid commands or not-implemented stubs.

### 6. Clearer `doctor` label
The top-level `doctor` command must remain named:

```bash
curriculum-gen doctor
```

But its help presentation should be clearer.

Required behavior:

- top-level help should describe `doctor` as environment diagnostics,
  dependency checks, or equivalent wording;
- `curriculum-gen doctor --help` should communicate that it is the canonical
  command for checking local runtime/tooling readiness;
- runtime behavior of `doctor` should remain unchanged in this task.

## Scope Boundary For Leaf Commands
This task is primarily about the CLI root and major command groups.

Required explicit help subcommands:

- top-level app
- `content`
- `pdf`
- `llm`

Optional but not required:

- `curriculum-gen pdf generate help`
- `curriculum-gen content match help`
- other leaf-command `help` aliases

The implementing agent may extend the behavior further if it remains coherent,
but the minimum contract is the four entrypoints listed above.

## Recommended Implementation Direction
The current CLI already has shared group-help callback behavior.

Preferred implementation direction:

- reuse the existing help-printing path rather than duplicating help text;
- add explicit `help` commands that delegate to the same underlying group help
  rendering used by `--help` or empty invocation;
- keep command wiring explicit and readable.

Implementation should avoid:

- manually hardcoding help text strings;
- duplicating large blocks of help output logic;
- introducing special parsing hacks that make the command tree harder to
  maintain.

## Documentation Updates
Update `project.md` to mention that the CLI supports both:

- `--help`
- explicit `help` subcommands on major entrypoints

Update `project.md` and `agents.md` if needed so the `doctor` command
description matches the clearer CLI wording.

Update `agents.md` only if examples or execution guidance should mention these
explicit help paths.

## Verification
Minimum verification should include:

```bash
./curriculum-gen-dev help
./curriculum-gen-dev --help
./curriculum-gen-dev content help
./curriculum-gen-dev content --help
./curriculum-gen-dev pdf help
./curriculum-gen-dev pdf --help
./curriculum-gen-dev llm help
./curriculum-gen-dev llm --help
./curriculum-gen-dev doctor --help

.venv/bin/python build.py

./curriculum-gen help
./curriculum-gen content help
./curriculum-gen pdf help
./curriculum-gen llm help
./curriculum-gen doctor --help
```

The implementing agent should compare outputs semantically to confirm the
explicit `help` forms show the same command scope and descriptions as the
corresponding `--help` forms.

## Expected Verification Outcomes
The implementing agent should confirm:

1. `curriculum-gen help` works;
2. `curriculum-gen content help` works;
3. `curriculum-gen pdf help` works;
4. `curriculum-gen llm help` works;
5. top-level help shows a clearer description for `doctor`;
6. `doctor --help` also shows a clearer diagnostic description;
7. `--help` still works at all those levels;
8. empty group invocation still shows help;
9. source and packaged execution behave consistently.

## Acceptance Criteria
1. The CLI supports `curriculum-gen help`.
2. The CLI supports `curriculum-gen content help`.
3. The CLI supports `curriculum-gen pdf help`.
4. The CLI supports `curriculum-gen llm help`.
5. These explicit help subcommands print the same scoped help content as their
   corresponding `--help` forms.
6. The top-level CLI help presents `doctor` with a clearer label/description.
7. `curriculum-gen doctor --help` presents a clearer diagnostic description.
8. Existing empty-entrypoint help behavior remains intact.
9. Existing `--help` behavior remains intact.
10. The change is verified in source mode and packaged mode.
11. A history entry records the implementation and verification.

## Notes For The Implementing Agent
- Treat this as a CLI ergonomics task, not a command-tree redesign.
- Reuse existing help rendering paths wherever possible.
- Do not weaken the standard `--help` path to add command-style help.
- Keep `doctor` as the canonical diagnostic entrypoint; only improve its
  presentation.
