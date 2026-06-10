# 045 - Add JSONC support for candidate and related JSON inputs

## Status
Completed

## Context
The project currently loads candidate data with strict JSON parsing via
`json.loads(...)`.

That is correct for machine-only input, but it is unnecessarily rigid for the
actual authoring workflow used in this repository. Resume source files often
benefit from lightweight inline documentation such as:

- temporarily commenting out draft sections;
- leaving notes about wording choices;
- marking optional variants during tailoring;
- annotating fields that should be reviewed later.

Standard JSON does not allow comments, so users currently need to either:

- remove those notes before validation/generation; or
- keep context outside the file, which makes iterative editing worse.

This task exists to make authoring more ergonomic by supporting JSONC-style
comments in candidate and similar JSON inputs.

## Goal
Allow `hirepaper` to accept JSONC-style input for candidate source files and
other human-edited JSON artifacts where it improves the authoring workflow,
while preserving the same parsed data model after comments are stripped.

## Why This Task Exists
The input files in this project are not only machine payloads. They are also
working author documents.

Supporting comments is useful because it allows users to:

- explain why a bullet exists;
- keep alternate wording nearby during editing;
- annotate fields that should be trimmed or tailored;
- temporarily disable entries without moving them elsewhere.

This is an authoring and maintainability improvement, not a schema change.

## Product Decision
The project should accept JSONC as an input format for human-maintained source
files, but the in-memory contract remains standard parsed JSON data.

That means:

- comments are accepted in source files;
- comments are ignored during parsing;
- downstream loaders, validators, renderers, and generators still operate on
  normal Python dictionaries/dataclasses;
- emitted JSON artifacts should remain normal JSON unless a task explicitly
  decides otherwise.

This task is about input compatibility, not output format migration.

## In Scope
### Required
1. Candidate source loading through `load_candidate()`
2. CLI commands that read candidate JSON files

This includes, at minimum:

- `hirepaper content lint`
- `hirepaper content match`
- `hirepaper content tailor`
- `hirepaper linkedin generate`
- `hirepaper pdf generate`

### Strongly Recommended
3. Other repo-managed JSON inputs that are author-facing and edited by humans

Examples to evaluate:

- tailored candidate JSON outputs when later reused as inputs
- bundled example candidate JSON

### Explicitly Out of Scope
- changing output files from JSON to JSONC by default
- changing JSON Schema semantics
- allowing arbitrary non-JSON syntax beyond documented JSONC support

## Scope
This task may update:

- `src/hirepaper/loader.py`
- any JSON-reading helper modules that currently call `json.loads(...)`
- `README.md`
- `project.md`
- `docs/content.md`
- `docs/pdf.md`
- `docs/file-map.md`
- `assets/examples/candidate.example.json` if comments are added deliberately
- `sdd/history/`

This task may add:

- a small JSONC parsing helper module
- tests or verification fixtures using commented input files

This task should not:

- add a heavy dependency unless clearly justified;
- silently broaden parsing to a vague “almost JSON” format;
- break existing strict JSON inputs.

## Required Supported Syntax
At minimum, the parser should support standard JSON plus common JSONC comment
forms:

- line comments with `//`
- block comments with `/* ... */`

Trailing commas may be supported if the chosen approach naturally provides them,
but that is optional unless the implementation explicitly documents support.

If trailing commas are not supported, the docs should say so clearly.

## Required Behavior

### 1. Candidate files may contain comments
Files passed to candidate-reading workflows should parse successfully when they
contain supported JSONC comments.

Example intent:

```jsonc
{
  "summary": "Backend engineer with experience in e-commerce.",
  // Keep this role for LATAM-focused versions
  "experience": [
    {
      "company": "Example",
      "position": "Senior Backend Engineer"
    }
  ]
}
```

The parsed result must be equivalent to the same file with comments removed.

### 2. Existing strict JSON files must continue to work unchanged
This task must remain backward compatible with current valid JSON inputs.

### 3. Validation behavior must remain unchanged after parsing
After comments are stripped and the JSON is parsed:

- schema/required-field validation should behave exactly as before;
- dataclass mapping should behave exactly as before;
- command behavior should remain materially unchanged.

### 4. Error messages should remain clear
When an input file is invalid even after JSONC handling, the user should still
receive a useful parsing/validation error.

Avoid low-quality failures where comment stripping hides the real error
location without explanation.

## Design Guidance

### Preferred implementation direction
The project should centralize JSON/JSONC reading behind a small helper rather
than scattering ad hoc preprocessing across modules.

Recommended direction:

- add one helper that reads text and parses JSONC-compatible input;
- use that helper from `load_candidate()` and any similar human-facing JSON
  readers;
- keep the rest of the system unaware of whether comments were present.

### Dependency guidance
Prefer a small, explicit implementation or a lightweight dependency only if it
materially improves correctness and maintainability.

Do not add a dependency casually if comment handling can be implemented
reliably in a narrow helper.

### Output policy
Generated artifacts such as tailored candidate JSON should continue to be
written as standard JSON unless a future task explicitly introduces JSONC
output mode.

That keeps outputs deterministic and broadly interoperable.

## Documentation Requirements
When implemented, update docs to clarify:

- `candidate.json` may be authored as JSONC-style commented JSON;
- comments are accepted on input and ignored during parsing;
- outputs remain standard JSON;
- whether trailing commas are supported.

Documentation should not imply support for arbitrary JavaScript syntax.

## Acceptance Criteria
This task is complete only if all of the following are true:

1. Candidate-loading workflows accept JSONC comments.
2. Existing JSON inputs still work unchanged.
3. CLI commands that consume candidate JSON behave correctly with commented
   input files.
4. Parsed candidate data is identical to the same file with comments removed.
5. Documentation clearly states the supported comment behavior.

## Recommended Verification
At minimum verify:

```bash
./hirepaper-dev content lint /tmp/candidate-commented.json
./hirepaper-dev pdf generate /tmp/candidate-commented.json -o output/commented-input.pdf --locale en --density compact
./hirepaper-dev content match /tmp/candidate-commented.json data/vacancy.txt --format text
./hirepaper-dev linkedin generate /tmp/candidate-commented.json --output /tmp/linkedin-report.txt --format txt
```

Also verify a strict JSON file still works:

```bash
./hirepaper-dev content lint data/candidate.json
```

If packaged-binary behavior is in scope for the implementation, also verify:

```bash
.venv/bin/python build.py
./hirepaper content lint /tmp/candidate-commented.json
```

## Notes For The Implementing Agent
- Keep the parsing boundary narrow and explicit.
- Do not silently invent support for unrelated JSON5 features unless the task
  is deliberately expanded and documented.
- Treat this as an authoring UX improvement that must preserve deterministic
  downstream behavior.
