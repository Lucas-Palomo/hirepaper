# 041 - Add Markdown report output for human-readable report commands

## Status
Completed

## Context
The project already exposes multiple commands that return a structured result in
two broad output modes:

- machine-readable JSON;
- human-readable plain text meant for terminal reading or saved report files.

Today, the human-readable path is not consistent across commands:

- `content match` uses `--format text|json`;
- `content tailor` uses `--report-format text|json` for the optional saved
  report while the primary artifact remains a tailored `candidate.json`;
- `linkedin generate` uses `--format txt|json`.

The project now needs a third output option for the same human-oriented report
surface:

- Markdown (`.md`)

This should not introduce new semantic report content. It should provide a new
rendering format for the same validated report data already produced by these
commands.

## Commands In Scope
Based on the current codebase, the commands that accept a humanized report
format and should gain Markdown support are:

1. `hirepaper content match`
2. `hirepaper content tailor`
3. `hirepaper linkedin generate`

These are in scope because they already expose either:

- a format selector for human-readable vs JSON output; or
- an explicit saved report format contract.

The following are out of scope for this task:

- `hirepaper doctor`
- `hirepaper pdf check`
- `hirepaper pdf generate`
- `hirepaper llm health`
- `hirepaper llm usage`
- commands that only print operational diagnostics to stdout/stderr without a
  versioned report-format contract

## Goal
Allow every command that currently supports human-readable text reports to also
emit Markdown reports.

Required user-visible outcome:

- commands that currently support `text` or `txt` should also support `md`
- Markdown output should be saveable to file and printable to terminal
- JSON output behavior must remain unchanged

## Product Decision
Markdown is a rendering format, not a new report schema.

That means:

- the validated underlying structured report/result remains the source of truth
- `txt` / `text` / `md` are alternate renderings of the same structured data
- Markdown should remain deterministic and generated locally after schema
  validation

This task must not change the meaning of result schemas, scoring logic, lint
gates, or grounding policies.

## Scope
This task may update:

- `src/hirepaper/cli.py`
- `src/hirepaper/content_match.py`
- `src/hirepaper/content_tailor.py`
- `src/hirepaper/linkedin_generate.py`
- `README.md`
- `project.md`
- `docs/content.md`
- `docs/content-match.md`
- `docs/content-tailor.md`
- LinkedIn docs if present at implementation time
- `docs/file-map.md`
- `agents.md` only if verification guidance should mention Markdown output
- `sdd/history/`

This task may add:

- Markdown renderer helpers alongside existing text/JSON renderers
- shared formatting helpers if they materially reduce duplication
- updated examples and output-contract docs

This task should not:

- redesign result schemas
- rename public commands
- change primary artifacts such as the tailored `candidate.json`
- introduce rich HTML output
- add Markdown-only fields that are absent from the structured result

## Required Public Contract

### 1. `hirepaper content match`
Current public contract:

```bash
hirepaper content match <candidate.json> <vacancy.txt> [--format text|json]
```

Required new contract:

```bash
hirepaper content match <candidate.json> <vacancy.txt> [--format text|md|json]
```

Required behavior:

- `text` remains supported for backward compatibility
- `md` becomes a new human-readable output format
- `json` remains unchanged
- when `--output` is provided, the saved file content must match the selected
  format exactly

### 2. `hirepaper content tailor`
Current public contract:

```bash
hirepaper content tailor <candidate.json> <vacancy.txt> --output <tailored.json> \
  [--report-format text|json]
```

Required new contract:

```bash
hirepaper content tailor <candidate.json> <vacancy.txt> --output <tailored.json> \
  [--report-format text|md|json]
```

Required behavior:

- primary artifact remains the tailored `candidate.json`
- `--report-format md` becomes valid for terminal report rendering and optional
  `--report-output`
- `text` remains supported for backward compatibility
- `json` remains unchanged

### 3. `hirepaper linkedin generate`
Current public contract:

```bash
hirepaper linkedin generate <candidate.json> --output <report> --format txt|json
```

Required new contract:

```bash
hirepaper linkedin generate <candidate.json> --output <report> --format txt|md|json
```

Required behavior:

- `txt` remains supported for backward compatibility
- `md` becomes a new human-readable output format
- `json` remains unchanged

## Format-Naming Policy
The project currently uses both `text` and `txt` depending on the command.
This task should preserve existing command spelling for backward compatibility.

Required policy:

- `content match`: use `text`, `md`, `json`
- `content tailor`: use `text`, `md`, `json`
- `linkedin generate`: use `txt`, `md`, `json`

This task should not silently rename `text` to `txt` or vice versa.

Documentation should explain the distinction clearly rather than trying to
normalize it in behavior during this task.

## Rendering Expectations
Markdown output should be useful in:

- GitHub/GitLab markdown viewers
- editors and note apps
- documentation or application workflows that accept `.md`
- human review over email/chat copy-paste

Markdown should be:

- clean
- readable in raw form
- stable
- minimal

Avoid:

- HTML inside Markdown unless truly required
- decorative clutter
- complex tables when bullet lists are clearer
- format-specific content that diverges from `text`/`json`

Recommended Markdown patterns:

- top-level title with `#`
- major sections with `##`
- bullet lists for strengths, gaps, changes, warnings, skills, keywords
- short labeled lines where appropriate, such as score/rating/verdict
- fenced code blocks only when the structured content genuinely calls for them

## Command-Specific Markdown Requirements

### `content match`
Markdown rendering should represent the same conceptual sections as the text
report, including:

- title
- disclaimer
- score / rating / verdict
- executive summary
- strengths
- gaps
- matched requirements
- unmatched requirements
- inferences

Potential shape:

```md
# ATS Compatibility Analysis

## Disclaimer
...

## Summary
...

## Score
- Score: 85/100
- Rating: good
- Verdict: ...
```

### `content tailor`
Markdown rendering should represent the same conceptual sections as the text
report, including:

- title
- disclaimer
- mode / inference
- executive summary
- target role
- key changes
- rewrites
- removed or deprioritized sections
- lint status
- warnings

### `linkedin generate`
Markdown rendering should represent the same conceptual sections as the current
text report, including:

- title
- disclaimer
- profile strategy
- recommended headline
- recommended about section
- top skills
- experience emphasis guidance
- project emphasis guidance
- keywords
- cautions
- grounding notes

## Terminal Behavior
Markdown is a valid human-readable terminal output format, but the terminal
experience should remain practical.

Required policy:

- when `md` is selected, the command may print raw Markdown to stdout
- `--quiet` behavior must remain consistent with the current command semantics
- stderr artifact-path messaging must remain intact
- the command must not render one format to terminal and save another format to
  file within the same invocation

## Logging
If a command currently stores final human-readable report text in logs, decide
and document how Markdown is persisted.

Preferred behavior:

- save the actual final rendered artifact under a format-appropriate filename
- examples:
  - `final-report.txt`
  - `final-report.md`
  - `final-report.json`

At minimum, log behavior must not mislabel Markdown content as `.txt`.

## Output Path Behavior
This task does not require strict extension enforcement.

Required behavior:

- users may choose any output filename
- the file content must match the selected format
- docs and examples should encourage `.md` when `md` is selected

Optional implementation detail:

- commands may warn, but should not fail, when the output extension appears
  inconsistent with the chosen format

## Implementation Direction
Preferred implementation direction:

1. keep validated structured data as the canonical intermediate representation
2. add dedicated Markdown renderer functions:
   - `render_markdown_report(...)`
   - or equivalent local naming per module
3. branch output rendering only after validation
4. keep text and Markdown renderers close together so section parity is easy to
   maintain

If duplication becomes excessive, the implementation may extract shared helper
formatters, but this task should avoid broad renderer refactors unless they
clearly reduce maintenance risk.

## CLI Validation Rules
The CLI must reject unsupported format values clearly.

Required examples:

- `content match --format yaml` -> fail
- `content tailor --report-format yaml` -> fail
- `linkedin generate --format yaml` -> fail

Updated accepted values:

- `content match`: `text`, `md`, `json`
- `content tailor`: `text`, `md`, `json`
- `linkedin generate`: `txt`, `md`, `json`

## Documentation Updates
Implementation should update public docs so output-format support is consistent
everywhere.

At minimum update:

- command option tables
- usage examples
- format descriptions
- any file-map references to the affected commands

Examples should include at least one Markdown save flow per affected command.

## Verification
Minimum verification should include:

```bash
./hirepaper-dev content match data/candidate.json data/vacancy.txt --format md
./hirepaper-dev content match data/candidate.json data/vacancy.txt --format md --output output/match.md

./hirepaper-dev content tailor data/candidate.json data/vacancy.txt \
  --output output/tailored.json \
  --report-format md \
  --report-output output/tailor-report.md

./hirepaper-dev linkedin generate data/candidate.json \
  --output output/linkedin-report.md \
  --format md

.venv/bin/python build.py

./hirepaper content match data/candidate.json data/vacancy.txt --format md --output output/match-packaged.md
./hirepaper content tailor data/candidate.json data/vacancy.txt \
  --output output/tailored-packaged.json \
  --report-format md \
  --report-output output/tailor-report-packaged.md
./hirepaper linkedin generate data/candidate.json \
  --output output/linkedin-report-packaged.md \
  --format md
```

Also verify negative cases:

```bash
./hirepaper-dev content match data/candidate.json data/vacancy.txt --format yaml
./hirepaper-dev content tailor data/candidate.json data/vacancy.txt --output output/tailored.json --report-format yaml
./hirepaper-dev linkedin generate data/candidate.json --output output/linkedin.md --format yaml
```

## Expected Verification Outcomes
The implementing agent should confirm:

1. all three commands accept `md`
2. existing `text`/`txt` behavior remains unchanged
3. existing `json` behavior remains unchanged
4. Markdown output is readable both raw and rendered
5. saved file content matches the chosen format
6. logs do not mislabel Markdown artifacts as plain text
7. source and packaged entry points remain aligned

## Acceptance Criteria
1. Every command in scope that supports a human-readable report now also
   supports Markdown output.
2. `content match` accepts `--format md`.
3. `content tailor` accepts `--report-format md`.
4. `linkedin generate` accepts `--format md`.
5. Existing `text` / `txt` / `json` options remain backward compatible.
6. Markdown renderers are generated locally from already-validated structured
   report data.
7. Documentation is updated to reflect Markdown support.
8. Verification covers source mode and packaged mode.
9. A history entry records implementation details and verification results.

## Notes For The Implementing Agent
- Keep this as a format-expansion task, not a content-redesign task.
- Preserve report section parity across text, Markdown, and JSON.
- Be careful with logging filenames and help text so Markdown artifacts are not
  described as plain text by mistake.
