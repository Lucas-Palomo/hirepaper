# 018 - Redesign CLI subcommands for content and PDF workflows

**Date:** 2026-05-30
**Agent:** opencode (deepseek-v4-flash)

## Context
The CLI had grown flat top-level commands (`generate`, `doctor`, `ats-check`, `lint-content`) without a coherent organizational structure. As the product expands into content analysis (lint, match, tailor) alongside PDF operations, the flat model was becoming inconsistent and harder to teach.

## Changes Made

### Refactored: `src/curriculum_gen/cli.py`

**New subcommand structure:**

```
curriculum-gen doctor
curriculum-gen content lint <candidate_json>
curriculum-gen content match ...     (not yet implemented)
curriculum-gen content tailor ...    (not yet implemented)
curriculum-gen pdf generate <candidate_json> --output <pdf>
curriculum-gen pdf check <pdf>
```

**Implementation details:**
- Created two nested Typer apps: `content_app` and `pdf_app`, added to the main `app` via `app.add_typer()`.
- Extracted shared command logic into `_cmd_generate()`, `_cmd_pdf_check()`, and `_cmd_content_lint()` so the grouped CLI commands stay thin and consistent.
- `doctor` remains a top-level command unchanged.
- `content match` and `content tailor` are exposed as stubs that print `"Error: 'content ...' is not yet implemented"` and exit with code 1.

### Updated: `project.md`
- Added canonical CLI structure documentation.
- Updated the cli.py description to reflect the subcommand groups.

### Updated: `agents.md`
- Replaced old flat command examples with new subcommand form:
  - `generate` → `pdf generate`
  - `ats-check` → `pdf check`
  - Added `content lint` examples.
- Updated validation expectations section with new command names.

## Decisions & Tradeoffs
- **Extracted shared logic** rather than duplicating it — `pdf generate`, `pdf check`, and `content lint` each call explicit shared helpers. This keeps behavior consistent without carrying old flat commands forward.
- **Legacy commands removed** — The CLI has not been officially released, so no backward compatibility is needed. Old flat commands were dropped entirely to keep the surface clean.
- **Groups show help on empty invocation** — `content` and `pdf` subcommand groups use `invoke_without_command=True` with a callback that prints group help when no subcommand is given, instead of a cryptic "Missing command" error.
- **Top-level app shows help on empty invocation** — Same pattern applied to the main `app` so `curriculum-gen` without arguments shows help (exit 0) instead of "Missing command" (exit 2).
- **`content match`/`tailor` exposed as stubs** — Included with explicit error messages so the CLI structure is obvious before those features land. Users who try them get a clear, non-zero exit.

## Verification

### New subcommands
```
$ ./curriculum-gen-dev content lint data/candidate.json
→ PASS with warnings

$ ./curriculum-gen-dev pdf generate data/candidate.json -o /tmp/test.pdf
→ Generated: /tmp/test.pdf

$ ./curriculum-gen-dev pdf check /tmp/test.pdf
→ PASS (15 checks passed)

$ ./curriculum-gen-dev doctor
→ All checks passed.
```

### Not-implemented stubs
```
$ ./curriculum-gen-dev content match
→ Error: 'content match' is not yet implemented (exit code 1)

$ ./curriculum-gen-dev content tailor
→ Error: 'content tailor' is not yet implemented (exit code 1)
```

### Packaged binary
```
$ ./curriculum-gen --help             # shows only doctor, content, pdf
$ ./curriculum-gen content --help     # shows group help
$ ./curriculum-gen pdf --help         # shows group help
$ ./curriculum-gen content lint data/candidate.json   # works
$ ./curriculum-gen pdf generate data/candidate.json -o /tmp/test.pdf   # works
$ ./curriculum-gen pdf check /tmp/test.pdf   # works
$ ./curriculum-gen doctor             # works
```

### Removed flat commands
```
$ ./curriculum-gen-dev generate --help
→ No such command 'generate'. (exit code 2)

$ ./curriculum-gen-dev ats-check --help
→ No such command 'ats-check'. (exit code 2)
```

### Help without arguments
Every command (except `doctor`) shows its help when called without required arguments, including the top-level entrypoint:
```
$ ./curriculum-gen                    → shows top-level help (exit 0)
$ ./curriculum-gen pdf generate       → shows help (exit 0)
$ ./curriculum-gen pdf check          → shows help (exit 0)
$ ./curriculum-gen content lint       → shows help (exit 0)
$ ./curriculum-gen content            → shows content group help (exit 0)
$ ./curriculum-gen pdf                → shows pdf group help (exit 0)
$ ./curriculum-gen doctor             → runs normally (exit 0)
```

## Residual Risks
- Future tasks that add `content match`/`tailor` must replace the stub implementations with real logic.

## Follow-up Items
- Implement `content match` and `content tailor` as separate tasks.
