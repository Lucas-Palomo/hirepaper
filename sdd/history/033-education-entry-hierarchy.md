# 033 - Refine education entry hierarchy in `standard` layout

**Date:** 2026-06-08
**Agent:** opencode (deepseek-v4-flash)

---

## Context

The `standard` layout rendered education entries using the generic `\resumeEntry` structure with:
- `institution` as the primary left-side bold title;
- `degree / period` grouped together as the right-side bold slot;
- `location / GPA / honors` collapsed into a single subordinate line.

This overloading made education feel mechanically mapped to the experience macro rather than intentionally composed. The degree (the most important signal) was visually subordinated.

## Changes Made

### `src/curriculum_gen/generator.py` — `_render_education()`

Reordered the `\resumeEntry` arguments and extracted GPA/honors to a separate optional line:

**Before:**
```
University Name                      Degree / Period
Location / GPA / Honors
```

**After:**
```
Degree / Course                      Institution
Location                             Period
GPA: 3.7 · Summa Cum Laude          (optional extras line)
```

Specific changes:
- `\resumeEntry` now uses `degree` as arg #1 (bold left) and `institution` as arg #2 (bold right), instead of the reverse.
- `period` is arg #3 (right subdued) and `location` is arg #4 (left subdued), instead of being collapsed together.
- GPA and honors are no longer in the location line. They render on a separate `\resumeEntrySub` line only when present, using `\textbullet{}` as separator when both exist.

No macro or template changes were needed — the existing `\resumeEntry` and `\resumeEntrySub` commands handle the new structure.

## Verification

### Source-mode

```bash
./curriculum-gen-dev pdf generate data/candidate.json --output /tmp/education-layout.pdf --density compact --locale en
./curriculum-gen-dev pdf check /tmp/education-layout.pdf               # PASS (15 checks)
pdftotext /tmp/education-layout.pdf -    # All education data present and readable

./curriculum-gen-dev pdf generate data/candidate.json --output /tmp/education-layout-full.pdf --density full --locale en
./curriculum-gen-dev pdf check /tmp/education-layout-full.pdf           # PASS with warnings (1 warn, 15 ok)
```

### Extracted text (education section)

```
Bachelor of Science in Computer Science
São Paulo, SP

Universidade de São Paulo (USP)
Feb 2012 – Dec 2016

GPA: 3.7 • Summa Cum Laude
```

All five data points present:
- Degree: Bachelor of Science in Computer Science
- Institution: Universidade de São Paulo (USP)
- Location: São Paulo, SP
- Period: Feb 2012 – Dec 2016
- Extras: GPA 3.7, Summa Cum Laude

The column-based reading order (left column before right column) is inherent to the tabular layout and mirrors how experience entries are extracted. ATS check passes with all required content.

### Packaged mode

```bash
.venv/bin/python build.py
./curriculum-gen pdf generate data/candidate.json --output /tmp/education-layout-packaged.pdf --density compact --locale en
./curriculum-gen pdf check /tmp/education-layout-packaged.pdf           # PASS (15 checks)
```

## Key outcomes

1. Degree/course is now the primary first-line value.
2. Institution remains visible on the first line as the paired secondary value.
3. Location and period render together on the second line as metadata.
4. GPA and honors render on a separate optional extras line only when present.
5. ATS-safe visible-text behavior is preserved.

### `\mbox` wrapping on all bold entry fields

After applying `\mbox` to education fields (degree, institution), extended the same pattern to all `\resumeEntry` bold fields for consistency:
- **Experience**: `\mbox{company}` and `\mbox{position}`
- **Projects**: `\mbox{name}` and `\mbox{role}`
- **Volunteer**: `\mbox{organization}` and `\mbox{position}` (via `\resumeVolunteer`)

This prevents line breaks within any primary bold field across the entire resume, matching the existing pattern in header contact items and links.

## Decisions & Tradeoffs

- Chose to reuse existing `\resumeEntry` with reordered arguments rather than creating a new education-specific macro — zero template changes, minimal diff.
- GPA/honors use `\textbullet{}` as separator — reliable in LaTeX across all PDF viewers.
- The tabular layout causes pdftotext to read left column before right column, which is the same behavior as experience entries and acceptable for ATS extraction.
- `\mbox` wrapping applied to all bold entry fields for consistent atomicity — company, position, project name, role, organization all behave the same way.
