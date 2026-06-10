# 044 - Refine experience content hierarchy and keyword placement

## Status
Completed

## Context
The current `standard` experience layout mixes three different content layers
in a way that weakens reading order:

1. role/context narrative (`role_summary`)
2. evidence bullets (`achievements` / highlights rendered as bullets)
3. technical keyword line (`technologies`)

Today, the rendered experience block places the technology/keyword line before
the role summary. This causes two layout problems:

- the technical keyword line interrupts the narrative flow before the reader
  reaches the role summary;
- the role summary, which should introduce the experience, is visually treated
  as secondary supporting text rather than the lead-in to the bullets.

There is also a formatting issue: the role summary currently renders in italics,
which gives it the appearance of a side note rather than a first-class part of
the experience narrative.

This task exists to improve hierarchy, readability, and visual rhythm in the
experience block without compromising ATS extraction.

## Goal
Refine the experience-section layout so that:

- `role_summary` appears as normal text, not italicized;
- `role_summary` appears before the bullets as the narrative opener;
- a small visual pause separates `role_summary` from the bullets;
- the technology/keyword line moves to the end of the experience entry;
- the technology/keyword line renders in a smaller, secondary text style.

## Why This Task Exists
The current ordering prioritizes low-context technical tags above the
experience narrative.

That is the wrong reading hierarchy for humans:

- the reader should first understand the role and scope of the work;
- then read the strongest evidence bullets;
- then optionally scan the technical keywords as reinforcement.

This task is not about changing content semantics. It is about presenting the
same information in a more defensible order.

## Affected Surface
Primary:

- experience entries in `standard` layout

Likely implementation areas:

- `src/hirepaper/generator.py`
- `templates/standard.cls`
- potentially density-related spacing behavior if needed
- `project.md`
- `docs/file-map.md`
- `sdd/history/`

## Goal State
The intended experience entry order should be:

1. header (`company`, `position`)
2. metadata line (`location`, employment type, date range)
3. `role_summary` as normal body text
4. one small visual pause
5. bullets
6. technology/keyword line in smaller secondary text

Expected visual shape:

```text
<company>                                         <position>
<metadata-left>                                   <period>

<role summary in normal text>

- bullet
- bullet
- bullet

<smaller technical keyword line>
```

## Scope
This task may update:

- `src/hirepaper/generator.py`
- `templates/standard.cls`
- `project.md`
- `docs/file-map.md`
- `sdd/history/`

This task should not:

- redesign unrelated sections such as education, projects, or volunteer;
- change the candidate schema;
- remove keyword metadata generation from PDF metadata;
- reduce ATS-visible content;
- introduce decorative formatting that harms extraction.

## Required Behavior

### 1. Move the technology/keyword line after the bullets
Current behavior renders the technology line before `role_summary`.

Required new behavior:

- if an experience entry has technologies, render that line after the bullets;
- if there are no bullets but there is a role summary, render technologies after
  the role summary;
- if there is no role summary and no bullets, render technologies last among the
  available supporting lines.

The keyword line should behave as trailing technical context, not as the
opening content line.

### 2. Render `role_summary` in normal text
Current behavior in `src/hirepaper/generator.py` wraps `role_summary` in
`\textit{...}`.

That behavior should be removed for experience entries.

Required new behavior:

- render `role_summary` as normal text;
- keep it visually distinct through spacing and size, not italics.

This should make the role summary read as a primary explanatory line rather
than an aside.

### 3. Add visual breathing room before bullets
After the role summary, the layout should introduce a small vertical pause
before the first bullet.

Required outcome:

- the role summary should not sit flush against the first bullet;
- the pause should be subtle, not large enough to waste vertical space;
- the spacing should remain consistent across entries.

This may be implemented either:

- in the generator with an explicit spacer between summary and bullets; or
- in the template/macros if that produces a cleaner result.

### 4. Render the keyword line in a smaller secondary style
The technology line should remain visible and ATS-extractable, but visually
de-emphasized.

Required style direction:

- smaller font than the main bullets/body text;
- subdued color or secondary styling is acceptable if extraction remains safe;
- no iconography or decorative prefix is required.

The goal is to keep the line readable without competing with the narrative.

### 5. Preserve ATS-safe extraction
This layout refinement must not degrade ATS behavior.

Required expectations:

- the role summary remains extractable as plain text;
- bullets remain extractable in sensible reading order;
- the keyword line remains visible in extracted text;
- fonts remain ATS-safe and Unicode-mapped.

## Design Guidance

### Preferred implementation direction
The most coherent implementation is likely in `src/hirepaper/generator.py`,
where the experience block is currently assembled in sequence.

Recommended direction:

- build the experience entry in this order:
  1. header
  2. role summary
  3. bullets
  4. technologies
- remove italic wrapping from the rendered role summary;
- emit a small spacer before bullet output when both summary and bullets exist;
- emit a dedicated smaller-text sub-line or macro for technologies.

### Template considerations
If the current `\resumeEntrySub` macro is too generic for both role summary and
technology lines, it may be worth introducing separate macros, for example:

- one sub-line style for normal supporting body text;
- one compact sub-line style for secondary keywords/technologies.

This should remain a narrow template change, not a broad redesign.

### Density considerations
The smaller technology line should reduce visual competition, but the task must
still respect compact density behavior.

The implementation should avoid:

- adding large blank gaps;
- causing frequent page growth because of over-generous spacing;
- making the keyword line so small or faint that it becomes visually useless.

## Acceptance Criteria
This task is complete only if all of the following are true:

1. `role_summary` renders before the bullets in experience entries.
2. `role_summary` no longer renders in italics.
3. There is a small visual pause between `role_summary` and the first bullet.
4. The technology/keyword line renders after the bullets.
5. The technology/keyword line uses a smaller secondary text style.
6. ATS extraction remains valid after the layout change.
7. The packaged binary preserves the corrected hierarchy.

## Recommended Verification
At minimum verify:

```bash
./hirepaper-dev pdf generate data/candidate.json -o output/experience-hierarchy-dev.pdf --density compact --locale en
./hirepaper-dev pdf check output/experience-hierarchy-dev.pdf
pdftotext output/experience-hierarchy-dev.pdf -

.venv/bin/python build.py
./hirepaper pdf generate data/candidate.json -o output/experience-hierarchy-packaged.pdf --density compact --locale en
./hirepaper pdf check output/experience-hierarchy-packaged.pdf
pdftotext output/experience-hierarchy-packaged.pdf -
```

Also verify visually:

- `role_summary` reads as the opener to the experience;
- bullets have a small but noticeable separation from the summary;
- technologies read as trailing secondary context;
- no overlap, awkward wrapping, or density regression appears.

If practical, also verify with `pt-BR` locale and both densities.

## Notes For The Implementing Agent
- Treat this as a hierarchy and readability fix, not a content rewrite task.
- Do not move keyword metadata out of the PDF metadata block; this task only
  changes visible layout order.
- Keep the implementation close to the existing experience renderer unless the
  template clearly needs a narrow new macro for secondary keyword lines.
