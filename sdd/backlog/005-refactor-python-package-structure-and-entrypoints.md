# 005 - Refactor Python package structure and entrypoints

## Status
Completed

## Context
The project currently works, but its Python structure is inconsistent with the direction already taken by the CLI work.

Two structural issues need to be corrected:
- the project uses a `src/` directory as if `src` were the package name;
- there is still a `generate.py` file at the repository root even though the project is evolving toward a proper CLI entrypoint.

The `src/` directory itself is not the problem. The problem is that the current import/package layout treats `src` as the application package instead of using `src` as a source root containing a real package.

## Goal
Refactor the Python project layout so it follows normal packaging conventions and exposes a single clear application entry strategy.

## Why This Task Exists
The current structure creates unnecessary ambiguity:
- it is unclear whether the official interface is `generate.py`, `python -m ...`, or the installed CLI command;
- `src` is being used as the logical package namespace, which is poor practice for a packaged Python application;
- some runtime path logic is coupled to the repository layout in ways that should be reduced where practical.

This task exists to make the project easier to install, run, maintain, and extend.

## Required Outcome
After this task, the project should:
- keep `src/` only as the source root;
- define a real Python package name for the application;
- expose the CLI through that real package;
- eliminate or deprecate root-level entrypoint duplication cleanly;
- preserve the current user-facing CLI behavior unless a change is explicitly justified.

## Scope
This task is a structural refactor.

It covers:
- package layout;
- import paths;
- CLI entrypoints;
- packaging metadata;
- removal or controlled deprecation of legacy root scripts.

It does not require redesigning the generator pipeline itself.

## Detailed Instructions
### 1. Introduce a real package under `src/`
Refactor the source tree so that `src/` contains a properly named application package.

Recommended package name:
- `curriculum_gen`

Target direction:

```text
src/
  curriculum_gen/
    __init__.py
    __main__.py
    cli.py
    generator.py
    loader.py
    locale.py
    models.py
```

The final package name may differ only if there is a strong reason. If changed, the reason must be documented.

### 2. Stop using `src` as the package namespace
The project must no longer expose imports or entrypoints like:
- `src.cli:app`
- `python -m src`

Instead, it should use the real package namespace, for example:
- `curriculum_gen.cli:app`
- `python -m curriculum_gen`

### 3. Update packaging metadata
Update `pyproject.toml` so it reflects the refactored package structure correctly.

This includes:
- script entrypoints;
- package discovery or package-dir configuration if needed;
- any metadata required for editable install or normal installation to keep working.

The CLI script should point to the real package, not to `src` as a fake package name.

### 4. Resolve the root `generate.py` situation
The repository root currently contains `generate.py`.

This file should not remain as a competing long-term interface if the CLI is now the official entrypoint.

Preferred direction:
- remove `generate.py` entirely if it is no longer needed;
- or convert it into a minimal compatibility wrapper only if temporary backward compatibility is truly needed.

If a compatibility wrapper is kept temporarily:
- it must delegate to the official CLI path;
- it must not duplicate generation logic;
- it should be clearly marked as transitional;
- the intended removal path should be documented.

If there is no strong compatibility need, removing `generate.py` is the cleaner outcome.

### 5. Preserve one clear official interface
After the refactor, the project should have one clear operational story:
- installed command, for example `curriculum-gen ...`;
- optional module execution, for example `python -m curriculum_gen ...`.

The project should not leave multiple equally “official” execution styles competing with each other without documentation.

### 6. Review runtime path assumptions
Inspect code that derives paths from file location and repository layout.

Examples to review:
- template directory resolution;
- output directory resolution;
- logs directory resolution;
- locale directory resolution;
- data/example file references.

The goal is not to eliminate all path logic blindly, but to make it coherent with the new package structure.

The refactor should avoid brittle assumptions that only work because files currently sit in a specific repository layout.

### 7. Keep behavior stable
Do not change the project’s external behavior unnecessarily.

The refactor should preserve, as much as possible:
- the existing CLI command set;
- required flags such as `--input`, `--locale`, and `--output`;
- current generation flow;
- current locale and logging behavior.

This task is about structure and maintainability, not about changing product behavior.

### 8. Clean repository artifacts if needed
If the refactor makes some files or paths obsolete, clean them up deliberately.

Examples:
- stale `__pycache__` references should not matter for source control;
- duplicate entrypoint files should not remain without purpose;
- packaging configuration should not reference paths that no longer exist.

Do not remove project files casually; only remove what is clearly obsolete after the refactor.

## Constraints
- Follow standard Python packaging conventions.
- Keep the refactor incremental and readable.
- Avoid broad unrelated rewrites.
- Preserve current functionality.
- Do not introduce extra abstraction unless it clearly improves the structure.

## Acceptance Criteria
The task should be considered complete only if all of the following are true:

1. The code lives under a real package inside `src/`.
2. `src` is no longer the application package namespace.
3. `pyproject.toml` points CLI entrypoints to the real package.
4. `python -m <real_package>` works as a module entrypoint.
5. The official CLI still works after the refactor.
6. `generate.py` is either removed or reduced to a thin documented compatibility wrapper.
7. Imports and path resolution still work after the move.

## Recommended Verification
The implementing agent should verify at least:
- CLI help output works;
- `generate --help` still works;
- `doctor` still works;
- the package can be invoked as a module;
- a real PDF generation path still works after the move.

Suggested verification examples:

```bash
curriculum-gen --help
curriculum-gen generate --help
curriculum-gen doctor
python -m curriculum_gen --help
curriculum-gen generate --input data/candidate.json --locale en --output output/resume.pdf
```

## Notes For The Implementing Agent
- Do not confuse “using a `src/` layout” with “naming the package `src`”. The first is normal; the second is what must be fixed.
- Prefer the package name `curriculum_gen` unless there is a compelling reason not to.
- Treat `generate.py` as legacy unless a documented compatibility requirement exists.
- Keep the CLI as the primary interface.
