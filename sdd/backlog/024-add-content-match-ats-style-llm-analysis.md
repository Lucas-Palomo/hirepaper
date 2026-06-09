# 024 - Add `content match` ATS-style LLM compatibility analysis

## Status
Completed

## Context
The project already has the following related building blocks:

- candidate JSON input used by PDF generation;
- `content lint` for candidate-data quality checks;
- LLM configuration loading via `--config`;
- initial `content match` / `content tailor` connectivity commands;
- `llm health` and `llm usage` diagnostics.

The current `content match` command is only a connectivity test. It does not yet
analyze the candidate JSON against a vacancy description or return a meaningful
compatibility assessment.

The next step is to turn `content match` into a real ATS-style compatibility
analysis workflow that compares:
- a candidate JSON file using the existing resume schema;
- a raw vacancy `.txt` file;
- an LLM configuration file for the actual model call.

This workflow is intentionally non-deterministic because it depends on LLM
reasoning. That non-determinism must be explicit in the UX and in the command
output.

## Goal
Implement a production-usable `content match` command that:
- reads the canonical candidate JSON;
- reads a raw vacancy `.txt` description;
- runs candidate validation via `content lint` before matching;
- sends a structured ATS-style matching request to the configured LLM;
- returns a detailed human-readable report by default;
- optionally returns structured JSON for automation;
- optionally saves the final report and full execution logs;
- explains the reasons behind the model's decision with clear traceability.

## Scope
This task may update:
- `src/curriculum_gen/cli.py`
- `src/curriculum_gen/content_lint.py`
- `src/curriculum_gen/llm/config.py`
- `src/curriculum_gen/llm/client.py`
- new matching-specific modules under `src/curriculum_gen/`
- `project.md`
- `agents.md` if execution guidance needs to mention the new command
- `sdd/history/`

This task may add:
- a structured result model for content matching;
- a prompt loader and default prompt asset;
- a versioned JSON Schema asset for the public match result;
- helper code for report rendering;
- fixtures for testing candidate/vacancy matching flows.

This task should not:
- change the candidate JSON schema itself;
- implement `content tailor` beyond what is needed for shared helpers;
- silently fall back when the LLM request fails;
- invent unsupported candidate facts.

## Command Surface
Target command shape:

```bash
curriculum-gen content match <candidate.json> <vacancy.txt> --config <config.json>
```

### Required inputs
- positional `candidate`: existing candidate JSON schema file
- positional `vacancy`: raw vacancy description text file
- required `--config`: real LLM config file

### Flags
- `--locale`, `-l`
  - controls response language for the final rendered analysis
  - default should follow current project conventions
- `--format`
  - default output is human-readable text
  - supported explicit values: `text|json`
  - supported explicit machine option: `json`
  - if provided with any unsupported value, fail clearly
- `--output <path>`
  - optional path to save the final rendered result
  - must save exactly the selected final format
  - human-readable text when default format is used
  - JSON when `--format=json` is used
- `--log <path>`
  - optional path to save execution logs/artifacts as a `.zip` archive
  - help text must explain that the saved log format is ZIP
  - logs must include sensitive-data warning in help text and runtime messaging
  - the ZIP may contain full candidate payload, vacancy text, prompt, model
    output, and usage metadata
- `--prompt <path>`
  - optional path to a plain-text prompt file
  - if provided, it fully replaces the built-in default matching prompt
- `--strict`
  - restricts the model to explicit evidence from the candidate JSON and vacancy
    text only
  - when `--strict` is used, `--inference=low` becomes mandatory
  - any incompatible combination must fail clearly before the model call
- `--inference low|medium|high`
  - controls how much technical/semantic inference the model may apply
  - `low`: conservative, near-literal matching
  - `medium`: balanced equivalence/inference
  - `high`: broader semantic inference where evidence is still explained
  - default should be `medium` unless `--strict` is active

## Required Workflow
### 1. Candidate load and validation
The command must:
- load the candidate JSON using the existing loader path;
- fail clearly if the file is missing or invalid;
- run the equivalent of `content lint` before matching.

Lint gating rules:
- lint warnings: continue matching
- lint failures: abort matching

The abort message must make it obvious that the match was not attempted because
candidate data quality failed validation.

### 2. Vacancy input handling
The vacancy input is a raw `.txt` file and may be noisy, unstructured, or copied
from job boards, email, or chat.

The implementation must:
- read the file as UTF-8 text;
- fail clearly if the file is missing or unreadable;
- treat the text as raw source input rather than requiring pre-normalized
  sections.

The model is expected to infer likely categories such as:
- mandatory requirements;
- desirable requirements;
- responsibilities;
- contextual/company text.

That inference must still be grounded in the raw vacancy text.

### 3. Matching architecture
Use a hybrid flow rather than a free-form LLM prompt.

Minimum architecture:
1. validate candidate input
2. run lint gate
3. load vacancy text
4. build a structured candidate payload from the JSON
5. build prompt context including:
   - matching policy
   - locale
   - strict/inference policy
   - expected output schema
6. call the LLM
7. parse and validate structured response
8. render text or JSON output
9. optionally save output and logs

The local code should structure the candidate data before sending it to the
model. Do not rely on the LLM to rediscover schema semantics from raw JSON
without guidance.

Use both:
- a natural-language prompt for behavioral instructions;
- a versioned JSON Schema for structural output constraints.

The same JSON Schema used for local validation should also be provided to the
LLM as explicit context during the request.

## ATS-style Analysis Expectations
The model should act like an ATS-style compatibility evaluator, but with better
explainability than a simple keyword matcher.

The result must include:
- overall score from `0` to `100`;
- formal category label;
- final verdict;
- executive summary;
- strengths;
- gaps;
- matched requirements;
- unmatched requirements;
- clearly separated inferences;
- a non-determinism disclaimer.

### Score categories
Use these exact category bands:
- `90-100`: `strong`
- `75-89`: `good`
- `60-74`: `partial`
- `40-59`: `weak`
- `0-39`: `poor`

The model should produce both:
- numeric `score`
- categorical `rating`

The implementation must validate that `rating` is consistent with `score`.

`rating` must use a fixed enum:
- `strong`
- `good`
- `partial`
- `weak`
- `poor`

## Strict and Inference Policy
### `--strict`
When `--strict` is active:
- only explicit evidence from the candidate JSON and vacancy text may be used;
- inference must be minimized;
- `--inference=low` is mandatory;
- `inferences` in the final result should be empty or minimal and clearly marked.

### `--inference`
The model must receive explicit behavior instructions for inference level.

Recommended behavior:
- `low`
  - avoid equivalence unless explicit or extremely obvious
  - prioritize literal evidence
- `medium`
  - allow common technical equivalence and moderate semantic interpretation
- `high`
  - allow broader semantic interpretation, but still require traceable rationale

Invalid combinations must fail before the LLM request.

Example invalid usage:
```bash
curriculum-gen content match data/candidate.json data/vaga.txt --config ./config --strict --inference high
```

Expected behavior:
- command exits non-zero
- clear message explains that `--strict` requires `--inference=low`

## Output Formats
### Default human-readable output
The default terminal output must be a polished, readable report containing at
minimum:
- disclaimer about LLM subjectivity/non-determinism;
- score and rating;
- final verdict;
- executive summary;
- strengths;
- gaps;
- matched requirements;
- unmatched requirements;
- explicit inferences section;
- any relevant cautionary notes.

The explanation quality matters more than brevity. The user must be able to
understand why the model concluded what it concluded.

To avoid unnecessary repetition, the default human-readable report should be
rendered in this order:
1. disclaimer
2. score / rating / verdict
3. executive summary
4. strengths
5. gaps
6. matched requirements
7. unmatched requirements
8. inferences

The JSON result may keep separate structures even when the human-readable
renderer consolidates them for readability.

### JSON output
When `--format=json` is used, the command must emit only structured JSON as the
final result.

The schema should be balanced for:
- machine automation;
- human auditability.

The public JSON contract should also exist as a versioned repository asset:

- `assets/schemas/content-match-result.schema.json`

The implementation should:
- load this schema as part of the matching request context;
- use it to reinforce the output contract in the model call;
- validate parsed model output against the same schema locally.

Target JSON shape:

```json
{
  "score": 78,
  "rating": "good",
  "verdict": "Good overall compatibility with notable gaps in specific requirements.",
  "summary": "Candidate aligns with Python backend and API work, but lacks explicit evidence for some requested technologies.",
  "strengths": [
    {
      "title": "Relevant backend experience",
      "evidence": [
        "Candidate evidence...",
        "Vacancy evidence..."
      ]
    }
  ],
  "gaps": [
    {
      "title": "Missing explicit evidence for a required technology",
      "severity": "high",
      "evidence": [
        "Vacancy requires X...",
        "Candidate JSON does not explicitly show X..."
      ]
    }
  ],
  "matched_requirements": [
    {
      "requirement": "Experience with REST APIs",
      "priority": "must_have",
      "assessment": "matched",
      "confidence": "high",
      "evidence": [
        "..."
      ]
    }
  ],
  "unmatched_requirements": [
    {
      "requirement": "Experience with Kubernetes",
      "priority": "nice_to_have",
      "assessment": "not_matched",
      "confidence": "medium",
      "evidence": [
        "..."
      ]
    }
  ],
  "inferences": [
    {
      "claim": "FastAPI experience may indicate REST API familiarity",
      "basis": "Technical inference",
      "confidence": "medium"
    }
  ],
  "disclaimer": "This analysis uses an LLM and may contain subjective judgment. Review the evidence before making decisions."
}
```

The exact field names for the first implementation must be:
- `score`
- `rating`
- `verdict`
- `summary`
- `strengths`
- `gaps`
- `matched_requirements`
- `unmatched_requirements`
- `inferences`
- `disclaimer`

The implementation may add internal helper models, but the public JSON contract
should remain stable once introduced.

`confidence` must use a fixed enum:
- `low`
- `medium`
- `high`

`priority` must use a fixed enum:
- `must_have`
- `should_have`
- `nice_to_have`
- `unknown`

`assessment` must use a fixed enum:
- `matched`
- `partially_matched`
- `not_matched`
- `unclear`

Use `unclear` when the available candidate and vacancy evidence does not allow a
reasonable conclusion of `matched`, `partially_matched`, or `not_matched`
without overstating certainty.

`severity` must use a fixed enum:
- `low`
- `medium`
- `high`

## Prompt Behavior
### Default prompt
Provide a built-in default prompt for ATS-style matching.

The default prompt should live as a versioned text asset in the repository
rather than being embedded inline in code. A suitable location is under
`assets/` so it remains easy to inspect, patch, and log. The first
implementation should store it as:

- `assets/prompts/content-match-default.txt`

The public JSON result schema should also live as a versioned repository asset:

- `assets/schemas/content-match-result.schema.json`

The prompt must instruct the model to:
- behave as a resume-to-vacancy compatibility evaluator;
- analyze only the supplied candidate payload and vacancy text;
- respect locale output requirements;
- respect strict/inference policy;
- identify likely mandatory vs desirable requirements from the vacancy text;
- classify requirements using the public `priority` enum;
- avoid inventing unsupported candidate experience;
- separate explicit evidence from inference;
- return the exact structured schema requested.

For `inferences`, the response should use:
- `claim`: free text
- `basis`: free text
- `confidence`: validated enum `low|medium|high`

The default prompt content for the first implementation should be:

```text
You are an ATS-style candidate-to-vacancy compatibility evaluator.

Your task is to compare:
1. a structured candidate payload
2. a raw vacancy text

You must produce a compatibility analysis that is useful for human review and
machine processing.

Core constraints:
- Use only the supplied candidate payload and vacancy text.
- Do not invent candidate experience, skills, certifications, achievements,
  education, language ability, leadership background, seniority, or domain
  expertise.
- Respect the requested output locale for all natural-language fields.
- Treat the vacancy text as potentially noisy, messy, or incomplete. Infer
  structure from it, but stay grounded in the text.
- Distinguish explicit evidence from inference.
- If evidence is insufficient to conclude matched, partially_matched, or
  not_matched with reasonable confidence, use unclear.

Matching policy:
- strict mode means rely only on explicit evidence from the candidate payload
  and vacancy text
- inference=low means conservative, near-literal matching
- inference=medium means balanced technical/semantic inference
- inference=high means broader semantic inference, but still grounded in
  traceable rationale

Enum rules:
- requirement priority:
  - must_have
  - should_have
  - nice_to_have
  - unknown
- assessment:
  - matched
  - partially_matched
  - not_matched
  - unclear
- confidence:
  - low
  - medium
  - high
- gap severity:
  - low
  - medium
  - high
- rating bands:
  - 90-100 => strong
  - 75-89 => good
  - 60-74 => partial
  - 40-59 => weak
  - 0-39 => poor

Analysis requirements:
- Identify likely requirements from the vacancy text.
- Infer each requirement priority as must_have, should_have, nice_to_have, or
  unknown.
- Evaluate candidate alignment for each requirement.
- Produce an overall score from 0 to 100.
- Ensure the rating matches the score band.
- Explain why the candidate matches or does not match.
- Highlight strengths that materially support the score.
- Highlight gaps that materially reduce the score.
- Use higher gap severity when the missing evidence meaningfully damages overall
  compatibility, especially for likely must_have requirements.
- Keep priority and severity conceptually separate:
  - priority = how important the requirement appears in the vacancy
  - severity = how damaging the gap is to the final match result

Evidence rules:
- Every strength, gap, matched requirement, and unmatched requirement should be
  grounded in evidence.
- Evidence should be short, concrete, and traceable to the candidate payload or
  vacancy text.
- Do not quote excessively; concise snippets or precise paraphrases are fine.
- Inferences must be listed separately from explicit matches.
- If strict mode is active, keep inferences empty or minimal and only when
  absolutely necessary.

Output contract:
- Return only valid JSON.
- Do not include markdown fences.
- Do not include commentary before or after the JSON object.
- Return exactly one JSON object.
- Use exactly these top-level fields:
  - score
  - rating
  - verdict
  - summary
  - strengths
  - gaps
  - matched_requirements
  - unmatched_requirements
  - inferences
  - disclaimer

Top-level field requirements:
- score: integer or numeric value from 0 to 100
- rating: one of strong, good, partial, weak, poor
- verdict: short executive conclusion
- summary: concise audit-friendly explanation of the result
- strengths: array of objects with:
  - title
  - evidence (array of strings)
- gaps: array of objects with:
  - title
  - severity
  - evidence (array of strings)
- matched_requirements: array of objects with:
  - requirement
  - priority
  - assessment
  - confidence
  - evidence (array of strings)
- unmatched_requirements: array of objects with:
  - requirement
  - priority
  - assessment
  - confidence
  - evidence (array of strings)
- inferences: array of objects with:
  - claim
  - basis
  - confidence
- disclaimer: must state that this analysis uses an LLM and may contain
  subjective judgment

Scoring guidance:
- A high score requires strong alignment on likely must_have requirements.
- Missing likely must_have requirements should usually reduce the score
  substantially.
- Nice-to-have gaps should usually reduce the score less than must-have gaps.
- Use partial matches when the candidate shows related but incomplete evidence.
- Use unclear when the available evidence is too weak or ambiguous for a more
  confident classification.

Final reminder:
- Be evidence-driven.
- Be conservative when evidence is weak.
- Keep the JSON schema valid.
```

### Prompt replacement
If `--prompt <file>` is provided:
- load prompt file as plain text;
- fully replace the default prompt;
- fail clearly if the file is missing or unreadable.

The command should still enforce output-schema requirements even when a custom
prompt is used.

## Logging
When `--log <path>` is provided, save a ZIP archive containing a structured log
bundle with at least:
- command parameters relevant to matching;
- effective prompt text;
- candidate payload sent to the model;
- vacancy text sent to the model;
- raw LLM response;
- parsed/validated result;
- token/usage metadata if available;
- timestamp and model/config metadata where available.

The command help and/or runtime messaging must warn that logs may store
sensitive information.

Minimum required ZIP contents:
- `meta.json`
- `prompt.txt`
- `candidate-payload.json`
- `vacancy.txt`
- `raw-response.json`
- `validated-result.json`
- `usage.json`

If `--log` is requested, producing the ZIP archive is mandatory. Partial or
ad hoc log output outside the ZIP should be treated as a failure for this task.

`meta.json` must contain at least:

```json
{
  "command": "curriculum-gen content match data/candidate.json data/vacancy.txt --config ./config --format=json",
  "timestamp_utc": "2026-06-05T15:30:00Z",
  "locale": "pt-BR",
  "format": "json",
  "strict": false,
  "inference": "medium",
  "model": "provider/model-name",
  "base_url": "https://example.invalid",
  "candidate_path": "data/candidate.json",
  "vacancy_path": "data/vacancy.txt",
  "prompt_source": "default",
  "output_path": "output/match-report.json",
  "log_path": "output/match-log.zip",
  "lint_status": "warning",
  "llm_call_status": "success"
}
```

Minimum required `meta.json` fields:
- `command`
- `timestamp_utc`
- `locale`
- `format`
- `strict`
- `inference`
- `model`
- `base_url`
- `candidate_path`
- `vacancy_path`
- `prompt_source`
- `output_path`
- `log_path`
- `lint_status`
- `llm_call_status`

Do not store API keys or other secret credentials in `meta.json`.

## Failure Behavior
The command must fail completely when:
- candidate JSON cannot be loaded;
- content lint returns failure;
- vacancy file cannot be read;
- config cannot be loaded;
- prompt file cannot be loaded;
- strict/inference combination is invalid;
- the LLM request fails;
- the LLM response cannot be parsed or validated;
- output/log files cannot be written.

Do not provide heuristic fallback matching in this task.

## Implementation Guidance
### Candidate payload shaping
Build a structured candidate payload from the current data model, rather than
passing only opaque raw JSON.

At minimum include normalized sections such as:
- personal/headline context
- summary/profile
- experience
- education
- skills
- projects
- certifications
- awards
- volunteer
- languages
- links

Do not alter facts. Preserve source-grounded content only.

### Priority vs severity
Keep these concepts separate:
- `priority`: how important a requirement appears to be in the vacancy
  (`must_have|should_have|nice_to_have|unknown`)
- `severity`: how damaging a specific gap is to the overall compatibility
  assessment (`low|medium|high`)

A `must_have` requirement often leads to a more severe gap when unmet, but the
implementation should not assume they are identical fields.

### Result validation
The result parser should verify at least:
- all required top-level fields exist;
- `score` is numeric and within `0-100`;
- `rating` is one of `strong|good|partial|weak|poor`;
- `rating` matches the score band;
- any `priority` fields are one of
  `must_have|should_have|nice_to_have|unknown`;
- any `assessment` fields are one of
  `matched|partially_matched|not_matched|unclear`;
- any `confidence` fields are one of `low|medium|high`;
- any `severity` fields are one of `low|medium|high`;
- list fields are arrays;
- disclaimer is non-empty.

### LLM JSON parsing and validation
The implementation must treat the LLM output as untrusted until validated.

Required parsing behavior:
- the model must be instructed to return only a JSON object;
- the model request must include the versioned JSON Schema as explicit context;
- if the response contains markdown code fences, the implementation may strip a
  single outer fenced JSON wrapper before parsing;
- if the response contains extra prose before or after the JSON object, fail;
- if valid JSON cannot be extracted, fail;
- if the parsed JSON does not satisfy schema validation, fail.

Do not apply heuristic fallback repair beyond the minimal removal of a single
outer JSON markdown fence. Do not silently coerce malformed structures into a
valid result.

Logging expectations for parsing:
- store the original raw model output in `raw-response.json`;
- store the validated public result in `validated-result.json`;
- if parsing fails, preserve enough raw output in the ZIP to diagnose the
  failure.

### Output rendering
Human-readable rendering should be deterministic given a validated result
object, even though the underlying model call is not deterministic.

Prefer separating:
- LLM response parsing/validation
- result-domain model
- human report rendering
- JSON serialization

## Documentation Expectations
If this task is implemented, update project context where needed to document:
- real behavior of `content match`;
- supported flags;
- logging sensitivity;
- failure model;
- JSON output mode.

## Verification Expectations
Minimum implementation verification should include:

### Source CLI checks
```bash
./curriculum-gen-dev content match --help
./curriculum-gen-dev content lint data/candidate.json
```

### Real matching execution
Use a real config file for this task's verification context:
```bash
./curriculum-gen-dev content match data/candidate.json data/vacancy.txt --config ./config
./curriculum-gen-dev content match data/candidate.json data/vacancy.txt --config ./config --format=json
./curriculum-gen-dev content match data/candidate.json data/vacancy.txt --config ./config --output output/match-report.txt
./curriculum-gen-dev content match data/candidate.json data/vacancy.txt --config ./config --format=json --output output/match-report.json
./curriculum-gen-dev content match data/candidate.json data/vacancy.txt --config ./config --log output/match-log.json
```

### Policy validation
```bash
./curriculum-gen-dev content match data/candidate.json data/vacancy.txt --config ./config --strict --inference low
./curriculum-gen-dev content match data/candidate.json data/vacancy.txt --config ./config --strict --inference high
```

Expected:
- first command may proceed
- second command must fail clearly before the model call

### Packaging validation
After implementation:
```bash
.venv/bin/python build.py
./curriculum-gen content match --help
```

## Acceptance Criteria
1. `content match` accepts `<candidate.json>` and `<vacancy.txt>` plus required `--config`.
2. The command runs candidate validation before matching.
3. Lint warnings allow matching to continue.
4. Lint failures abort matching.
5. The command performs a real ATS-style LLM analysis rather than a connectivity test.
6. Default output is human-readable and includes score, rating, verdict, summary, strengths, gaps, matched/unmatched requirements, inferences, and disclaimer.
7. `--format=json` emits structured JSON using the documented schema.
8. `--output` saves the final rendered format exactly as selected.
9. `--log` saves a ZIP archive containing prompt, payload, raw response, validated result, and usage metadata, with documentation warning about sensitive data.
10. `--prompt` fully replaces the default prompt.
11. `--strict` requires `--inference=low`.
12. Invalid strict/inference combinations fail clearly before the model call.
13. The model is instructed to infer likely mandatory vs desirable requirements from the raw vacancy text.
14. The implementation validates the structured LLM result before rendering.
15. The command fails completely on LLM failure; no heuristic fallback is used.
16. Source help and packaged help both work after implementation.
17. Real matching smoke tests succeed with `./config` in the execution environment used for this task.
18. Completed work is documented in `sdd/history/024-...`.

## Completion Record
When complete, record implementation details, prompt decisions, verification
commands, and residual risks in `sdd/history/024-...`.
