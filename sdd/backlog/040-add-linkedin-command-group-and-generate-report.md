# 040 - Add `linkedin` command group and `linkedin generate` report workflow

## Status
Completed

## Context
The project already has a clear core identity:

- canonical structured candidate data in `candidate.json`;
- deterministic local processing and validation;
- LLM-assisted analysis and transformation where the LLM plans or rewrites
  controlled parts, but does not own the final artifact end to end;
- primary product pipeline centered on resume generation and ATS-safe output.

The current LLM content surface includes:

- `content match` for ATS-style compatibility analysis;
- `content tailor` for vacancy-oriented transformation of canonical candidate
  data into a new validated `candidate.json`.

There is now a related but distinct need: generate LinkedIn-oriented output
from the same canonical candidate source without collapsing LinkedIn behavior
into the resume-tailoring contract.

LinkedIn is not the same artifact as a tailored resume:

- it has a different communication goal;
- it uses different density and narrative expectations;
- its output should not overwrite or masquerade as canonical candidate JSON;
- it still must remain grounded in the candidate source data.

For that reason, LinkedIn support should live under its own command group
rather than being embedded inside `content tailor`.

## Goal
Add a top-level `linkedin` command group with a first production command:

```bash
hirepaper linkedin generate <candidate.json> --output <linkedin.txt|json> --format txt|json
```

This command should generate a LinkedIn-focused report derived from the
canonical candidate JSON using the same general operating model as
`content tailor`:

1. load and validate canonical candidate data locally;
2. optionally load extra context and custom prompt input;
3. send structured context and output contract to the LLM;
4. validate the model response against a LinkedIn report schema;
5. render and save the final report locally as `txt` or `json`.

The command should produce a report artifact, not a new candidate JSON.

## Product Decision
The `linkedin` command group is a separate public CLI surface.

Initial public behavior:

- `hirepaper linkedin`
  - should behave like `hirepaper linkedin help`
  - if invoked without a subcommand, show help and exit successfully
- `hirepaper linkedin help`
  - explicit help command for the group
- `hirepaper linkedin generate`
  - generates a LinkedIn-focused report from candidate source data

This task does not introduce LinkedIn publishing automation or direct platform
integration. It only produces grounded guidance/content artifacts suitable for
human review and manual use.

## Why A Separate Group
LinkedIn should not be modeled as a variant of `content tailor` because the
artifact contract is different.

`content tailor`:
- primary artifact: final tailored `candidate.json`
- transformation target: canonical resume source data
- downstream use: PDF resume generation

`linkedin generate`:
- primary artifact: LinkedIn-focused report (`txt` or `json`)
- transformation target: derived channel guidance/content
- downstream use: human editing and manual LinkedIn profile updates

This separation keeps the CLI coherent and prevents mixed contracts inside the
`content` namespace.

## Scope
This task may update:

- `src/hirepaper/cli.py`
- new LinkedIn-specific modules under `src/hirepaper/`
- `src/hirepaper/llm/config.py` only if profile-specific config is needed
- `docs/`
- `README.md`
- `project.md`
- `agents.md` if verification guidance should mention the new command group
- `assets/prompts/`
- `assets/schemas/`
- `sdd/history/`

This task may add:

- a `linkedin` Typer command group;
- a `linkedin generate` command;
- a LinkedIn report JSON Schema;
- LinkedIn report rendering helpers for text and JSON output;
- a built-in default prompt asset for LinkedIn report generation;
- optional LinkedIn-specific log archive support if the implementation follows
  the same logging patterns as `content match` / `content tailor`.

This task should not:

- change the canonical candidate JSON schema;
- publish content to LinkedIn;
- scrape LinkedIn;
- claim platform-specific guarantee of ranking or visibility;
- invent unsupported facts, dates, employers, titles, metrics, links, or
  certifications;
- turn the command into a generic social-post generator.

## Command Surface

### Group behavior

```bash
hirepaper linkedin
hirepaper linkedin help
```

Required behavior:

- `hirepaper linkedin` should invoke the same help surface as
  `hirepaper linkedin help`;
- both forms should exit successfully;
- help text should clearly explain that the group is for LinkedIn-focused
  profile/report workflows derived from canonical candidate data.

### Primary command

```bash
hirepaper linkedin generate <candidate.json> --output <linkedin.txt|json> --format txt|json
```

#### Required positional input
- `candidate`: path to canonical candidate JSON

#### Required options
- `--output <path>`
  - required
  - saves the final LinkedIn report artifact

- `--format txt|json`
  - required explicit option for the public contract in this task
  - controls saved output format

#### Optional options
- `--config <config.toml>`
  - optional TOML config override
  - otherwise resolve config using current project precedence
- `--locale`, `-l`
  - report locale
  - default should follow current project conventions
- `--prompt <path>`
  - optional plain-text prompt override
  - fully replaces the built-in default LinkedIn prompt
- `--extra-context <file>`
  - repeatable
  - additional UTF-8 text context that may support grounded rewriting or
    prioritization
- `--log <path>`
  - optional ZIP archive for execution logs if implemented
- `--timeout-seconds`
  - optional per-run override
- `--max-tokens`
  - optional per-run override
- `--force`
  - allow overwrite of output/log destinations
- `--quiet`
  - suppress detailed terminal report if a human-readable terminal rendering is
    otherwise shown
- `--verbose`, `-v`
  - reuse existing LLM transport verbosity semantics if practical

This first task does not require vacancy input. The command is about generating
a strong baseline LinkedIn profile report from candidate source data. Vacancy-
aware LinkedIn tailoring may be added later as a separate task.

## Output Contract
`linkedin generate` produces a LinkedIn-focused report, not a candidate JSON.

Supported output formats:

- `txt`
- `json`

### `txt` output
Human-readable report intended for direct review and manual LinkedIn editing.

### `json` output
Structured machine-readable report intended for automation, future transforms,
or UI integration.

The command succeeds only if:

- input candidate JSON loads successfully;
- candidate data passes `content lint` gating;
- the LLM returns a response that validates against the LinkedIn report schema;
- the final report is successfully rendered and written to `--output`.

The command must fail clearly if:

- `--output` is omitted;
- `--format` is omitted or unsupported;
- the candidate file is missing or invalid;
- the candidate fails lint;
- the prompt file is missing or unreadable;
- an extra-context file is missing, unreadable, or empty;
- the model response cannot be validated against the schema;
- the output path cannot be written.

## Relationship To `content tailor`
The implementation should reuse the same overall design logic where practical:

- local candidate loading through canonical loader;
- preflight overwrite validation;
- lint gating before model work;
- prompt loading from built-in asset or override path;
- extra-context support with UTF-8 validation;
- structured payload creation for the LLM;
- structured schema validation on the returned artifact;
- local rendering to final terminal/text/json output;
- optional execution logs.

However, the final artifact differs:

- `content tailor` returns validated candidate JSON
- `linkedin generate` returns validated LinkedIn report data

That distinction must stay explicit in code, docs, and help text.

## Required Workflow

### 1. Candidate load and lint gate
The command must:

- load the candidate JSON through the existing loader path;
- fail clearly on missing or invalid candidate input;
- run the equivalent of `content lint` before any LLM call.

Lint gating rules:

- lint warnings: continue
- lint failures: abort

The abort message should clearly state that LinkedIn generation was not
attempted because candidate data failed quality validation.

### 2. Output destination preflight
Before any LLM call, validate all destinations:

- `--output`
- `--log` when provided

Required behavior:

- if destination does not exist, continue
- if destination exists and `--force` is set, continue
- if destination exists and `--force` is not set:
  - prompt only in an interactive TTY
  - otherwise fail clearly and exit non-zero

This must happen before any token-consuming operation.

### 3. Prompt and extra context handling
The command must support:

- built-in default prompt asset;
- custom prompt replacement via `--prompt`;
- repeatable UTF-8 `--extra-context` files.

Each extra-context file:

- must be read as UTF-8 text;
- must fail clearly if unreadable or empty;
- is auxiliary context only;
- must not silently override contradictory canonical candidate data.

Grounding priority:

1. canonical `candidate.json`
2. explicit supporting `--extra-context`
3. model inference

### 4. LLM request and response validation
The local code should send a structured payload that includes:

- normalized candidate content;
- locale;
- LinkedIn-specific content policy;
- explicit grounding requirements;
- requested output schema.

The model response must be validated locally against a versioned LinkedIn report
schema.

The command must not treat free-form prose that fails schema validation as
success.

### 5. Final rendering
After validation:

- render text output for `--format txt`;
- render canonical JSON output for `--format json`;
- optionally print a terminal summary unless `--quiet` is active.

The terminal rendering should stay concise and should not replace the saved
artifact contract.

## LinkedIn Report Expectations
The report should be useful for someone updating a real LinkedIn profile while
remaining grounded in source data.

Minimum conceptual sections:

- disclaimer
- profile strategy summary
- recommended headline
- recommended about/summary section
- top skills to emphasize
- experience emphasis guidance
- project or proof-point emphasis guidance
- suggested keywords
- cautions / unsupported claims to avoid
- grounding notes

The report should explain not only what to say, but what to prioritize for the
LinkedIn channel relative to the candidate’s existing source data.

## Initial Report Schema Direction
The exact field names may evolve, but the first public JSON contract should stay
close to this shape:

```json
{
  "disclaimer": "string",
  "profile_focus": "string",
  "headline": {
    "recommended": "string",
    "rationale": ["string"]
  },
  "about": {
    "recommended": "string",
    "rationale": ["string"]
  },
  "top_skills": [
    { "name": "string", "reason": "string" }
  ],
  "experience_highlights": [
    {
      "experience_ref": "exp_1",
      "recommended_emphasis": ["string"],
      "optional_rewrite": "string"
    }
  ],
  "project_highlights": [
    {
      "project_ref": "proj_1",
      "recommended_emphasis": ["string"],
      "optional_rewrite": "string"
    }
  ],
  "keywords": {
    "prioritize": ["string"],
    "avoid": ["string"]
  },
  "cautions": ["string"],
  "grounding_notes": ["string"]
}
```

Important policy:

- the schema should support actionable LinkedIn guidance;
- it should not require platform scraping or platform-private fields;
- it should permit concise optional rewrites while keeping structural grounding;
- it should remain explainable and auditable.

## Content Policy
The LinkedIn output must obey the same factual rigor as the rest of the
project.

Required policy:

- do not invent roles, employers, dates, metrics, technologies, outcomes, or
  certifications;
- do not inflate seniority beyond what source data supports;
- do not fabricate community presence, thought leadership, or audience impact;
- do not convert weak evidence into strong claims;
- do not imply platform growth outcomes that the tool cannot justify.

Allowed behavior:

- reorder emphasis;
- compress or clarify phrasing;
- make tone more suitable for LinkedIn;
- identify stronger source-backed signals already present in candidate data;
- suggest concise rewrites when grounded in explicit source facts.

## Prompt Asset Requirement
Add a built-in default prompt asset for LinkedIn generation under
`assets/prompts/`.

The prompt should:

- frame the model as a grounded LinkedIn profile strategist;
- explain that the candidate JSON is canonical;
- define how extra context may be used;
- require schema-conforming output;
- prohibit invented claims;
- bias toward concise, professional, evidence-backed writing.

The prompt must be written so it works with structured local schema validation
rather than expecting the model to emit free-form markdown only.

## Logging
If `--log` is implemented in this task, follow the existing sensitive-data
policy used in `content match` and `content tailor`.

At minimum, the log archive may include:

- metadata;
- candidate payload sent to the model;
- extra-context inputs;
- selected prompt text;
- schema asset used for validation;
- raw LLM response;
- validated LinkedIn report JSON;
- final rendered text output when applicable.

The help text and runtime messaging must warn that logs can contain sensitive
candidate and model data.

## Documentation Updates
Implementation should update:

- `README.md`
- `project.md`
- relevant `docs/` command references
- `docs/file-map.md`

Documentation should clearly distinguish:

- resume/candidate workflows under `content`
- LinkedIn/report workflows under `linkedin`

## Verification
Minimum verification should include:

```bash
./hirepaper-dev linkedin --help
./hirepaper-dev linkedin help
./hirepaper-dev linkedin generate data/candidate.json --output output/linkedin-report.txt --format txt
./hirepaper-dev linkedin generate data/candidate.json --output output/linkedin-report.json --format json

.venv/bin/python build.py

./hirepaper linkedin --help
./hirepaper linkedin help
./hirepaper linkedin generate data/candidate.json --output output/linkedin-report-packaged.txt --format txt
./hirepaper linkedin generate data/candidate.json --output output/linkedin-report-packaged.json --format json
```

If logging is implemented, also verify one run with `--log`.

## Expected Verification Outcomes
The implementing agent should confirm:

1. `hirepaper linkedin` and `hirepaper linkedin help` show the same help
   surface;
2. `linkedin generate` rejects missing required `--output`;
3. `linkedin generate` rejects unsupported `--format`;
4. candidate lint failures abort before any LLM call;
5. text output is rendered and saved correctly;
6. JSON output validates and is saved correctly;
7. source and packaged entry points remain aligned.

## Acceptance Criteria
1. A new top-level `linkedin` command group exists.
2. `hirepaper linkedin` behaves like help.
3. `hirepaper linkedin help` exists and works.
4. `linkedin generate` accepts canonical candidate input and required
   `--output` + `--format`.
5. The command supports `--prompt` and repeatable `--extra-context`.
6. The implementation follows the same high-level discipline as
   `content tailor`.
7. The final artifact is a LinkedIn-focused report, not candidate JSON.
8. Output is supported in both `txt` and `json`.
9. Grounding rules forbid invented claims.
10. The change is documented and verified in source and packaged modes.
11. A history entry records the implementation and verification.

## Notes For The Implementing Agent
- Reuse `content tailor` architecture where it helps, but do not force the
  LinkedIn command into the `content` contract.
- Optimize for a strict, auditable output shape.
- Keep the first scope to report generation only.
- Treat LinkedIn as a derived communication channel, not a new source of truth.
