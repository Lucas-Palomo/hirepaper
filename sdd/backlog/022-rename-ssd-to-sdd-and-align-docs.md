# 022 - Rename `ssd/` to `sdd/` and align project documentation

## Status
Completed

## Context
The project follows a Spec Driven Development workflow, but the working
artifact directory was named `ssd/` instead of `sdd/`.

That mismatch creates unnecessary ambiguity in agent instructions,
project documentation, and task references. The repository should use one
canonical directory name that matches the intended methodology.

## Goal
Rename the project workstream directory from `ssd/` to `sdd/` and update
all internal references so backlog, history, and agent guidance use the
same term consistently.

## Scope
This task may update:
- `agents.md`
- `project.md`
- `sdd/backlog/`
- `sdd/history/`
- any repo documentation that still references `ssd/`

This task should not:
- change runtime CLI behavior;
- change PDF generation behavior;
- change ATS validation behavior;
- change packaging behavior.

## Required Behavior
- The canonical backlog directory must be `sdd/backlog/`.
- The canonical history directory must be `sdd/history/`.
- Root instructions must reference `sdd/` consistently.
- Historical and backlog documents should not point future agents to the old
  `ssd/` path.

## Acceptance Criteria
1. The repository contains `sdd/backlog/` and `sdd/history/`.
2. The old `ssd/` directory no longer exists.
3. `agents.md` references `sdd/backlog/` and `sdd/history/`.
4. `project.md` references `sdd/backlog/` and `sdd/history/`.
5. No active repository documentation points future work to `ssd/`.
6. The change is recorded in `sdd/history/022-rename-ssd-to-sdd-and-align-docs.md`.

## Verification
```bash
find sdd -maxdepth 2 -type d | sort
rg -n "ssd/|\\bssd\\b" agents.md project.md sdd \
  -g '!sdd/backlog/022-rename-ssd-to-sdd-and-align-docs.md' \
  -g '!sdd/history/022-rename-ssd-to-sdd-and-align-docs.md'
```

## Completion Record
Completed in `sdd/history/022-rename-ssd-to-sdd-and-align-docs.md`.
