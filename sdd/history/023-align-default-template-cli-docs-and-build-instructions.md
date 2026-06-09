# 023 - Align default template, prune legacy layouts, and sync CLI docs

**Date:** 2026-06-05
**Agent:** Codex GPT-5.4 + opencode (deepseek-v4-flash)

---

## Context

After the repository path cleanup, three smaller inconsistencies remained:

- `generate_latex()` still defaulted to the legacy inline template instead of
  the canonical `standard` template;
- `project.md` described the CLI as if `doctor` were a subcommand group and
  omitted the `llm` group from the topology summary;
- `build.py` still documented `python3 build.py`, while root instructions
  already standardized on `.venv/bin/python build.py`.

The repository also still carried deprecated `standard-headline-inline` and
`standard-headline-tabular` template files even though the product direction had
already converged on a single canonical `standard` layout.

## Changes

- Updated `src/curriculum_gen/generator.py` so the default template fallback is
  `templates/standard.tex`.
- Removed deprecated legacy template files:
  - `templates/standard-headline-inline.tex`
  - `templates/standard-headline-inline.cls`
  - `templates/standard-headline-tabular.tex`
  - `templates/standard-headline-tabular.cls`
- Simplified `src/curriculum_gen/cli.py` so `--layout` remains available but
  only supports `standard` and is explicitly documented as reserved for future
  layouts.
- Updated `project.md` to describe the CLI accurately as:
  - top-level `doctor` command;
  - `content`, `pdf`, and `llm` subcommand groups;
  - `standard` as the only current layout.
- Updated the `build.py` docstring usage example to `.venv/bin/python build.py`
  so it matches `agents.md` and `project.md`.
- Added backlog task `023` to record the drift-alignment work.

## Decisions and Tradeoffs

- The generator fallback was aligned to the canonical layout even though the CLI
  already passed template paths explicitly. This removes hidden divergence for
  direct programmatic use of `generate_latex()`.
- The legacy layouts were removed from the repository because keeping dead
  template variants increased maintenance cost without adding supported product
  value.
- `--layout` was intentionally preserved instead of removed so future layout
  expansion can reuse the existing CLI surface without another breaking change.
- Build guidance was normalized to the project-local virtual environment because
  that is the documented and historically verified path in this repository.

## Verification

```bash
./curriculum-gen-dev --help
./curriculum-gen-dev pdf generate --help
.venv/bin/python build.py
./curriculum-gen --help
```

Results:
- source-based CLI help rendered successfully;
- `pdf generate --help` rendered successfully and documented `--layout` as a
  reserved future-facing flag with `standard` as the current supported value;
- packaged binary rebuilt successfully at `dist/curriculum-gen`;
- packaged CLI help rendered successfully after rebuild.

## Residual Risks

- Historical backlog and history entries still mention the removed legacy
  layouts because they record prior states of the project. That is intentional.
