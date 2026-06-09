# 028 - Add `content tailor` command

## Status
Planned

## Context
The project already supports:

- canonical candidate JSON loading and rendering;
- candidate-content linting;
- ATS-style vacancy matching through `content match`;
- LLM configuration resolution with command-specific `content_tailor` profile;
- ZIP log persistence with temporary staging and cleanup;
- structured JSON Schema-guided LLM output validation.

`content tailor` still exists only as a connectivity test. That is now the main
remaining product gap.

The command should not become a free-form resume generator. The project’s core
identity is still:

- deterministic local data model;
- ATS-safe PDF generation from structured JSON;
- factual grounding in candidate source data.

For that reason, `content tailor` must produce a valid final `candidate.json`
tailored to a vacancy, but the LLM must not own the final artifact end to end.

The right model is:

1. local code loads the canonical candidate JSON and supporting inputs;
2. the LLM returns a structured tailoring plan and optional controlled rewrites;
3. local code applies those changes deterministically;
4. the command succeeds only if it produces a valid final candidate JSON that
   passes schema/loading and does not fail `content lint`.

## Goal
Implement a production-usable `content tailor` command that:

- reads the canonical candidate JSON;
- reads a raw vacancy `.txt` file;
- optionally reads extra text context files;
- generates a vacancy-tailored final `candidate.json`;
- optionally generates a separate human/machine-readable tailoring report;
- optionally saves a ZIP archive with structured execution logs;
- preserves factual grounding and section semantics;
- fails unless the final tailored JSON is valid and lint-clean enough to ship.

## Product Decision
The primary product of `content tailor` is always a final tailored candidate
JSON artifact.

The command is successful only if it writes a valid final `candidate.json` to
the requested `--output` path.

The report is a secondary artifact:

- shown in the terminal by default;
- optionally saved separately as text or JSON;
- never substituted for the primary tailored JSON output.

## Scope
This task may update:

- `src/curriculum_gen/cli.py`
- `src/curriculum_gen/content_match.py` only for shared helper reuse if needed
- new tailor-specific modules under `src/curriculum_gen/`
- `src/curriculum_gen/loader.py`
- `src/curriculum_gen/content_lint.py`
- `src/curriculum_gen/llm/config.py`
- `src/curriculum_gen/llm/client.py`
- `assets/prompts/`
- `assets/schemas/`
- `project.md`
- `agents.md` if execution guidance needs new examples
- `sdd/history/`

This task may add:

- candidate JSON Schema asset;
- tailoring-plan JSON Schema asset;
- rewrite-response JSON Schema asset;
- tailoring-report JSON Schema asset;
- tailor-specific prompt asset(s);
- local plan-application helpers;
- rewrite helpers for approved fields;
- fixtures for candidate/vacancy/context tailoring flows.

This task should not:

- change the canonical candidate JSON shape;
- change PDF generation rules directly;
- invent unsupported experience, dates, metrics, links, certifications, or
  technologies;
- let the LLM directly emit the final candidate JSON without local assembly and
  validation;
- treat a saved report without a final valid tailored JSON as success.

## Command Surface
Target command shape:

```bash
curriculum-gen content tailor <candidate.json> <vacancy.txt> --output <tailored.json>
```

### Required positional inputs
- `candidate`: path to the canonical candidate JSON
- `vacancy`: path to the raw vacancy description text file

### Required options
- `--output <tailored.json>`
  - required
  - path for the final tailored candidate JSON

### Optional flags and options
- `--config <config.toml>`
  - optional TOML config override
  - otherwise resolve using existing config precedence
- `--locale`, `-l`
  - response/report language
  - default should follow current project conventions
- `--mode conservative|rewrite`
  - default: `conservative`
- `--inference low|medium|high`
  - default: `medium`
- `--extra-context <file>`
  - repeatable
  - additional UTF-8 text sources that may support tailoring decisions
- `--report-output <path>`
  - optional
  - save tailoring report separately
- `--report-format text|json`
  - default: `text`
  - format used only for the optional separate report artifact
- `--log <path>`
  - optional
  - save execution logs as a ZIP archive
- `--prompt <path>`
  - optional plain-text prompt override for the plan stage
- `--timeout-seconds`
  - optional per-run override
- `--max-tokens`
  - optional per-run override
- `--force`
  - allow overwrite of existing output/report/log destinations
- `--quiet`
  - suppress the detailed human-readable terminal report
- `--verbose`, `-v`
  - reuse current verbosity semantics for LLM transport diagnostics if practical

## Output Contract

### Primary output
The command must always produce:

- a final tailored `candidate.json` at `--output`

The command must fail if:

- `--output` is omitted;
- the final JSON cannot be produced;
- the final JSON does not load successfully through the canonical loader;
- the final JSON fails `content lint`.

### Optional report output
The command may also produce:

- a report written to `--report-output` when requested

Report output is never mandatory for success.

### Terminal behavior
By default, terminal output should follow the `content match` style:

- disclaimer;
- mode/inference;
- summary of what changed;
- key rewrites/prioritizations;
- warnings;
- saved artifact paths.

With `--quiet`, suppress only the detailed human-readable report.

`--quiet` must not suppress:

- overwrite prompts;
- critical warnings;
- validation failures;
- confirmation of saved tailored JSON path;
- confirmation of saved report/log paths.

## Overwrite Policy
The command must check all output destinations before any LLM call is made.

Destinations to validate up front:

- `--output`
- `--report-output` when provided
- `--log` when provided

Required behavior:

- if a destination does not exist, continue
- if a destination exists and `--force` is set, continue
- if a destination exists and `--force` is not set:
  - when running in an interactive TTY, prompt the user whether to overwrite
  - when not running in an interactive TTY, fail clearly and exit non-zero

This check must happen before:

- candidate linting;
- extra-context loading;
- any prompt/model call;
- any token-consuming operation.

The command must not spend LLM tokens only to fail on a late overwrite check.

## Input Handling

### 1. Candidate input
The command must:

- load the candidate JSON through the existing loader path;
- fail clearly on missing/invalid input;
- run `content lint` before any tailoring call.

Lint gating:

- lint warnings: continue
- lint failures: abort before tailoring

### 2. Vacancy input
The vacancy is a raw UTF-8 text file.

The command must:

- read it as UTF-8;
- fail on missing/unreadable/empty vacancy input;
- treat it as raw source text, not require any pre-normalized structure.

### 3. Extra context
`--extra-context <file>` may be passed multiple times.

Each extra-context file:

- must be read as UTF-8 text;
- must fail clearly if unreadable or empty;
- is auxiliary context only;
- must be recorded in log metadata and persisted logs.

Grounding policy for extra context:

- `candidate.json` remains the primary canonical source;
- extra context may complement, clarify, or introduce additional candidate facts
  only when the section placement is semantically appropriate and the source is
  explicit;
- extra context must not outrank contradictory canonical candidate JSON data;
- any final tailored content that depends materially on extra context must
  record explicit grounding to the relevant context source.

Examples:

- a project `README.md` may support content in `projects`
- a published technical article may support a project, summary, or links section
- an extra-context file must not silently create unsupported work experience
  entries without grounded rationale

## Tailoring Modes

### `conservative`
`conservative` is the default.

Allowed behaviors:

- reorder sections/items;
- keep/remove optional content;
- prioritize skills/projects/experience;
- rewrite `headline`, `summary`, and `target_role` conservatively based on
  existing grounded content;
- perform lexical tightening or vacancy-specific phrasing without broad factual
  expansion.

Not allowed:

- broad semantic rewrites that substantially reframe unsupported claims;
- new bullets built from speculative extrapolation;
- unsupported technology/category expansion.

### `rewrite`
`rewrite` may:

- do everything `conservative` can do;
- rewrite existing bullets;
- merge multiple grounded bullets into one (`N:1`);
- rewrite `headline`, `summary`, and `target_role` more aggressively;
- generalize phrasing when supported by explicit evidence plus permitted
  inference level.

Not allowed:

- splitting one grounded bullet into multiple bullets (`1:N`);
- inventing new factual claims;
- inventing metrics, dates, scopes, tools, employers, certifications, links, or
  roles.

## Inference Policy
`--inference` controls semantic extrapolation, not the shape of transformation.

Recommended semantics:

- `low`
  - near-literal wording
  - minimal equivalence
- `medium`
  - common technical equivalence allowed when justified
- `high`
  - broader semantic reframing allowed, but still grounded and explainable

Mode/inference interaction:

- `mode` controls whether the command may rewrite content and how broadly
- `inference` controls how much semantic equivalence the LLM may use while
  planning or rewriting

Any final rewritten text must remain explainable through stored grounding.

## Required Local/LLM Architecture
Use a structured hybrid flow rather than direct free-form final JSON generation.

Minimum architecture:

1. validate output destinations
2. load candidate JSON
3. run input lint gate
4. load vacancy text
5. load extra-context text files
6. build structured candidate payload with stable local IDs
7. load candidate JSON Schema
8. load tailoring-plan JSON Schema
9. load rewrite-response JSON Schema
10. request structured tailoring plan from LLM
11. validate tailoring plan locally
12. apply structural plan locally
13. if `mode=rewrite`, request focused rewrites only for approved fields/items
14. validate rewrite response locally against the rewrite schema
15. assemble final tailored candidate JSON locally
16. validate final tailored candidate JSON through the canonical loader/schema
17. run `content lint` on the final tailored candidate
18. render terminal report and optional report artifact
19. save ZIP logs when requested

The final tailored JSON must be assembled by local code.

The LLM must not be treated as the sole owner of the final artifact.

## Candidate Schema Requirement
The project must add and use a versioned JSON Schema for the canonical candidate
format.

That schema must be:

- provided explicitly to the LLM during tailoring;
- used locally to validate plan application outcomes when practical;
- consistent with the existing canonical loader/data model.

Important:

- the candidate schema must describe what the current loader/model actually
  accepts, not a stricter idealized format;
- fields accepted as absent or nullable by the canonical loader/model must not
  be made artificially required/non-nullable in the schema;
- final runtime success is still decided by the loader plus lint, but schema
  validation must not reject candidate payloads that the canonical loader would
  accept.

This schema does not replace the loader. The loader remains the runtime contract
enforcer.

## Tailoring Plan Requirement
The first model call must return a structured tailoring plan rather than a final
candidate JSON blob.

The plan should use stable references/IDs instead of unstructured prose.

Minimum plan responsibilities:

- decide what to keep/remove/reorder;
- decide which sections to emphasize;
- decide whether optional sections should be omitted;
- propose approved rewrite targets;
- identify grounding and confidence;
- identify when extra-context was used materially.

The plan must be validated against a JSON Schema.

## Rewrite Response Requirement
If `mode=rewrite`, the rewrite stage must also return a structured response
validated against its own JSON Schema.

That schema must define:

- which rewrite request each response item satisfies;
- the rewritten text payload;
- the operation shape (`1:1` or `N:1`);
- explicit grounding references;
- confidence;
- optional warnings or cautions.

The implementation must not treat rewrite-stage output as valid solely because a
request succeeded transport-wise. Local schema validation is mandatory.

## Stable ID Requirement
The candidate payload sent to the LLM must include stable IDs for mutable items.

Examples:

- experience items
- achievements/highlights
- projects
- project highlights
- skill categories
- individual skill items
- certifications
- awards
- volunteer entries
- languages
- personal links / extra links

The purpose is to let the LLM return actions like:

- keep/remove
- reorder
- prioritize
- rewrite approved item
- merge multiple grounded items

without asking the local code to diff fuzzy text strings.

## Rewrite Policy

### Approved rewrite targets
At minimum, the system may rewrite:

- `personal.headline`
- `summary`
- `target_role`
- experience bullets/highlights/achievement-derived bullets
- project descriptions
- project highlights

Only in ways permitted by `mode` and `inference`.

### Not allowed to change factually
The system must not invent or silently alter:

- employers
- job titles not supported by the source
- dates
- certifications
- credential URLs
- metrics
- technologies
- links
- degrees/institutions
- locations
- scope/seniority beyond supported evidence

### `N:1` bullet merges
In `rewrite`, multiple grounded bullets may be merged into a single bullet when:

- the resulting bullet is supported by all referenced items;
- no factual loss or unsupported expansion occurs;
- grounding references are retained in the report/log output.

`1:N` bullet expansion is out of scope for this task.

## Section Rules

The tailored final JSON may:

- remove optional sections entirely;
- reduce entries inside optional sections;
- reorder prioritized projects/experience entries;
- suppress lower-value optional content for the vacancy.

The final result must still remain a valid candidate JSON according to the
canonical schema.

The LLM may decide optional-section removal, but the decision must be visible in
the report/log output.

## Report Requirements
The tailoring report is a separate artifact from the final candidate JSON.

### Report JSON
Add a dedicated report schema. It should be similar in tone to `content match`,
but focused on transformation rather than evaluation.

Minimum required content:

- disclaimer
- mode
- inference
- summary
- target role summary
- key changes
- rewritten items
- removed/deprioritized sections
- grounding notes
- lint status before
- lint status after
- warnings

### Human-readable report
The default terminal report should render:

1. disclaimer
2. mode / inference
3. executive summary
4. key structural changes
5. rewrite summary
6. removed/deprioritized content
7. lint before/after summary
8. warnings

The terminal report should not dump full raw lint output by default.

### Lint reporting
Do not render the full lint transcript in the human-readable report by default.

Instead:

- show summarized status/counts in terminal/report text;
- include compact warning/failure summaries in the structured report so the
  counts remain interpretable;
- keep detailed lint artifacts in JSON/log output.

## Disclaimer Requirement
Like `content match`, `content tailor` must include a disclaimer in the report
that the workflow uses an LLM and may contain subjective or imperfect judgment.

The disclaimer belongs in:

- terminal report
- JSON/text report artifact
- logs if the report is persisted there

The disclaimer does not belong inside the final tailored candidate JSON.

## Validation Requirements

### Final JSON validation
The command succeeds only if the final tailored JSON:

- loads through the canonical loader;
- conforms to the candidate schema/loader expectations;
- does not fail `content lint`.

### Final lint gating
Required final behavior:

- lint `pass`: succeed
- lint `warning`: succeed with visible warning summary
- lint `fail`: fail command

The command must not write a success message for a final candidate JSON that
fails lint.

## Logging Requirements
When `--log <path>` is provided, save a ZIP archive using the shared temporary
staging lifecycle used by other commands.

Minimum required log contents:

- `meta.json`
- candidate input payload
- vacancy text
- extra-context files or normalized copies
- candidate schema
- tailoring-plan schema
- rewrite-response schema
- tailoring report schema
- prompt(s)
- tailoring plan raw response
- validated tailoring plan
- rewrite request/response artifacts when `mode=rewrite`
- final tailored candidate JSON
- report artifact when generated
- summarized lint before/after

### Log metadata
`meta.json` should include at minimum:

- `command`
- `timestamp_utc`
- `candidate_path`
- `vacancy_path`
- `extra_context_paths`
- `output_path`
- `report_output_path`
- `report_format`
- `log_path`
- `mode`
- `inference`
- `locale`
- `model`
- `base_url`
- `timeout_seconds`
- `max_tokens`
- `lint_status_before`
- `lint_status_after`
- `tailoring_status`
- `rewrite_stage_used`

## Error Handling
The command must fail clearly on:

- missing/invalid candidate input
- missing/unreadable/empty vacancy input
- missing/unreadable/empty extra-context input
- unsupported report format
- output/report/log path conflicts without `--force` approval
- prompt file read failure
- LLM request failure
- invalid tailoring-plan response
- invalid rewrite response
- final candidate JSON assembly failure
- final candidate JSON validation failure
- final candidate JSON lint failure
- report write failure
- log archive creation failure

## Recommended Implementation Direction

### Reuse from `content match`
Prefer reusing:

- LLM config resolution
- prompt loading
- ZIP log staging
- local schema validation helpers
- text/json report rendering conventions where practical

### Keep logic separated
Recommended module boundaries:

- `content_tailor.py` for orchestration
- helper(s) for candidate payload normalization with stable IDs
- helper(s) for local plan application
- helper(s) for rewrite application
- helper(s) for tailoring report rendering

Avoid mixing all tailoring logic directly into CLI command wiring.

## Documentation Expectations
This task should update:

- `project.md`
- `agents.md` command examples if needed
- any stale docs that still call `content tailor` a connectivity test

## Acceptance Criteria
This task is complete only if:

1. `curriculum-gen content tailor <candidate.json> <vacancy.txt> --output <tailored.json>` exists.
2. `--output` is mandatory and is treated as the primary product path.
3. `--report-output` and `--report-format text|json` exist as separate report controls.
4. `--extra-context <file>` is supported as a repeatable option.
5. `--mode conservative|rewrite` is supported.
6. overwrite checks occur before any LLM call.
7. the command uses a structured tailoring plan, not direct free-form final JSON generation.
8. the command uses the candidate JSON Schema in prompt context and local validation.
9. the command uses a dedicated rewrite-response schema when `mode=rewrite`.
10. the final tailored JSON is assembled locally and validated locally.
11. the command fails if the final tailored JSON is invalid.
12. the command fails if the final tailored JSON fails lint.
13. lint warnings do not block success.
14. `--quiet` suppresses only the detailed terminal report, not critical messages.
15. `--log` persists a ZIP archive with staged cleanup and tailor-specific artifacts.
16. source and packaged command execution both preserve the behavior above.

## Suggested Verification
Minimum verification for the eventual implementation:

```bash
./curriculum-gen-dev content tailor --help
./curriculum-gen-dev content tailor data/candidate.json data/vacancy.txt --output output/tailored.json
./curriculum-gen-dev content lint output/tailored.json
.venv/bin/python build.py
./curriculum-gen content tailor --help
./curriculum-gen content tailor data/candidate.json data/vacancy.txt --output output/tailored-packaged.json
./curriculum-gen content lint output/tailored-packaged.json
```

Additional recommended verification:

```bash
./curriculum-gen-dev content tailor data/candidate.json data/vacancy.txt \
  --output output/tailored.json \
  --report-output output/tailor-report.txt \
  --report-format text \
  --log output/tailor-log.zip

./curriculum-gen-dev content tailor data/candidate.json data/vacancy.txt \
  --output output/tailored-rewrite.json \
  --mode rewrite \
  --report-output output/tailor-report.json \
  --report-format json \
  --extra-context README.md
```
