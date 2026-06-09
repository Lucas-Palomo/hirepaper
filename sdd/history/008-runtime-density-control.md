# 008 — Runtime density control for standard layout

**Date:** 2026-05-27
**Agent:** opencode (deepseek-v4-flash)

---

## Context

The generated PDF could become too dense when the candidate JSON contained many
sections, links, and bullets. Rendering decisions belonged in the CLI, not in
the candidate data.

## Changes

### 1. `DensityPolicy` model (`src/curriculum_gen/density.py`)

Frozen dataclass with explicit limits for each rendering aspect.

| Field | Compact | Full |
|-------|---------|------|
| `max_links` | 3 | 4 |
| `max_experience_items` | 3 | all |
| `max_experience_bullets` | 2 | 4 |
| `show_role_summary` | false | true |
| `show_experience_technologies` | true | true |
| `max_skills_per_category` | 5 | 8 |
| `max_projects` | 1 | 3 |
| `max_project_bullets` | 1 | 2 |
| `show_awards` | false | true |
| `show_volunteer` | false | true |

Default: `compact`.

### 2. CLI integration

Added `--density {compact,full}` option to `generate`. Validates input against
`DENSITY_MAP`. Passes policy to generator. Help documents both options.

### 3. Generator refactored

- All section renderers accept `DensityPolicy`.
- Links, experience items, bullets, projects, and skills are all capped per policy.
- Awards and Volunteer sections are conditionally rendered based on `show_awards`/`show_volunteer`.
- Empty sections (when content is suppressed) are removed from the output via
  regex stripping of `\resumeSection{}` lines.

### 4. Bullet prioritization

`_bullet_score()` assigns points based on:
- presence of digits (+3)
- percentage values (+2)
- action-result connector (+2)
- strong action verbs (+1)
- scale keywords (million, users, etc.) (+1)

Bullets are sorted by score before applying per-role caps, ensuring the
strongest signals survive density limits.

### 5. Backward compatibility

`generate_latex()` defaults `density="compact"`. Existing callers (CLI without
`--density`) continue to work with no changes.

## Verification

```bash
./curriculum-gen generate data/candidate.json -o output/resume-compact.pdf
./curriculum-gen generate data/candidate.json -o output/resume-full.pdf --density full
```

Compact: 7 sections, 7 bullets, 3 links, no awards/volunteer
Full: 9 sections, 14 bullets, 4 links, includes awards and volunteer
Both produce valid 2-page PDFs.
