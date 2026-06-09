# 007 — Optimize candidate input schema and layout coverage

**Date:** 2026-05-27
**Agent:** opencode (deepseek-v4-flash)

---

## Context

The input schema was narrow for real-world resume authoring. Several high-value
candidate data points were missing from both the JSON schema and the LaTeX layout.

## Changes

### Schema additions

| Section | New fields |
|---------|-----------|
| `personal` | `headline` — professional title below name |
| `experience` | `technologies`, `role_summary`, `scope`, `achievements[]` (STAR-like) |
| `education` | `honors` (e.g., Summa Cum Laude) |
| `project` | `role`, `start_date`, `end_date`, `highlights[]` |
| `certification` | `credential_url` |
| — | **`awards[]`** — new top-level section |
| — | **`volunteer[]`** — new top-level section |

### Achievement model (`Achievement`)

STAR-like structured accomplishments:
- `situation`, `task`, `action`, `result`, `metrics`, `summary`
- Generator compresses available fields into concise ATS-friendly bullets
- Falls back to `summary` if present, or builds from action/result/metrics

### Backward compatibility

All new fields are optional. `highlights` is still supported on `experience`
and `project` — used when `achievements` is absent. Old JSON files without
new fields compile without errors.

### LaTeX class (`resume.cls`)

New commands:
- `\resumeHeadline{text}` — italic subtitle below name
- `\resumeEntrySub{text}` — metadata line (tech stack, role summary, etc.)
- `\resumeAward{name}{issuer}{date}` — compact award entry
- `\resumeVolunteer{org}{position}{dates}{location}` — volunteer entry

### Template (`resume.tex`)

New placeholders: `{HEADLINE}`, `{SECTION_AWARDS}`, `{SECTION_VOLUNTEER}`

Template also hardened against empty replacements (added `%` to prevent
blank-line LaTeX errors when optional fields are absent).

### Sample data (`data/candidate.json`)

Updated with: headline, technologies per role, STAR achievements on one role,
education honors, project role/dates/highlights, certification URL,
one award, one volunteer entry.

### Locale

New keys: `section.awards`, `section.volunteer`
Translations: en (Awards, Volunteer), pt-BR (Prêmios, Voluntariado)

## Verification

```bash
# Full candidate
./curriculum-gen generate data/candidate.json -o output/resume.pdf

# Backward compat (minimal JSON)
./curriculum-gen generate minimal.json -o output/minimal.pdf

# pt-BR with new sections
./curriculum-gen generate data/candidate.json -o output/curriculo.pdf -l pt-BR
```
