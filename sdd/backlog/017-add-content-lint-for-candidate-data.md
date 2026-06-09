# 017 - Add content lint for candidate data

## Status
Completed

## Context
The project already does two important things reasonably well:
- generates ATS-safe resume PDFs from structured JSON;
- validates technical PDF extraction safety with `ats-check`.

What it does not yet do is evaluate whether the resume content itself is strong, consistent, and recruiter-friendly before rendering.

Today, the candidate input validation in `src/curriculum_gen/loader.py` is intentionally minimal. It mostly ensures that a few required fields exist.

That is not enough for real-world resume authoring.

A candidate can still produce a resume that is:
- technically extractable by ATS;
- visually acceptable;
- weak in substance;
- inconsistent in chronology;
- repetitive;
- vague;
- missing measurable impact;
- overfilled with low-signal bullets.

This task introduces a separate content lint layer focused on the quality and structure of resume data, not on PDF rendering safety and not yet on job-description matching.

## Goal
Provide a local content-lint command that analyzes candidate JSON and reports actionable density and section-balance diagnostics before PDF generation.

The command should help the candidate answer:
- Is my input complete enough?
- Is any section too dense for recruiter scanning?
- Is the content balance between sections reasonable?
- Is the resume overpacked in ways that commonly hurt ATS parsing and recruiter review?

The command must stay conservative and explainable. It should not pretend to be a perfect recruiter simulator.

## Command
Add a new CLI command:

```bash
curriculum-gen lint-content <candidate_json>
```

Expected usage:

```bash
curriculum-gen lint-content data/candidate.json
```

The command should inspect the structured input and report `OK`, `WARN`, and `FAIL` diagnostics in a style consistent with `ats-check`.

## Scope Boundary
This task is specifically about deterministic content lint for candidate data.

It must not expand into:
- ATS PDF extraction validation;
- automatic rewriting of resume bullets;
- LLM-generated resume content;
- job-description matching or vacancy targeting;
- keyword libraries or keyword coverage scoring;
- ranking candidates against external benchmarks.

Those may come later as separate tasks.

## Core Principles
The lint should be:
- deterministic where possible;
- low-noise;
- easy to explain;
- focused on section density and scanability;
- advisory on editorial balance.

Use failures only for problems that make the data clearly broken or materially unreliable.

Use warnings for density issues, section imbalance, or missed prioritization opportunities.

## Required Checks

### 1. Structural completeness
Validate that the JSON contains the minimum content expected for a credible resume.

At minimum, check:
- `summary` exists and is not empty;
- at least one `experience` or `project` entry exists;
- `skills` exists and has at least one non-empty category;
- `education` exists unless the project explicitly decides to allow omission.

Examples:
- empty summary;
- no experience and no projects;
- skills section present but effectively empty.

### 2. Summary density
Measure whether the summary is too short or too dense for fast scanning.

At minimum, measure:
- word count;
- estimated line density;
- whether the summary is absent, too short, or overly long for a compact resume.

Suggested initial thresholds:
- `FAIL` if empty;
- `WARN` if fewer than 25 words;
- `OK` if roughly 25 to 80 words;
- `WARN` if more than 80 words.

The agent executor may tune these thresholds slightly if implementation details make adjacent values more practical.

### 3. Experience density
Measure how dense the work-experience section is.

At minimum, check:
- total number of experience entries;
- bullets per role;
- word count per bullet;
- total number of experience bullets across the resume.

Suggested initial thresholds:
- `FAIL` if no `experience` and no `projects` exist;
- `WARN` if a role has more than 5 bullets;
- `WARN` if a bullet exceeds 32 words;
- `WARN` if total experience bullets exceed 18 to 20.

This phase should not try to score bullet quality semantically. It should focus on density only.

### 4. Skills density
Measure whether the skills section is overpacked.

At minimum, check:
- number of categories;
- number of skills per category;
- total skill count.

Suggested initial thresholds:
- `FAIL` if skills are missing or all categories are empty;
- `WARN` if a category has more than 8 to 10 items;
- `WARN` if total skill count exceeds roughly 30 to 35.

### 5. Projects density
Measure whether the projects section is oversized relative to the rest of the resume.

At minimum, check:
- number of projects;
- highlights per project;
- description word count per project.

Suggested initial thresholds:
- `WARN` if more than 3 projects are rendered with meaningful detail;
- `WARN` if a project description exceeds 60 to 80 words;
- `WARN` if a project has more than 3 highlights.

### 6. Education density
Education is usually a low-density section.

Warn when education becomes unusually verbose relative to its normal signal value.

The first version can keep this check simple, for example:
- warn if education entries accumulate too many subordinate details or unusually long text blobs.

### 7. Section balance
Evaluate whether the section proportions look unbalanced for a compact ATS-friendly resume.

At minimum, check:
- whether projects are denser than experience;
- whether the skills section is disproportionately large compared to experience detail;
- whether summary plus all bullets together suggest an overpacked compact resume.

Suggested examples:
- `WARN` if projects carry more bullet/detail mass than experience;
- `WARN` if skill count is greater than roughly 2x the number of experience bullets;
- `WARN` if total narrative word count strongly suggests poor one-page scanability in compact mode.

### 8. Placeholder and template-language leakage
Fail or warn when source content still contains obvious placeholder text.

Examples:
- `Your Name`
- `Company Name`
- `Target Position Title`
- `Optional:`
- `Tech1`, `Skill A`
- other sample-fixture text from `data/example.json`

This check should be especially useful for first-time users who copy the example file and forget to replace all placeholders.

### 9. Command requirement
The implementing agent must generate a new CLI command:

```bash
curriculum-gen lint-content <candidate_json>
```

This is not optional.

The backlog item is not complete if the analysis exists only as an internal helper with no CLI surface.

The command must:
- load candidate JSON through the existing loader path;
- run the density and balance checks;
- print a readable report with `OK`, `WARN`, and `FAIL`;
- return non-zero when failures are found.

## Severity Guidance
Recommended severity policy:

### Fail
Use `FAIL` for:
- missing critical structural content;
- empty required sections for a credible resume;
- clear placeholder leakage in submitted candidate data.

### Warn
Use `WARN` for:
- dense summaries;
- too many bullets in a role;
- overpacked skills categories;
- oversized projects sections;
- weak section balance;
- scanability problems.

### OK
Use `OK` for checks that pass clearly.

## Output Behavior
The command should print a readable diagnostic report.

Example shape:

```text
Content lint: data/candidate.json

[OK] Summary is present
[WARN] Summary is dense for fast scanning (92 words)
[OK] Experience section has 3 entries
[WARN] Role 'Senior Software Engineer' has 7 bullets; consider prioritizing the strongest 4-5
[WARN] Skills section is overpacked (34 items across 4 categories)
[WARN] Projects section is denser than experience section
[FAIL] Placeholder text detected: Target Position Title

Result: FAIL
```

Exit code behavior:
- `0` when no failures are found;
- non-zero when one or more failures are found;
- warnings alone should not fail the command.

## Implementation Direction
Recommended implementation shape:

- add a new module such as `src/curriculum_gen/content_lint.py`;
- keep lint rules separate from `loader.py`;
- allow the loader to remain focused on schema parsing, not editorial judgment;
- reuse dataclasses from `models.py`;
- implement small, explicit rule functions that append `OK`, `WARN`, and `FAIL` results.

Suggested architecture:
- `load_candidate()` parses JSON into the existing model;
- `lint_candidate(candidate: Candidate) -> int` runs structured checks;
- CLI command prints the report and exits consistently with `ats-check`.

## Acceptance Criteria
This task should be considered complete only if:

1. `curriculum-gen lint-content <candidate_json>` exists.
2. The command loads candidate JSON using the existing loader path.
3. Structural completeness is checked.
4. Summary density warnings exist.
5. Experience density warnings exist.
6. Skills density warnings exist.
7. Section-balance warnings exist.
8. Placeholder leakage from sample/example content is checked.
9. The command returns a non-zero exit code when failures are found.
10. The implementation stays deterministic and does not introduce LLM-based rewriting or keyword lists.

## Suggested Verification
The implementing agent should verify at least:

```bash
curriculum-gen lint-content data/candidate.json
curriculum-gen lint-content data/example.json
```

And ideally also:
- a fixture with empty summary;
- a fixture with overlong summary;
- a fixture with too many bullets in one role;
- a fixture with overpacked skills.

## Suggested Evolution Path
This task should be implemented in phases rather than all at once.

Recommended order:

1. Phase 1: deterministic density checks
   - structural completeness;
- summary density;
- experience density;
- skills density;
- section balance;
   - placeholder leakage;
- projects density.

2. Phase 2: editorial heuristics
- repetition;
- metric presence;
- weak bullet phrasing;
- summary quality.

3. Phase 3: correlation checks
- skills not evidenced elsewhere;
- seniority-aware warnings.

4. Phase 4: optional stricter modes
   - machine-readable output;
   - `--strict`;
   - `--json-report`;
   - selective rule enable/disable.

## Notes For The Implementing Agent
- Keep the first version practical and low-noise.
- Prefer a smaller set of trustworthy density rules over a large set of brittle heuristics.
- The agent executor must actually add the `lint-content` CLI command, not only helper code.
- Do not mix content lint with `ats-check` in this task.
- Do not mix this task with job-description matching.
- Do not auto-rewrite candidate text as part of the lint command.
