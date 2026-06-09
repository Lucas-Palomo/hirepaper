# 023 - Align default template, prune legacy layouts, and sync CLI docs

## Status
Completed

## Context
The repository had three remaining specification drift points after the `sdd/`
rename:

- `generate_latex()` still defaulted to a legacy template path;
- `project.md` described the CLI topology imprecisely;
- `build.py` documented a build command that did not match the root guidance in
  `agents.md` and `project.md`.

The repository also still carried two deprecated layout template pairs even
though the canonical direction had already converged on a single `standard`
layout.

These were small issues individually, but they reduced confidence in the SDD
documents as the canonical description of the current system.

## Goal
Remove the remaining drift between code defaults and project documentation for
template selection, CLI structure, and build instructions, and prune deprecated
layout artifacts while keeping `--layout` reserved for future extension.

## Scope
This task may update:
- `src/curriculum_gen/generator.py`
- `src/curriculum_gen/cli.py`
- `agents.md`
- `project.md`
- `build.py`
- `templates/`
- `sdd/history/`

This task should not:
- change candidate schema behavior;
- change PDF layout rendering rules beyond removing deprecated template options;
- change ATS validation behavior;
- change packaging behavior beyond documentation alignment.

## Required Behavior
- `generate_latex()` must default to the canonical `standard` template.
- Deprecated template files must be removed from the repository.
- The CLI must keep `--layout`, but only support `standard` and describe the
  flag as reserved for future layouts.
- `project.md` must describe the CLI topology as it actually exists.
- Build instructions must be consistent across root documentation and `build.py`.
- The packaged binary must still build and render CLI help after the change.

## Acceptance Criteria
1. `src/curriculum_gen/generator.py` defaults to `standard.tex`.
2. Only `standard.tex` / `standard.cls` remain in `templates/`.
3. `src/curriculum_gen/cli.py` accepts `--layout standard` and treats the flag
   as reserved for future layouts.
4. `project.md` documents `doctor` as a top-level command and `content`, `pdf`,
   and `llm` as subcommand groups, with `standard` as the only current layout.
5. `build.py` usage text matches the documented `.venv/bin/python build.py`
   command.
6. `agents.md`, `project.md`, and `build.py` no longer disagree on the build
   command.
7. `./curriculum-gen-dev --help` succeeds.
8. `./curriculum-gen-dev pdf generate --help` shows `--layout` as a reserved
   future-facing flag.
9. `.venv/bin/python build.py` succeeds.
10. `./curriculum-gen --help` succeeds after rebuild.
11. The work is recorded in `sdd/history/023-align-default-template-cli-docs-and-build-instructions.md`.

## Verification
```bash
./curriculum-gen-dev --help
./curriculum-gen-dev pdf generate --help
.venv/bin/python build.py
./curriculum-gen --help
```

## Completion Record
Completed in `sdd/history/023-align-default-template-cli-docs-and-build-instructions.md`.
