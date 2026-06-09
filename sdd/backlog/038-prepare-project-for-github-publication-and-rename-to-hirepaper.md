# 038 - Prepare project for GitHub publication and rename to `hirepaper`

## Status
Completed

## Context
The project is already a working CLI with PDF generation, ATS validation,
content tooling, and packaging support.

However, it still carries signs of an internal/work-in-progress repository
rather than a polished public GitHub project. The main gaps are:

- project naming still uses `curriculum-gen` throughout the codebase,
  documentation, entrypoints, and packaged artifact;
- there is no canonical `README.md` suitable for public discovery and onboarding;
- command documentation is spread across implementation and internal docs rather
  than presented as a polished public entrypoint;
- `project.md` has grown into a large mixed-purpose file containing runtime,
  architecture, important paths, and operational rules together;
- `agents.md` should remain useful, but some project-structure guidance can be
  better separated from agent execution rules;
- the repository still needs a publication-grade `.gitignore` so local build
  artifacts, caches, logs, temporary outputs, and editor/runtime residue do not
  pollute the Git history;
- repository residue and internal naming should be cleaned up so the project
  feels intentionally publishable.

The project should be prepared to look coherent, documented, and intentionally
named when published on GitHub.

## Goal
Prepare the repository for public GitHub publication by:

- renaming the project from `curriculum-gen` to `hirepaper`;
- making `hirepaper` the only canonical CLI/binary name;
- cleaning up repository/documentation residue tied to the old name;
- creating or tightening a publication-grade `.gitignore`;
- improving public-facing documentation;
- documenting the command surface clearly;
- reorganizing `project.md` into a cleaner split of concerns;
- adding a proper top-level `README.md`.

Target outcome:

- the project presents itself publicly as `hirepaper` everywhere that matters;
- a newcomer can understand what the project is, how to install/run it, and
  which commands exist by reading `README.md`;
- internal project context remains available, but in a cleaner document
  structure;
- the packaged executable is `hirepaper` and not `curriculum-gen`.

## Product Decision
The project name should be changed to:

```text
hirepaper
```

Required naming policy after this task:

- `hirepaper` is the only canonical project/product name;
- the public executable name is `hirepaper`;
- `curriculum-gen` should be removed from canonical docs, help text, packaging,
  and public-facing references unless retained only as narrowly scoped migration
  context in history records.

This task is intentionally a public-facing cleanup and rename initiative, not
just a cosmetic string replacement.

## Scope
This task may update:

- root executable wrappers/scripts
- packaging/build configuration
- `pyproject.toml`
- `build.py`
- `src/curriculum_gen/` package contents if naming-sensitive strings or runtime
  identifiers need adjustment
- CLI help text and user-facing strings
- `project.md`
- `agents.md`
- `.gitignore`
- new supporting docs created from a `project.md` split
- `README.md`
- other repo documentation and examples referencing the old project name
- `sdd/history/`

This task may add:

- `README.md`
- one or more new internal project-context documents if `project.md` is split
  into clearer files

This task should not:

- redesign core resume generation semantics;
- widen into unrelated feature work;
- silently remove useful internal project context without relocating it;
- leave the executable naming half-migrated.

## Required Outcomes

### 1. Rename the project to `hirepaper`
All canonical public-facing references should use `hirepaper`.

Required areas to review and update:

- CLI program name shown in help text
- root wrapper scripts
- packaged artifact name
- build output naming
- documentation examples
- project description strings
- README title and usage examples

The final public entrypoint should be:

```bash
./hirepaper
```

The executable should be only `hirepaper`.

### 2. Remove canonical reliance on `curriculum-gen`
After this task, `curriculum-gen` should no longer be the active canonical name
for:

- CLI invocation examples
- packaged binary examples
- README instructions
- primary project docs
- user-facing command documentation

If any legacy mention remains, it should exist only where strictly necessary for
historical or migration context.

### 3. Add a proper `README.md`
Create a top-level `README.md` suitable for GitHub publication.

Minimum required README scope:

- project name: `hirepaper`
- short project description
- core pipeline overview
- key features
- prerequisites / external dependencies
- how to run from source
- how to build the binary
- command overview
- key usage examples
- where to find deeper docs if relevant

The README should be written for a new external reader, not only for internal
agents.

### 4. Document the command surface clearly
The command surface should be documented in a cleaner, public-friendly way.

At minimum, the public docs should clearly cover:

- `hirepaper help`
- `hirepaper doctor`
- `hirepaper init`
- `hirepaper content init`
- `hirepaper content lint`
- `hirepaper content match`
- `hirepaper content tailor`
- `hirepaper pdf generate`
- `hirepaper pdf check`
- `hirepaper llm health`
- `hirepaper llm usage`

The documentation does not need exhaustive prose for every option, but the
commands must be discoverable and explained coherently.

### 5. Improve and split `project.md`
`project.md` currently carries multiple concerns in one place, especially:

- runtime commands
- architecture flow
- important paths
- layout/density rules
- packaging/runtime behavior

This task should improve that structure.

Preferred direction:

- keep one document focused on infrastructure / runtime flow / architecture;
- move file-map / important-path / operational project-structure material into a
  second document;
- leave the resulting structure easier to maintain and easier for agents to read.

A good target shape would be roughly:

- one document for architecture / flow / runtime contracts
- one document for important files / directories / operational map

The exact filenames are up to the implementing agent, but the split must be
clear and intentional.

### 6. Improve `agents.md`
`agents.md` should remain focused on execution rules for agents.

Required direction:

- align the project name with `hirepaper`;
- update command examples to the new executable name;
- ensure references to project-context docs match the new split;
- keep the file focused on execution guidance rather than duplicating large
  chunks of project structure documentation that belong elsewhere.

### 7. Clean repository residue
The implementing agent should identify and clean repository residue that makes
this project feel unpublished or inconsistently named.

Examples may include:

- stale command examples using `curriculum-gen`
- mismatched binary/wrapper names
- outdated doc references
- inconsistent wording between docs and actual CLI behavior
- old naming in packaging or build output
- missing or insufficient ignore rules for generated/local-only files

This cleanup should be disciplined:
- remove or update residue that affects publication quality;
- do not perform broad speculative deletions unrelated to the rename/documentation goal.

### 8. Add or improve `.gitignore`
The repository should include a GitHub-ready `.gitignore` aligned with this
project’s real local artifacts.

Required direction:

- ignore Python cache artifacts such as `__pycache__/` and compiled bytecode;
- ignore local virtual environments such as `.venv/`;
- ignore packaging/build outputs such as `build/` and `dist/`;
- ignore generated runtime outputs such as `output/`, `logs/`, and temporary
  artifacts produced by local verification where appropriate;
- ignore editor/IDE residue such as `.idea/` if the project chooses not to
  publish it;
- keep tracked example/config assets and canonical fixtures that belong in the
  repo;
- avoid overly broad ignore rules that would accidentally hide source,
  templates, docs, or canonical project assets.

This task is not complete if the repository is renamed and documented but still
feels noisy or unsafe to publish due to missing ignore hygiene.

## Required Naming and Entry Point Behavior
After this task, expected command examples should look like:

```bash
./hirepaper --help
./hirepaper doctor
./hirepaper content init --output /tmp/candidate.json
./hirepaper pdf generate data/candidate.json --output output/resume.pdf
./hirepaper pdf check output/resume.pdf
```

If a development entrypoint is still kept, the implementing agent should make a
clear naming decision and document it. Preferred direction:

- use `./hirepaper-dev` for source-mode development execution if a separate dev
  wrapper remains valuable;
- avoid leaving `./curriculum-gen-dev` as the active development entrypoint.

The final decision must be coherent and documented.

## Documentation Expectations
Minimum public-facing documentation deliverables:

- `README.md` exists and is suitable for GitHub landing-page use;
- command overview is documented;
- build/run instructions are documented;
- old project-name references are removed from canonical public docs.

Minimum internal-doc structure deliverables:

- `project.md` is improved and no longer overloaded with mixed concerns;
- a second internal project-context file exists if a split is performed;
- `agents.md` references the resulting structure coherently.

Minimum repository hygiene deliverables:

- `.gitignore` exists or is improved to match the project’s real generated and
  local-only artifacts;
- generated residue that should not be versioned is clearly excluded.

## Verification
Minimum verification should include:

```bash
./hirepaper --help
./hirepaper help
./hirepaper doctor --help
./hirepaper content help
./hirepaper pdf help
./hirepaper llm help

.venv/bin/python build.py

./hirepaper doctor
./hirepaper content init --output /tmp/hirepaper-candidate.json --force
./hirepaper content lint /tmp/hirepaper-candidate.json
```

If a dedicated development wrapper remains:

```bash
./hirepaper-dev --help
```

The implementing agent should also verify that:

- the packaged binary is named `hirepaper`;
- canonical docs and examples use `hirepaper` consistently;
- README examples match actual runnable commands.
- `.gitignore` covers the main local/generated residue paths introduced by this
  repository’s workflow.

## Expected Verification Outcomes
The implementing agent should confirm:

1. the canonical project name is now `hirepaper`;
2. the executable is `hirepaper`;
3. command help and docs consistently use `hirepaper`;
4. `README.md` exists and is publishable;
5. `project.md` has been improved/split into clearer concerns;
6. `agents.md` is aligned to the new project name and doc structure;
7. `.gitignore` is aligned with publication readiness and repository hygiene;
8. source and packaged command flows remain functional.

## Acceptance Criteria
1. The project is renamed canonically to `hirepaper`.
2. The executable is only `hirepaper`.
3. Public-facing docs no longer use `curriculum-gen` as the canonical name.
4. A top-level `README.md` is added and suitable for GitHub publication.
5. The command surface is documented clearly.
6. `project.md` is improved and split into clearer concerns.
7. `agents.md` is updated to align with the new name and doc structure.
8. `.gitignore` is created or improved to cover generated/local-only residue.
9. Repository residue related to old naming or poor presentation is cleaned up.
10. The change is verified in source mode and packaged mode.
11. A history entry records the rename, documentation decisions, and verification.

## Notes For The Implementing Agent
- Treat this as a publication-readiness task, not a superficial search/replace.
- Optimize for coherence of naming, docs, and entrypoints.
- Keep the final repo understandable to both external GitHub readers and future
  agents working inside the codebase.
- When splitting `project.md`, prefer clearer ownership of concerns over minimal
  diff size.
