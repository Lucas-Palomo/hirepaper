# 018 - Redesign CLI subcommands for content and PDF workflows

## Status
Completed

## Context
The CLI started small and currently exposes flat top-level commands:

- `generate`
- `doctor`
- `ats-check`

This was sufficient while the project was mostly about JSON-to-PDF generation and ATS-safe PDF validation.

The product direction is now broader:
- content linting on source JSON;
- future content/job matching;
- future content tailoring;
- PDF generation;
- PDF validation.

If the CLI continues to grow with flat commands such as:
- `lint-content`
- `match-job`
- `tailor-job`
- `ats-check`
- `generate`

the command surface will become inconsistent and harder to teach.

The CLI should move to a subcommand model organized around workflow domains rather than historical implementation order.

## Goal
Redesign the CLI command structure so that it is grouped into coherent subcommand families for:
- content-source operations;
- PDF artifact operations;
- environment diagnostics.

This task is about CLI structure only.

It is not about implementing new matching or tailoring behavior yet.

## Scope Boundary
This task must only redesign the CLI command tree and route existing behavior into the new structure.

It must not:
- implement `content match` logic;
- implement `content tailor` logic;
- add LLM integration;
- add `pdf match`;
- change the underlying resume generation rules;
- expand ATS validation semantics beyond command naming and routing;
- redesign the candidate schema.

If placeholders or stubs are needed for future commands, they must be clearly marked as not-yet-implemented and must not pretend to perform matching or tailoring.

## Target CLI Shape
The target structure should be:

```bash
curriculum-gen doctor

curriculum-gen content lint <candidate_json>
curriculum-gen content match ...
curriculum-gen content tailor ...

curriculum-gen pdf generate <candidate_json> --output <pdf>
curriculum-gen pdf check <pdf>
```

Important:
- `pdf check` is the user-facing CLI name for the current ATS-safe PDF validation behavior;
- `content lint` is the user-facing CLI location for source-content linting;
- `content match` and `content tailor` must exist only if they are intentionally exposed as placeholders or explicitly deferred with clear behavior.
- the subcommand structure is the only canonical CLI shape after this task.

## Required Decisions
The implementing agent should make and document the following decisions:

### 1. Group names
Use:
- `content`
- `pdf`

Keep:
- `doctor`

Rationale:
- `content` owns source JSON analysis and transformation;
- `pdf` owns artifact generation and artifact validation;
- `doctor` remains a global environment check.

### 2. Current command mapping
Existing commands should map as follows:

- current `generate` -> `pdf generate`
- current `ats-check` -> `pdf check`
- current or planned `lint-content` -> `content lint`

### 3. Legacy command policy
There is no need to preserve legacy flat commands in this task.

The CLI is not officially published yet, so the old flat command surface should be removed rather than retained as compatibility baggage.

Required policy:
- remove legacy flat command entrypoints from the public CLI;
- do not keep compatibility aliases for `generate` or `ats-check`;
- make the new grouped command tree the only supported interface;
- update help text and docs accordingly.

### 4. Future placeholder policy
The CLI structure must make room for:
- `content match`
- `content tailor`

But this task must not implement their actual business logic.

Acceptable approaches:
- define the subcommand groups now and leave `match`/`tailor` out until their own tasks land;
- or expose them with a clear "not implemented yet" exit path.

Preferred approach:
- create the subcommand architecture now;
- include only stable, implemented commands in the public help unless there is a strong reason to expose placeholders.

## Required Outcomes

### 1. New subcommand structure
The CLI must support:

```bash
curriculum-gen doctor
curriculum-gen content lint <candidate_json>
curriculum-gen pdf generate <candidate_json> --output <pdf>
curriculum-gen pdf check <pdf>
```

### 2. Existing behavior preserved
The following existing capabilities must still work after the refactor:
- environment validation;
- PDF generation;
- ATS-safe PDF checking.

Behavior must be preserved through the new grouped commands, not through legacy aliases.

### 3. No false feature exposure
The CLI must not imply that `content match` or `content tailor` already work if they do not.

If they are visible, they must fail clearly with an explicit not-yet-implemented message and non-zero exit code.

### 4. Help text coherence
The top-level help and subgroup help must make the workflow understandable.

The structure should clearly suggest:
- content commands act on candidate source data;
- PDF commands act on generated or external PDF files.

## Recommended Implementation Direction
The implementing agent should refactor the Typer app structure to support nested command groups.

Possible shape:
- top-level app;
- nested `content_app`;
- nested `pdf_app`.

The exact internal code organization is up to the implementing agent, but the public CLI shape should match the target structure.

Recommended implementation principles:
- keep command wiring explicit;
- avoid broad rewrites unrelated to the CLI tree;
- preserve current behavior and error messaging where practical through the new command tree;
- keep module boundaries readable.

## Documentation Expectations
This task should update CLI-facing documentation where needed, including:
- help text strings;
- command examples in project docs if they become stale;
- any references that still present the old flat command shape as canonical.

At minimum, `project.md` should no longer describe only the old flat command model if the new one becomes canonical.

## Acceptance Criteria
This task should be considered complete only if:

1. The CLI is reorganized into subcommand groups.
2. `curriculum-gen pdf generate ...` exists.
3. `curriculum-gen pdf check ...` exists.
4. `curriculum-gen content lint ...` exists if the lint command task has already landed, or the structure cleanly accommodates it.
5. `doctor` still exists as a top-level command.
6. Existing generation and PDF-check behavior still work after the refactor.
7. Legacy flat commands are removed from the supported CLI surface.
8. The CLI does not falsely advertise implemented matching/tailoring logic.
9. Help text reflects the new command structure.

## Suggested Verification
The implementing agent should verify at least:

```bash
curriculum-gen --help
curriculum-gen doctor --help
curriculum-gen pdf --help
curriculum-gen pdf generate --help
curriculum-gen pdf check --help
curriculum-gen content --help
```

And, if `content lint` is already implemented by that time:

```bash
curriculum-gen content lint data/candidate.json
```

Also verify backward compatibility paths if they are preserved, for example:

```bash
curriculum-gen generate ...
curriculum-gen ats-check ...
```

In the final scope for this task, those legacy commands should no longer be supported. If invoked during verification, they should be treated as obsolete paths rather than required behavior.

## Relationship With Other Tasks
This task is intentionally structural.

It should land before or alongside feature tasks that depend on the new shape, especially:
- content lint;
- content match;
- content tailor.

But it must not absorb their implementation scope.

## Notes For The Implementing Agent
- Do not implement `pdf match` in this task.
- Do not implement actual matching or tailoring logic in this task.
- Focus on command architecture, migration safety, and help-text clarity.
- Prefer a CLI shape that scales cleanly as more content-oriented features are added.
- Do not retain legacy flat commands just to ease migration; that would create unnecessary backlog noise for an unpublished CLI.
