# 046 - Add structured achievement context without changing PDF bullet rendering

**Date:** 2026-06-10  
**Agent:** opencode (deepseek-v4-flash)

## Context

The project serves two consumers — human readers of the final PDF and
LLM-facing workflows (content match, content tailor, LinkedIn generate) —

but both used the same flat achievement model. Adding structured semantic
context (action, result, metrics) enables AI workflows to reason about
evidence without forcing the visible PDF text to become mechanical.

## Changes Made

### `src/hirepaper/models.py`

Added `AchievementContext` dataclass:

```python
@dataclass
class AchievementContext:
    action: Optional[str] = None
    result: Optional[str] = None
    metrics: Optional[str] = None
```

Updated `Achievement` with optional `context` field:

```python
@dataclass
class Achievement:
    ...
    context: Optional[AchievementContext] = None
```

### `src/hirepaper/loader.py` — `_parse_achievements()`

- Parses `context` from raw JSON when present.
- **Normalizes legacy top-level fields**: when `context` is absent but
  `action`/`result`/`metrics` exist at the achievement root, they are
  automatically promoted into `context`. This keeps the LLM payload
  consistent regardless of authoring style.

### `assets/schemas/candidate.schema.json`

- Added `context` as an optional property of `achievement` with `action`,
  `result`, `metrics` sub-fields.
- Added `description` annotations explaining that `summary` is the visible
  bullet text and `context` is semantic metadata for AI workflows.

### `src/hirepaper/linkedin_generate.py` and `src/hirepaper/content_tailor.py`

- LLM payload builders now include `context` in the achievement payload
  when present.

`content_match.py` was not updated because it sends `highlights` (plain
strings), not structured achievements.

### Not changed

- `generator.py` — `_render_achievement_bullet()` already renders `summary`
  first, falling back to legacy fields. `context` is never rendered directly.
  No change needed.
- PDF output — `summary` remains the canonical visible source. No formatting
  change.

## Verification

```bash
# Existing files unchanged
./hirepaper-dev content lint data/candidate.json
./hirepaper-dev pdf generate data/candidate.json -o /tmp/ach-base.pdf --locale en --density compact
./hirepaper-dev pdf check /tmp/ach-base.pdf

# summary + context
./hirepaper-dev pdf generate /tmp/ach-context-fixture.json -o /tmp/ach-context.pdf --locale en --density compact
./hirepaper-dev pdf check /tmp/ach-context.pdf
# → text extraction confirms bullet reads from summary, not context

# Legacy action/result/metrics
./hirepaper-dev pdf generate /tmp/ach-legacy-fixture.json -o /tmp/ach-legacy.pdf --locale en --density compact
./hirepaper-dev pdf check /tmp/ach-legacy.pdf

# Packaged binary
.venv/bin/python build.py
./hirepaper pdf generate data/candidate.json -o /tmp/ach-pkg.pdf --locale en --density compact
./hirepaper pdf check /tmp/ach-pkg.pdf
```

All pass. No `context` text leaks into PDF extracted text.

## Supported authoring patterns

| Pattern | Example | Works |
|---|---|---|
| `summary` only | `"summary": "Natural bullet."` | ✅ |
| `summary` + `context` | `"summary": "...", "context": {"action": ..., "result": ..., "metrics": ...}` | ✅ |
| Legacy `action/result/metrics` | `"action": "...", "result": "...", "metrics": "..."` | ✅ (normalized) |
| Mixed legacy + summary | `"summary": "...", "action": "...", "result": "..."` | ✅ |
