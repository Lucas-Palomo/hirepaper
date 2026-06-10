# 044 - Refine experience content hierarchy and keyword placement

**Date:** 2026-06-10  
**Agent:** opencode (deepseek-v4-flash)

## Context

The `standard` layout rendered experience entries with a suboptimal content
hierarchy: technologies appeared before the role summary, the role summary was
italicized (reading like a side note), and keywords competed with narrative
evidence.

## Changes Made

### `src/hirepaper/generator.py` — `_render_experience()`

Reordered the experience entry assembly:

```
Before:                    After:
header                     header
metadata                   metadata
technologies               role_summary (normal text)
role_summary (italic)      bullets
bullets                    technologies (smaller text)
```

- Moved technologies from before `role_summary` to **after** bullets.
- Moved `role_summary` before bullets as the narrative opener.
- Removed `\textit{}` wrapping from `role_summary` — renders as normal text.
- Added `\vspace{3pt}` between `role_summary` and bullets when both exist.
- Technologies now render with the new `\resumeTechSub` macro instead of
  `\resumeEntrySub`.

### `templates/standard.cls` — new `\resumeTechSub` macro

Added a dedicated macro for the technology/keyword line:

```latex
\newcommand{\resumeTechSub}[1]{%
  {\fontsize{8.5}{10.5}\selectfont\color{subdued} #1}\vspace{1pt}\par%
}
```

- Smaller font (8.5pt vs 9.5pt body) — visually de-emphasized.
- Subdued color — still ATS-extractable (`pdftotext` preserves it).
- Placed after bullets — reads as trailing technical context.

## Result

### Full density (with `role_summary`)

```
TechCorp Solutions                    Senior Software Engineer
São Paulo, SP                         Mar 2021 – Present
Led platform architecture and mentored a team of 8 engineers...
– Designed and implemented real-time data pipeline...
– Led migration of monolithic application...
Python, Kafka, PostgreSQL, Docker, Kubernetes, AWS
```

### Compact density (no `role_summary` — pre-existing policy)

```
TechCorp Solutions                    Senior Software Engineer
São Paulo, SP                         Mar 2021 – Present
– Designed and implemented real-time data pipeline...
– Led migration of monolithic application...
Python, Kafka, PostgreSQL, Docker, Kubernetes, AWS
```

### Acceptance criteria

| # | Criterion | Status |
|---|---|---|
| 1 | `role_summary` renders before bullets | ✅ |
| 2 | `role_summary` no longer in italics | ✅ |
| 3 | Visual pause between summary and bullets | ✅ (`\vspace{3pt}`) |
| 4 | Technology/keyword line after bullets | ✅ |
| 5 | Keyword line uses smaller secondary style | ✅ (new `\resumeTechSub`) |
| 6 | ATS extraction valid | ✅ |
| 7 | Packaged binary preserves hierarchy | ✅ |

## Verification

```bash
# source — both densities
./hirepaper-dev pdf generate data/candidate.json -o /tmp/exp-hierarchy-compact.pdf --density compact --locale en
./hirepaper-dev pdf check /tmp/exp-hierarchy-compact.pdf          # PASS

./hirepaper-dev pdf generate data/candidate.json -o /tmp/exp-hierarchy-full.pdf --density full --locale en
./hirepaper-dev pdf check /tmp/exp-hierarchy-full.pdf             # PASS with warnings

# packaged binary
.venv/bin/python build.py
./hirepaper pdf generate data/candidate.json -o /tmp/exp-hierarchy-pkg.pdf --locale en --density full
./hirepaper pdf check /tmp/exp-hierarchy-pkg.pdf                  # PASS with warnings
```

Extracted text confirms the ordering: summary → bullets → keywords.

## Residual Risks

- `compact` density already had `show_role_summary=False` — role summary
  remains hidden in compact mode. This is pre-existing density policy, not
  changed by this task.
- The `\resumeTechSub` font size (8.5pt) is near the readability floor —
  could be bumped to 9pt if feedback indicates it is too small.
