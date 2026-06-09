# 033 - Refine education entry hierarchy in `standard` layout

## Status
Completed

## Context
The current `standard` layout renders education entries with this effective
hierarchy:

```text
Institution                     Degree / Period
Location, GPA / Honors
```

In the current generator, education is assembled so that:

- the institution is treated as the primary left-side title;
- the degree is grouped with the date range in the right-side slot;
- location, GPA, and honors are collapsed together into a subordinate line.

That structure is functional, but it is not the best hierarchy for education.
The most important signal in an education entry is usually the degree/course,
followed by the institution, then location and period, with GPA/honors as
optional supporting details.

The current layout makes the entry feel mechanically mapped to the generic
`\resumeEntry` structure rather than intentionally composed for education.

## Goal
Adjust the education section in the `standard` layout so each entry follows this
hierarchy:

```text
Degree / Course    Institution
Location           Period
Extras: GPA, Honors
```

Or, stated semantically:

- first line: course/degree + institution
- second line: location + period
- optional third line: extras such as GPA and honors

This should produce a clearer and more natural education presentation without
reducing ATS safety.

## Product Decision
Education should not be treated as a simple mirror of experience layout.

Required priority order for each education entry:

1. degree/course
2. institution
3. location
4. date range
5. extras such as GPA and honors

Rationale:

- recruiters typically scan the degree first;
- the institution is still important, but secondary to the credential itself;
- period and location are supporting metadata;
- GPA and honors are optional details and should not compete with the main
  education identity.

## Scope
This task may update:

- `src/curriculum_gen/generator.py`
- `templates/standard.cls`
- `templates/standard.tex` if needed
- `project.md` if education layout behavior should be clarified
- `sdd/history/`

This task should not:

- change the candidate schema;
- redesign unrelated sections;
- alter education data semantics;
- remove GPA or honors support;
- widen into a full header or experience layout refactor.

## Current Undesired Structure
Current effective structure:

```text
University Name                  Degree / Jan 2018 -- Dec 2022
City, State / GPA: 3.7 / Summa Cum Laude
```

Problems with this structure:

- the degree is visually subordinated to the institution;
- period is packed into the same slot as the degree;
- GPA and honors are mixed into the same line as location;
- the overall block feels dense and less intentional than experience entries.

## Target Structure
Target effective structure:

```text
Bachelor of Science in Computer Science    Universidade de São Paulo
São Paulo, SP                              Feb 2012 -- Dec 2016
GPA: 3.7 · Summa Cum Laude
```

Equivalent simplified pattern:

```text
Course / Degree    University
Location           Period
Extras
```

Where `Extras` is optional and may contain:

- `GPA: ...`
- honors/distinctions such as `Summa Cum Laude`
- both, when both exist

## Required Behavior

### 1. First-line hierarchy
The first education line must prioritize the degree/course as the primary value.

Required behavior:

- degree/course should appear in the dominant left-side position;
- institution should appear alongside it as the paired secondary value;
- period must not be packed into the same field as the degree.

### 2. Second-line metadata
Location and period should be rendered together as the education metadata line.

Required behavior:

- location remains visible when present;
- period remains visible when present;
- the line should read as metadata, not as the primary identity of the entry.

Preferred pattern:

```text
São Paulo, SP    Feb 2012 -- Dec 2016
```

### 3. Optional extras line
GPA and honors should render on their own optional subordinate line.

Required behavior:

- if only GPA exists, render only GPA;
- if only honors exists, render only honors;
- if both exist, render both in one clean subordinate line;
- GPA/honors must not be collapsed into the location/period line.

Acceptable examples:

```text
GPA: 3.7
```

```text
Summa Cum Laude
```

```text
GPA: 3.7 · Summa Cum Laude
```

### 4. Concise but not collapsed
Education should remain compact, but it should not look visually collapsed into
one and a half lines of overloaded metadata.

The final structure should feel:

- concise;
- readable;
- aligned with the overall hierarchy of the `standard` layout;
- intentionally composed rather than mechanically reused.

### 5. ATS-safe text preservation
The change must preserve:

- visible degree/course text;
- visible institution text;
- visible location;
- visible dates;
- visible GPA/honors when present;
- sensible extraction order in `pdftotext`.

The task is not complete if the PDF looks better visually but extraction order
or visible detail quality regresses.

## Recommended Implementation Direction
The exact implementation is up to the implementing agent, but the education
layout should no longer force the entry into the current shape:

- `institution` as left primary field;
- `degree / period` as right primary field;
- `location / GPA / honors` as one merged sub-line.

Acceptable directions may include:

- reusing `\resumeEntry` with education-specific field ordering;
- adding a dedicated education macro for better structure;
- rendering an education header block plus one optional sub-line for extras.

Preferred outcome:
- minimal structural complexity;
- explicit education hierarchy;
- stable spacing and extraction behavior.

## Relationship With Existing Task History
An earlier task already established that GPA and honors should not be packed into
the main degree line.

This task refines that direction further by specifying the full desired
education hierarchy:

- degree before institution;
- location with period;
- GPA/honors as extras.

If implementation notes reference previous layout work, they should document how
this task tightens the education structure rather than reopening unrelated
layout decisions.

## Verification
Minimum verification should include visual and ATS-safe extraction checks.

### Source-mode generation

```bash
./curriculum-gen-dev pdf generate data/candidate.json --output /tmp/education-layout.pdf --density compact --locale en
./curriculum-gen-dev pdf check /tmp/education-layout.pdf
pdftotext /tmp/education-layout.pdf -
pdftoppm -png /tmp/education-layout.pdf /tmp/education-layout
```

### Fixture coverage
The implementing agent should verify at least:

- one education entry with both GPA and honors;
- one entry with only GPA or only honors if available, or a temporary fixture;
- one entry with no extras.

This is necessary to confirm the optional third line behaves correctly.

### Packaged verification

```bash
.venv/bin/python build.py
./curriculum-gen pdf generate data/candidate.json --output /tmp/education-layout-packaged.pdf --density compact --locale en
./curriculum-gen pdf check /tmp/education-layout-packaged.pdf
```

## Expected Verification Outcomes
The implementing agent should confirm:

1. education entries now render with degree/course before institution;
2. location and period appear as the metadata line;
3. GPA and honors render on a separate optional extras line;
4. extracted text still preserves readable education ordering;
5. source and packaged execution behave consistently.

## Acceptance Criteria
1. Education entries in the `standard` layout no longer render as `institution`
   primary + `degree / period` secondary.
2. Education entries render with degree/course as the primary first-line value.
3. Institution remains visible on the first line as the paired secondary value.
4. Location and period render together on the second line.
5. GPA and honors render on a separate optional extras line.
6. ATS-safe visible-text behavior is preserved.
7. The change is verified in source mode and packaged mode.
8. A history entry records the implementation, rationale, and verification.

## Notes For The Implementing Agent
- Treat education as its own hierarchy, not as a forced clone of experience.
- Prefer clarity of credential presentation over generic macro reuse.
- Keep optional extras subordinate.
- Validate both rendered appearance and extracted text.
