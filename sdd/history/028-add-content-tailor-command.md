# 028 - Add `content tailor` command

**Date:** 2026-06-06
**Agent:** Codex GPT-5.4 + opencode (deepseek-v4-flash)

---

## Context

`content tailor` existed only as a connectivity test (`_run_content_hello`)
that verified the LiteLLM proxy could reach the configured model. There was
no real tailoring logic: no candidate loading, no vacancy-aware analysis,
no structured plan, no JSON output, no rewrite stage, and no report.

The task was to implement a production-usable `content tailor` command that:

- reads the canonical candidate JSON and a raw vacancy `.txt` file;
- optionally reads extra-context text files;
- uses a structured LLM-driven tailoring plan with stable IDs;
- applies the plan locally to produce a valid tailored `candidate.json`;
- optionally rewrites approved fields when `--mode=rewrite`;
- validates the final JSON through the canonical loader and `content lint`;
- renders a human-readable or JSON report;
- persists a ZIP log archive when requested.

## Changes

### Added: `assets/prompts/content-tailor-default.txt`

Default prompt for the tailoring plan stage. Instructs the LLM to:

- produce a structured plan referencing stable IDs;
- respect mode (conservative/rewrite) and inference (low/medium/high);
- ground every decision in source evidence;
- never invent facts, dates, metrics, technologies, or credentials.

### Added: `src/curriculum_gen/content_tailor.py`

New module (~700 lines) containing:

- **`_build_candidate_payload_with_ids()`**: transforms the canonical
  `Candidate` dataclass into a dict with stable IDs on every mutable item
  (experience entries, highlights, achievements, projects, project highlights,
  skill categories, skill items, certifications, awards, volunteer entries,
  languages, links, extra-links).

- **Schema loading helpers**: `load_candidate_schema()`,
  `load_tailor_plan_schema()`, `load_tailor_report_schema()`.

- **Prompt loading**: `load_default_tailor_prompt()`, `load_prompt()`.

- **Plan message builder**: `build_plan_messages()` constructs the system and
  user messages, embedding the stable-ID payload, vacancy text, candidate
  schema, tailor plan schema, and optional extra contexts.

- **Plan validation**: `_validate_against_schema()`, `_validate_plan()`,
  `parse_and_validate_response()` — reusable JSON Schema validation with
  support for `$ref`, enums, minLength, minItems, additionalProperties, and
  nested objects/arrays.

- **Structural plan application**: `_apply_structural_actions()` handles
  `keep`, `remove`, `reorder`, `prioritize`, `deprioritize`, `replace_items`
  across all target kinds (experience entries, project entries, skill
  categories, skill items, certifications, awards, volunteer, languages,
  links, sections).

- **Rewrite stage**: `_build_rewrite_messages()`, `_apply_rewrite_to_payload()`,
  `_apply_experience_rewrite()`, `_apply_project_rewrite()` — focused per-item
  rewrite calls to the LLM for `mode=rewrite`, with result application.

- **Payload-to-JSON conversion**: `_convert_payload_to_candidate_json()` and
  helpers (`_convert_experience_list`, `_convert_skills`, etc.) strip IDs and
  produce canonical candidate JSON dicts.

- **Report generation**: `_build_report_data()`, `render_text_report()`,
  `render_json_report()` produce human-readable or JSON tailoring reports.

- **Log archiving**: `save_tailor_log_zip()` uses the shared
  `StagedLogArchive` lifecycle to persist candidate input, vacancy text,
  extra contexts, schemas, prompts, raw/validated plan, rewrite responses,
  final JSON, report, and lint summaries.

- **Main orchestration**: `run_tailor()` implements the full 17-step flow
  (destination validation, input loading, lint gate, plan generation, plan
  validation, structural application, rewrite stage, final assembly, loader
  validation, lint gate after, output write, report render, log archive).

- **Rewrite gating fix**: `headline`, `summary`, and `target_role` rewrites
  are now processed in both `conservative` and `rewrite` modes. Bullet-level
  rewrites still require `--mode=rewrite`.

### Added: `assets/schemas/content-tailor-rewrite-response.schema.json`

New JSON Schema defining the structured format for rewrite-stage LLM responses.
Required fields: `request_refs`, `target_refs`, `operation` (`1_to_1`/`n_to_1`),
`rewrites` (map of ref→new text), `grounding` (array of source refs), `confidence`.
Optional field: `warnings`.

### Modified: `src/curriculum_gen/content_tailor.py`

- Added `load_rewrite_response_schema()` to load the rewrite-response schema.
- Added `_validate_rewrite_response()` and `parse_and_validate_rewrite_response()`
  — validates the LLM rewrite output against the schema before applying it.
- Updated `_build_rewrite_messages()` to include the rewrite-response schema in
  the prompt so the LLM produces the correct structured format.
- Updated the rewrite processing loop in `run_tailor()` to validate each rewrite
  response through `parse_and_validate_rewrite_response()` instead of a bare
  `json.loads`. Truncated (`finish_reason=length`) rewrite responses now raise a
  clear error instead of silently producing empty text.
- Updated `save_tailor_log_zip()` to include `rewrite-response-schema.json` in
  the log archive.

### Follow-up fixes after review (batch 2)

After a live test with `./config.toml`, the LLM returned a rewrite response
with `target_refs` that did not match the active rewrite request. Two changes:

- **Prompt clarification**: `_build_rewrite_messages()` now includes
  `Target refs to rewrite: ["..."]` and `Expected operation: 1_to_1` as
  explicit lines in the user message, so the LLM has a concrete JSON snippet
  to mirror in its response's `target_refs` and `operation` fields.

- **Better validation diagnostics**: `_validate_rewrite_response()` now
  reports the exact mismatch in its error message:
  ```
  rewrite response: 'target_refs' mismatch —
  expected ['headline'], got ['wrong_ref']
  ```

### Follow-up fixes after review (batch 3)

Running `--mode rewrite --inference high` crashed on `_extract_text()` in
`client.py:111` because `finish_reason` was checked *after* extracting text,
and some providers return `content=None` + `finish_reason=length` simultaneously.

Both the plan stage and the rewrite stage in `run_tailor()` were fixed:

- `finish_reason` is now read **before** `_extract_text()`.
- `_extract_text()` is wrapped in a `try/except LLMClientError`:
  - if `finish_reason == "length"`, the empty-text error is silently swallowed
    and the existing truncation error fires with whatever partial text was available;
  - otherwise, the `LLMClientError` is converted to `ContentTailorError` with
    a descriptive message including the rewrite request context (target_kind, refs).

### Follow-up fixes after review (batch 4)

After fixing the crash order, `--mode rewrite --inference high` still failed
because the plan JSON was consistently truncated (`finish_reason=length`).
The plan stage with rewrite+high generates a much larger JSON (structural
actions + rewrite requests for all bullets + grounding notes + section
decisions), and 16384 output tokens was insufficient.

Changes:

- The plan stage now uses its own `plan_effective_config` with a minimum of
  **32768 max_tokens** and **120s timeout**, regardless of the profile base.
  The rewrite stage continues to use the user/profile `max_tokens`.
- `assets/config/config.toml.example` updated to suggest `max_tokens = 32768`
  for the `[llm.content_tailor]` profile.

After the initial delivery, a review found three contract gaps and two runtime
validation failures during manual testing. The implementation was tightened in
place without changing the command surface.

- **Final candidate schema validation**: the final tailored JSON is now validated
  against `candidate.schema.json` before the canonical `load_candidate()` pass.
  This closes the gap where only the loader contract was enforced.

- **Report schema validation**: report generation now validates the final report
  payload against `content-tailor-report.schema.json` before writing terminal,
  file, or log artifacts.

- **Lint summary enrichment**: lint summaries now include
  `warning_summaries` and `failure_summaries`, matching the report schema
  instead of emitting count-only summaries that were schema-incomplete.

- **Rewrite response validation hardening**:
  - keeps strict validation for `operation`;
  - keeps strict validation for the effective rewrite targets;
  - validates `rewrites` cardinality according to the operation:
    `1_to_1` must rewrite every target ref, `n_to_1` must emit exactly one
    rewritten entry;
  - stops incorrectly requiring `request_refs == target_refs`, because
    `request_refs` may legitimately include supporting refs used as rewrite
    basis.

- **Conservative-mode rewrite application fix**: `headline`, `summary`, and
  `target_role` rewrites are now applied by target kind, which fixes the case
  where the plan correctly requested a conservative rewrite but the output JSON
  preserved the original field.

- **Schema metadata stripping for LLM output**:
  - plan and rewrite responses now strip top-level `$schema`, `$id`, and
    `title` before validation;
  - the prompt now sends a cleaned LLM-facing schema for the plan and rewrite
    stages, omitting those metadata fields to reduce model echo and prevent
    false `additionalProperties` failures such as:
    `plan does not match schema at '$id': additional properties are not allowed`.

- **Observed live-test behavior with environment config**:
  - command used:
    `./curriculum-gen-dev content tailor data/candidate.json data/vacancy.txt --output output/candidate-test.json --log output/content-tailor-debug.zip --force`
  - after the schema-metadata fix, the previously reported `$id` validation
    failure was no longer reproducible locally;
  - the live run then failed earlier at the provider boundary with:
    `LLM plan request failed: ... OpenAIException - Connection error`
  - because of that external connection failure, end-to-end confirmation against
    a live model remains pending even though local syntax and validation paths
    were updated successfully.

### Modified: `src/curriculum_gen/cli.py`

- Replaced the `content_tailor` connectivity-test stub with the full
  command supporting 16 CLI options:

  | Option | Type | Default | Description |
  |--------|------|---------|-------------|
  | `candidate` | positional | required | Candidate JSON |
  | `vacancy` | positional | required | Vacancy text |
  | `--output` | required | — | Final tailored candidate JSON |
  | `--config` | optional | — | TOML config override |
  | `--locale / -l` | optional | `en` | Response/report locale |
  | `--mode` | optional | `conservative` | conservative or rewrite |
  | `--inference` | optional | `medium` | low, medium, high |
  | `--extra-context` | repeatable | — | Extra text sources |
  | `--report-output` | optional | — | Separate report artifact |
  | `--report-format` | optional | `text` | text or json |
  | `--log` | optional | — | ZIP log archive |
  | `--prompt` | optional | — | Custom plan prompt |
  | `--timeout-seconds` | optional | profile value | Per-run timeout |
  | `--max-tokens` | optional | profile value | Per-run token limit |
  | `--force` | flag | — | Overwrite destinations |
  | `--quiet` | flag | — | Suppress terminal report |
  | `--verbose / -v` | count | 0 | LLM transport diagnostics |

- Added overwrite policy: checks all destinations before any LLM call,
  prompts interactively in TTY, fails clearly in non-TTY without `--force`.

- Terminal output follows `content match` style: disclaimer, mode/inference,
  executive summary, key changes, rewrites, section decisions, lint before/after,
  warnings, saved artifact paths.

### Modified: `project.md`

- Updated `content tailor` from "connectivity test" to full command
  documentation with all options.
- Added `content_tailor.py` to the source layout description.
- Updated the CLI structure block to show the full command shape.

## Decisions and Tradeoffs

- **Structured hybrid flow over free-form generation**: The LLM returns a
  plan with stable IDs; local code applies structural changes and assembles
  the final JSON. This keeps the LLM as a planning advisor rather than the
  sole owner of the final artifact.

- **Stable IDs instead of fuzzy text diff**: Every mutable item gets a
  deterministic ID (`exp_0`, `exp_0_hl_1`, `proj_2_desc`, etc.) so the
  LLM can reference items precisely without text matching.

- **Two-stage LLM for rewrite mode**: The plan stage decides what to rewrite;
  a separate focused LLM call per rewrite request applies the actual text
  transformation. This separates planning from generation for auditability.

- **Separate validation before and after**: Both the plan and the final JSON
  are validated against schemas; the final JSON also passes through the
  canonical `load_candidate()` and `lint_candidate()`.

- **Overwrite check before any LLM call**: All output destinations are
  validated upfront to avoid spending tokens only to fail on a late file
  conflict.

- **Reused patterns from `content_match`**: LLM config resolution, spinner,
  spinner thread pattern, `_build_effective_config()`, `_strip_json_fence()`,
  schema validation pattern, `StagedLogArchive` lifecycle, and disclaimer
  locale handling.

### Fixed: Rewrite stage gated only behind `--mode=rewrite`

The initial implementation only processed `rewrite_requests` from the plan when
`mode == "rewrite"`. However, `headline`, `summary`, and `target_role` are
approved rewrite targets even in `conservative` mode. The plan's
`rewrite_requests` array is the only mechanism for requesting these rewrites,
so skipping the rewrite stage entirely in conservative mode meant LLM-proposed
headline/summary/target_role changes were silently ignored.

**Fix in `src/curriculum_gen/content_tailor.py`** (`run_tailor`):

- Separates `rewrite_requests` into two groups:
  - `always_rewrites`: `headline`, `summary`, `target_role` — processed
    regardless of mode (conservative or rewrite)
  - `mode_rewrites`: all other target kinds — processed only in rewrite mode
- The `--mode` flag still controls whether bullet-level rewrites
  (`experience_bullet`, `project_description`, `project_bullet`) are executed,
  matching the intended conservative/rewrite semantics.

## Acceptance Criteria Status

| # | Criterion | Status |
|---|-----------|--------|
| 1 | `content tailor <candidate.json> <vacancy.txt> --output <tailored.json>` exists | ✅ |
| 2 | `--output` is mandatory and is the primary product path | ✅ |
| 3 | `--report-output` and `--report-format text\|json` exist | ✅ |
| 4 | `--extra-context <file>` is repeatable | ✅ |
| 5 | `--mode conservative\|rewrite` is supported | ✅ |
| 6 | Overwrite checks occur before any LLM call | ✅ |
| 7 | Uses structured tailoring plan, not free-form JSON generation | ✅ |
| 8 | Uses candidate JSON Schema in prompt context and local validation | ✅ |
| 9 | Uses dedicated rewrite-response schema when `mode=rewrite` | ✅ |
| 10 | Final tailored JSON assembled locally and validated locally | ✅ |
| 11 | Fails if final tailored JSON is invalid | ✅ |
| 12 | Fails if final tailored JSON fails lint | ✅ |
| 13 | Lint warnings do not block success | ✅ |
| 14 | `--quiet` suppresses only the detailed terminal report | ✅ |
| 15 | `--log` persists a ZIP archive with staged cleanup and tailor-specific artifacts | ✅ |
| 16 | Final tailored JSON is validated against `candidate.schema.json` and `load_candidate()` | ✅ |
| 17 | Report payload is validated against `content-tailor-report.schema.json` | ✅ |
| 18 | Rewrite response validation enforces operation/cardinality without assuming `request_refs == target_refs` | ✅ |
| 19 | Plan/rewrite validation tolerates echoed schema metadata (`$id`, `$schema`, `title`) | ✅ |

## Verification

```bash
python3 -m py_compile src/curriculum_gen/*.py src/curriculum_gen/llm/*.py
./curriculum-gen-dev content tailor --help
python3 -m py_compile src/curriculum_gen/content_tailor.py
./curriculum-gen-dev content tailor data/candidate.json data/vacancy.txt --output output/candidate-test.json --log output/content-tailor-debug.zip --force
```

### Results

- `py_compile` passed.
- `content tailor --help` shows the full command surface with all options.
- `python3 -m py_compile src/curriculum_gen/content_tailor.py` passed after the
  follow-up validation fixes.
- Live execution with the local environment config reached the LLM boundary but
  failed with provider connection error, so end-to-end model validation is still
  pending.

## Residual Risks

- The command has not been smoke-tested against a live LLM endpoint — plan generation
  and rewrite stages depend on the configured model's ability to produce valid
  plan JSON. Current local reproduction is blocked by provider connection error,
  not by a deterministic local parsing failure.
- The `replace_items` action type for skill categories/items uses `replacement_refs`
  that must reference existing IDs; items from extra context are not automatically
  assigned IDs in the current implementation.
- Extra-context files are passed to the LLM as plain text but are not indexed or
  pre-processed; very large extra contexts may increase token consumption.
- The spinner thread pattern is duplicated between `run_tailor` and `run_match`;
  a future refactor could extract the spinner into a shared utility.
- Rewrite-response schema validation only applies during the rewrite stage; if the
  rewrite stage is not triggered (no rewrite_requests in plan), no rewrite-response
  validation occurs. This is correct by design.
- The rewrite-response schema is loaded unconditionally even when `mode=conservative`;
  the load is cheap and ensures it is available for log archives if needed.
