# 036 - Refine `Certifications` and soften `Languages` within the utility band

## Status
Completed

## Context
The current `standard` layout uses a compact two-column utility band when
`Certifications` and `Languages` coexist.

That structural choice is acceptable and should be preserved.

However, the internal composition of those two columns is not well balanced.

### Certifications problems
The current certification macro is too compressed for longer certification
names. It effectively tries to keep:

- certification name
- issuer
- date

in a very tight one-line hierarchy.

That becomes fragile for entries such as:

```text
Certified Kubernetes Administrator (CKA) — CNCF    Nov 2022
```

Even after removing `credential_url`, the certification entry still carries too
much information in too little horizontal space.

### Languages problems
The `Languages` column is visually louder than it needs to be for a utility
section.

Today, each language label is strongly bolded, which makes the column call too
much attention to itself relative to:

- the supporting nature of language proficiency;
- the neighboring certifications column;
- the intended hierarchy of the utility band.

The result is a utility band where:

- certifications are structurally cramped;
- languages visually “shout” more than they should.

## Goal
Keep the two-column utility band, but improve the internal hierarchy of both
columns.

Target outcomes:

- `Certifications` becomes easier to scan, especially for long names;
- `Languages` becomes calmer and more utility-like;
- the band remains compact, ATS-safe, and visually balanced;
- the right column does not visually overpower the left column.

## Product Decision
The utility band should remain in a two-column layout.

This task is not about removing columns.

Instead, it should improve the composition inside the columns:

- `Certifications` should gain a clearer per-entry hierarchy with less forced
  horizontal compression;
- `Languages` should be visually softened so it reads as supporting metadata,
  not as a dominant section.

## Scope
This task may update:

- `src/curriculum_gen/generator.py`
- `templates/standard.cls`
- `templates/standard.tex` if needed
- `project.md` if utility-band layout behavior should be clarified
- `sdd/history/`

This task should not:

- remove the two-column utility band;
- move `Languages` or `Certifications` out of the band by default;
- redesign unrelated sections;
- change the candidate schema;
- widen into a complete utility-sections overhaul.

## Certifications Requirements

### Current undesired behavior
Current effective certification composition is close to:

```text
Certification Name — Issuer                         Date
```

Problems:

- long names become cramped quickly;
- issuer/date alignment becomes fragile;
- entries feel over-compressed inside a narrow column;
- the section is too close to line-breaking or awkward wrapping behavior.

### Target certification structure
Each certification entry should become a clearer compact block, such as:

```text
Certified Kubernetes Administrator (CKA)
CNCF                                            Nov 2022
```

Equivalent hierarchy:

- first line: certification name
- second line: issuer on the left, date on the right

Required behavior:

- certification name should be the dominant first-line value;
- issuer should remain visible and subordinate;
- date should remain visible and easy to scan;
- the entry should remain compact but no longer force all primary fields into
  one overloaded line.

If a certification name is short, the layout may still appear compact, but the
structural intent should remain the same.

## Languages Requirements

### Current undesired behavior
Languages currently render with too much emphasis for a utility section.

Effective current tone:

```text
Portuguese: Native
English: Fluent (C2)
Spanish: Intermediate (B1)
```

with the language names strongly bolded.

Problems:

- the column draws too much attention relative to its importance;
- bold labels create unnecessary visual contrast;
- the right utility column feels louder than the left.

### Target languages tone
Languages should remain readable, but visually calmer.

Acceptable direction:

- reduce the weight of the language label;
- keep proficiency readable in regular text;
- preserve a compact utility-section rhythm;
- avoid strong per-line emphasis that competes with certifications.

Examples of acceptable visual intent:

```text
Portuguese: Native
English: Fluent (C2)
Spanish: Intermediate (B1)
```

but with noticeably softer styling than the current bold-heavy treatment.

This task is about visual hierarchy, not changing the text content format.

## Required Behavior

### 1. Preserve the two-column band
The utility band must remain a two-column composition when both sections are
present.

This task must not flatten `Certifications` and `Languages` into a single-column
flow.

### 2. Certification entry hierarchy
Each certification entry must follow this hierarchy:

- line 1: certification name
- line 2: issuer on the left, date on the right

The date must remain visually associated with the certification entry and should
not drift into ambiguous placement.

### 3. Language visual softening
Language entries must be rendered with less visual aggression than the current
bold-heavy treatment.

Required outcome:

- `Languages` remains clearly readable;
- `Languages` no longer visually dominates the utility band;
- the right column feels supportive rather than loud.

### 4. Compact but stable spacing
Both columns should remain compact, but the spacing must be stable enough that:

- certification entries do not visually collide;
- languages lines do not look cramped or overly decorative;
- the band still reads as a clean utility area.

### 5. ATS-safe extraction preservation
The change must preserve:

- visible certification name;
- visible issuer;
- visible certification date;
- visible language name;
- visible language proficiency;
- sensible extracted reading order.

This task is not complete if the band looks better visually but extracted text
quality regresses.

## Recommended Implementation Direction
The exact implementation is up to the implementing agent, but the likely shape
is:

- replace the current one-line certification macro with a small two-line
  certification entry macro;
- tone down the language macro styling so it carries less emphasis;
- keep the outer utility-band column structure unchanged.

Preferred outcome:

- same high-level band structure;
- better entry-level hierarchy;
- lower visual noise;
- more balanced left/right column weight.

## Verification
Minimum verification should include visual and ATS-safe extraction checks.

### Source-mode generation

```bash
./curriculum-gen-dev pdf generate data/candidate.json --output /tmp/utility-band-refined.pdf --density compact --locale en
./curriculum-gen-dev pdf check /tmp/utility-band-refined.pdf
pdftotext /tmp/utility-band-refined.pdf - | sed -n '/Certifications/,$p'
pdftoppm -png /tmp/utility-band-refined.pdf /tmp/utility-band-refined
```

### Fixture coverage
The implementing agent should verify at least:

- one long certification name;
- one short certification name;
- multiple language entries.

This is necessary to confirm the certification hierarchy and language tone hold
under realistic utility-band density.

### Packaged verification

```bash
.venv/bin/python build.py
./curriculum-gen pdf generate data/candidate.json --output /tmp/utility-band-refined-packaged.pdf --density compact --locale en
./curriculum-gen pdf check /tmp/utility-band-refined-packaged.pdf
```

## Expected Verification Outcomes
The implementing agent should confirm:

1. the two-column utility band is preserved;
2. certifications now render with name first, then issuer/date on a second line;
3. languages render with visibly softer emphasis;
4. the utility band feels more balanced and less noisy;
5. extracted text still preserves readable certification and language content;
6. source and packaged execution behave consistently.

## Acceptance Criteria
1. The `Certifications` + `Languages` utility band remains two-column.
2. Certification entries no longer render as a single over-compressed line.
3. Certification entries render certification name first, then issuer/date on a
   second line.
4. Language entries are visually softened relative to the current bold-heavy
   treatment.
5. ATS-safe visible-text behavior is preserved.
6. The change is verified in source mode and packaged mode.
7. A history entry records the implementation, rationale, and verification.

## Notes For The Implementing Agent
- Keep the column layout; refine the internals.
- Treat `Languages` as supporting metadata, not a dominant section.
- Treat long certification names as a first-class validation case.
- Validate both rendered appearance and extracted text.
