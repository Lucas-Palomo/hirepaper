# 016 - Agent instruction consolidation

**Date:** 2026-05-29
**Agent:** Codex

---

## Context

The project had two older support files, `sdd/agent.md` and
`sdd/agent-context.md`, with instructions from the initial project phase. Those
files still described the agent as if it were creating the first implementation,
which no longer matched the current state of the codebase.

The project also now has two root-level entry points:
- `./curriculum-gen-dev` for source-based development and testing;
- `./curriculum-gen` for the packaged binary under `dist/curriculum-gen`.

## Changes

- Added root-level `agents.md` as the canonical instruction file for future
  agents.
- Added root-level `project.md` with technical project context, layout flow,
  density behavior, ATS validation expectations, and packaging notes.
- Removed stale `sdd/agent.md` and `sdd/agent-context.md` to avoid conflicting
  instructions.
- Documented the required per-task workflow:
  - inspect backlog and current implementation;
  - implement the scoped change;
  - run a focused test;
  - rebuild the packaged binary;
  - smoke-test the relevant entry point;
  - document completed work and decisions in `sdd/history/`.
- Added a verification rule for layout and density tasks requiring PDF-to-image
  rendering for visual inspection alongside ATS validation.
- Documented the two entry points and their intended use.
- Documented the build command as `.venv/bin/python build.py`, matching the
  current environment where `PyInstaller` is installed in `.venv`.

## Verification

```bash
./curriculum-gen-dev --help
.venv/bin/python build.py
./curriculum-gen --help
```

Results:
- development entry point help rendered successfully;
- packaged binary rebuilt successfully at `dist/curriculum-gen`;
- packaged entry point help rendered successfully.

## Notes

`python3 build.py` was not used as the documented command because the global
Python environment did not have `PyInstaller` installed. The project-local
virtual environment did.
