# 046 - Add structured achievement context without changing PDF bullet rendering

## Status
Completed

## Context
The project currently supports achievement bullets as visible text that renders
well in the PDF resume.

There is growing value in preserving more structured internal meaning for those
bullets, especially for LLM-assisted workflows such as:

- content matching;
- candidate tailoring;
- LinkedIn generation;
- future rewrite or summarization helpers.

A natural structure for that internal meaning is a STAR-like breakdown:

- action
- result
- metrics

However, rendering STAR fields directly into the visible PDF bullet text creates
awkward output. A bullet that reads naturally as a single sentence often becomes
mechanical when rendered as concatenated `action + result + metrics`.

Example problem pattern:

- natural visible bullet:
  - one fluent sentence
- rendered STAR bullet:
  - split clauses joined mechanically, often with punctuation that feels like
    internal notation instead of polished resume writing

This task exists to preserve structured semantic context for AI workflows
without degrading visible PDF quality.

## Goal
Extend the achievement data model so that a visible bullet can keep a natural
`summary` for rendering, while also optionally storing structured semantic
context for LLM-facing workflows.

## Product Decision
The visible PDF bullet remains summary-first.

That means:

- `summary` remains the canonical field for visible bullet rendering;
- structured STAR-like data is stored as optional internal context;
- the default PDF layout must not render `action`, `result`, or `metrics`
  directly as separate visible clauses unless a future task explicitly changes
  that presentation model.

This task is about enriching the source model, not changing how bullets read in
the standard resume output.

## Proposed Data Shape
Recommended direction:

```json
{
  "summary": "Natural visible bullet text.",
  "context": {
    "action": "What was done.",
    "result": "What changed or improved.",
    "metrics": "Any concrete evidence or measurement."
  }
}
```

`context` should be optional.

The existing simpler achievement forms should remain compatible where practical.

## Why This Task Exists
The project now serves two different consumers:

1. human readers of the final PDF;
2. AI/analysis workflows that benefit from structured meaning.

Those two consumers do not need the same surface representation.

For human readers:
- natural language bullets are better

For AI workflows:
- structured context is better

Trying to force one representation to serve both equally well leads to worse
results in at least one of them.

## In Scope
### Required
1. Achievement schema/model support for optional structured context
2. Loader support for that schema
3. Preserve current PDF bullet rendering from `summary`
4. Make structured context available to LLM-facing workflows

### LLM-facing workflows to review
- `content match`
- `content tailor`
- `linkedin generate`

### Explicitly Out of Scope
- changing the standard PDF bullet renderer to display STAR fields directly
- redesigning the resume bullet writing style
- forcing every achievement to include structured context

## Scope
This task may update:

- `src/hirepaper/models.py`
- `src/hirepaper/loader.py`
- `src/hirepaper/generator.py`
- `src/hirepaper/content_match.py`
- `src/hirepaper/content_tailor.py`
- `src/hirepaper/linkedin_generate.py`
- `assets/schemas/candidate.schema.json`
- `README.md`
- `project.md`
- `docs/content.md`
- `docs/file-map.md`
- example candidate JSON files
- `sdd/history/`

This task may add:

- new helper functions for achievement serialization into LLM payloads
- optional validation rules for `context`

This task should not:

- break existing candidate files that only use `summary`
- require `context` for every achievement
- make the PDF renderer depend on `context` for normal output

## Required Behavior

### 1. `summary` remains the visible render source
For standard resume rendering:

- if `summary` exists, it should continue to render as the visible bullet text;
- `context.action`, `context.result`, and `context.metrics` should not be
  concatenated into visible PDF bullet text by default.

This preserves fluency and layout quality.

### 2. Structured context is optional and non-breaking
Candidate files that use the current simple structure must remain valid.

Examples that should continue to work:

```json
{
  "summary": "Implemented backend integrations for checkout flows."
}
```

and legacy shapes currently supported by the project:

```json
{
  "action": "Implemented backend integrations.",
  "result": "Stabilized checkout flows.",
  "metrics": "Reduced support incidents."
}
```

If the project keeps backward compatibility for legacy achievement fields, the
loader should map them coherently.

### 3. Structured context should be available to AI workflows
When building payloads for LLM-oriented commands, the structured context should
be preserved when present.

Required outcome:

- AI workflows can access both:
  - the polished visible `summary`
  - the decomposed `context`

This enables future prompting and reasoning to use finer-grained evidence
without forcing the visible bullet text to become mechanical.

### 4. Schema should reflect the dual purpose clearly
The candidate schema should describe:

- `summary` as visible bullet text
- `context` as optional structured semantic metadata

The schema should not imply that `context` is rendered directly in the PDF.

## Design Guidance

### Preferred model direction
The `Achievement` dataclass should evolve toward something like:

```python
@dataclass
class AchievementContext:
    action: Optional[str] = None
    result: Optional[str] = None
    metrics: Optional[str] = None


@dataclass
class Achievement:
    summary: Optional[str] = None
    context: Optional[AchievementContext] = None
    # legacy compatibility fields may remain temporarily if needed
```

The exact shape may differ, but the separation of visible summary and optional
structured context should be preserved.

### Backward compatibility guidance
The current project already supports achievements with fields such as:

- `summary`
- `action`
- `result`
- `metrics`
- `situation`
- `task`

This task should not casually break those existing files.

Recommended direction:

- keep loading legacy fields;
- optionally normalize them into `context` internally;
- continue rendering `summary` when present;
- define deterministic fallback behavior when `summary` is absent.

### Rendering fallback guidance
If an achievement has no `summary`, the renderer may still build a bullet from
legacy fields as it does today.

But that fallback is a compatibility path, not the preferred authoring model.

Preferred authoring model after this task:

- human-facing bullet in `summary`
- optional STAR-like semantics in `context`

## Documentation Requirements
When implemented, documentation should explain:

- why `summary` remains the visible bullet source;
- what `context` is for;
- that `context` is optional;
- how legacy achievement fields are treated.

At least one example should show:

```json
{
  "summary": "Natural visible bullet text.",
  "context": {
    "action": "...",
    "result": "...",
    "metrics": "..."
  }
}
```

## Acceptance Criteria
This task is complete only if all of the following are true:

1. Candidate data may include optional structured achievement context.
2. Existing summary-based bullets still render the same visible PDF output.
3. PDF rendering does not become mechanically STAR-formatted by default.
4. LLM-facing workflows can access structured context when present.
5. Existing simple/legacy achievement inputs remain materially compatible.
6. Documentation clearly explains the distinction between visible `summary` and
   structured `context`.

## Recommended Verification
At minimum verify:

```bash
./hirepaper-dev content lint data/candidate.json
./hirepaper-dev pdf generate data/candidate.json -o output/achievement-context.pdf --density compact --locale en
./hirepaper-dev pdf check output/achievement-context.pdf
```

Also verify one candidate fixture using:

- `summary` only
- `summary` + `context`
- legacy `action/result/metrics` fields without `context`

For LLM-oriented flows, verify at minimum that the structured payload includes
the context when present, even if no live endpoint is configured.

If packaged-binary behavior is in scope, also rebuild and smoke-test `./hirepaper`.

## Notes For The Implementing Agent
- Do not let the internal structure leak into awkward visible prose.
- Treat `summary` as presentation text and `context` as semantic support.
- Preserve compatibility intentionally; this task touches a source authoring
  contract that may already exist in real files.
