# 022 - Rename `ssd/` to `sdd/` and align project documentation

**Date:** 2026-06-05
**Agent:** Codex GPT-5.4

---

## Context

The project follows a Spec Driven Development workflow, but the repository used
`ssd/` as the directory name for backlog and history artifacts. That naming was
inconsistent with the intended methodology and leaked into root instructions and
historical task references.

## Changes

- Renamed the repository workstream directory from `ssd/` to `sdd/`.
- Updated root documentation in `agents.md` to reference `sdd/backlog/` and
  `sdd/history/`.
- Updated technical context in `project.md` to reference `sdd/` paths.
- Updated backlog and history documents that still pointed to `ssd/` so future
  agents follow the canonical `sdd/` structure.
- Added backlog task `022` documenting the rename and alignment work.

## Decisions and Tradeoffs

- Historical documents were updated to use current repository paths instead of
  preserving obsolete `ssd/` path strings. This keeps the repo operationally
  consistent for future agents at the cost of slightly normalizing older prose.
- The change was scoped to documentation and repository structure only. Runtime
  code paths and CLI behavior were intentionally left untouched.

## Verification

```bash
find sdd -maxdepth 2 -type d | sort
rg -n "ssd/|\\bssd\\b" agents.md project.md sdd \
  -g '!sdd/backlog/022-rename-ssd-to-sdd-and-align-docs.md' \
  -g '!sdd/history/022-rename-ssd-to-sdd-and-align-docs.md'
```

Results:
- `sdd/backlog/` and `sdd/history/` exist.
- No remaining `ssd/` references were found in active repository
  documentation after excluding this task record and its history entry, which
  intentionally mention the old directory name for traceability.

## Residual Risks

- External notes, unpublished prompts, or local tooling outside the repository
  may still refer to `ssd/` and will need manual alignment if they are used.
