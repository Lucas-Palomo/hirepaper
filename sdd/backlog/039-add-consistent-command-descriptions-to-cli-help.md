# 039 - Add consistent command descriptions to CLI help

## Status
Completed

## Context
The CLI help output is already functional, but command descriptions are still
inconsistent across the public command tree.

Observed current behavior:

- top-level group descriptions are present for `content`, `pdf`, and `llm`;
- `doctor` and `init` already have visible descriptions in top-level help;
- some subcommands still appear in help output without a visible description,
  such as:
  - `content help`
  - `content lint`
  - `content match`
  - `content tailor`
  - `pdf help`
  - `pdf generate`
  - `pdf check`
  - `llm help`
  - `llm health`
  - `llm usage`

That makes the help output less scannable than it should be.

A published CLI should present a coherent help surface where every public
command and subcommand has a short, clear user-facing description.

## Goal
Add consistent help descriptions to all public CLI commands and major
subcommands so the help output is self-explanatory when users scan the command
lists.

Target outcomes:

- every public command shown in CLI help has a visible short description;
- descriptions are concise, accurate, and consistent in tone;
- help output becomes easier to scan without changing command behavior.

## Product Decision
This task is about CLI presentation quality, not command behavior.

Required policy:

- all public commands and major subcommands should have an explicit short help
  description;
- descriptions should explain what the command does, not restate the name in a
  circular way;
- wording should stay concise and operational.

## Scope
This task may update:

- `src/hirepaper/cli.py`
- `project.md` if command descriptions there should be aligned to the clearer
  help wording
- `agents.md` only if command examples or guidance should reflect refined help
  wording
- `sdd/history/`

This task should not:

- redesign the CLI tree;
- rename commands;
- change runtime behavior;
- widen into a broader documentation rewrite.

## Required Command Coverage
At minimum, the implementing agent should ensure visible descriptions for:

### Top-level commands
- `help`
- `doctor`
- `init`
- `content`
- `pdf`
- `llm`

### `content` subcommands
- `help`
- `init`
- `lint`
- `match`
- `tailor`

### `pdf` subcommands
- `help`
- `generate`
- `check`

### `llm` subcommands
- `help`
- `health`
- `usage`

If additional public commands exist by the time of implementation, they should
follow the same standard.

## Required Behavior

### 1. Short descriptions in command lists
Commands shown in grouped help output should no longer appear blank where a
short description is expected.

Examples of currently weak help surfaces include grouped listings where entries
such as `lint`, `match`, `tailor`, `generate`, `check`, `health`, or `usage`
appear without a short explanatory label.

After this task, those commands should present concise visible descriptions in
help listings.

### 2. Description quality
Descriptions should be:

- short;
- specific;
- action-oriented;
- consistent with actual command behavior.

Avoid poor descriptions such as:

- repeating the command name with no added meaning;
- vague placeholders;
- long paragraphs in the command list.

Good descriptions should read more like:

- what artifact the command creates or checks;
- what input domain it operates on;
- whether it bootstraps, validates, diagnoses, generates, or tailors.

### 3. Keep help output concise
This task should improve scanning quality without turning command lists into
verbose documentation blocks.

The command list should stay compact; longer explanation belongs in command help
or docs, not in the one-line summary field.

### 4. No behavior change
This task must not alter:

- command semantics;
- option behavior;
- CLI structure;
- exit status logic.

It is strictly a help-surface improvement.

## Recommended Implementation Direction
Preferred implementation direction:

- add or refine Typer `help=` text on command decorators where missing;
- keep description wording consistent across the command tree;
- reuse phrasing patterns where that improves coherence, but avoid robotic
  repetition.

Implementation should avoid:

- hardcoding long multi-line description blocks where a short summary is needed;
- changing command bodies when only help metadata is required.

## Documentation Updates
If `project.md` or other internal docs describe commands using visibly weaker or
stale wording, the implementing agent may align those descriptions.

That alignment is secondary. The primary required outcome is the CLI help
surface itself.

## Verification
Minimum verification should include:

```bash
./hirepaper-dev --help
./hirepaper-dev content --help
./hirepaper-dev pdf --help
./hirepaper-dev llm --help

.venv/bin/python build.py

./hirepaper --help
./hirepaper content --help
./hirepaper pdf --help
./hirepaper llm --help
```

The implementing agent should inspect the command lists and confirm that the
covered commands now display visible descriptions.

## Expected Verification Outcomes
The implementing agent should confirm:

1. top-level commands all show descriptions;
2. `content` subcommands all show descriptions;
3. `pdf` subcommands all show descriptions;
4. `llm` subcommands all show descriptions;
5. source and packaged help output remain aligned.

## Acceptance Criteria
1. Public top-level commands shown in help have visible descriptions.
2. Public `content` subcommands shown in help have visible descriptions.
3. Public `pdf` subcommands shown in help have visible descriptions.
4. Public `llm` subcommands shown in help have visible descriptions.
5. Descriptions are concise and consistent with actual behavior.
6. The change is verified in source mode and packaged mode.
7. A history entry records the implementation and verification.

## Notes For The Implementing Agent
- Treat this as a CLI polish task.
- Optimize for scanability of help output.
- Keep descriptions short enough to remain readable in grouped command lists.
