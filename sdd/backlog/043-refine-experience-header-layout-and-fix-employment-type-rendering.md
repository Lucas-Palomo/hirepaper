# 043 - Refine experience header layout and fix employment type rendering

## Status
Completed

## Context
The current `standard` resume layout has at least one concrete regression in
the experience section.

Observed issues in the current rendering:

1. `employment_type` is rendered as a separate sub-line below the location and
   technologies instead of being part of the compact experience header.
2. In the reported output, the literal locale key `label.employment_type`
   appears in the PDF instead of the translated label value, which indicates a
   locale/runtime resource mismatch or stale compiled catalog issue.
3. The intended hierarchy for the header is not being preserved: location,
   employment type, and date period should read as concise metadata attached to
   the role, not as disconnected blocks.

The user provided the intended layout direction with this example:

```text
Empresa    Cargo
LATAM | CLT    Periodo
```

This task exists to align the rendered experience header with that intended
structure.

## Goal
Refine the `standard` layout so that `employment_type` is rendered inline with
the experience metadata, not as a detached sub-line, and ensure locale labels
do not leak as raw translation keys in the PDF output.

## Why This Task Exists
The current output weakens both readability and professionalism:

- metadata that belongs together is visually fragmented;
- the reader sees an implementation-looking translation key in the final PDF;
- the role header consumes extra vertical space for low-value separation;
- the intended information hierarchy is not matching the design.

This is a layout bug, not a content-model problem.

## Affected Surface
Primary:

- experience entries in `standard` layout

Likely implementation areas:

- `src/hirepaper/generator.py`
- `templates/standard.cls`
- `locale/en/LC_MESSAGES/messages.po`
- `locale/pt_BR/LC_MESSAGES/messages.po`
- compiled `.mo` locale artifacts if they are committed and used at runtime
- documentation and history files if needed

## Goal State
For experience entries, the layout should follow this information hierarchy:

1. company on the left, role title on the right
2. location and employment type grouped on the left metadata line
3. date range on the right metadata line
4. optional technologies / role summary / bullets below

Expected shape:

```text
<company>                                         <position>
<location> | <employment_type>                   <period>
<technologies>
<optional summary>
- bullets
```

When `employment_type` is missing, the layout should degrade cleanly to:

```text
<location>                                       <period>
```

without stray separators.

## Scope
This task may update:

- `src/hirepaper/generator.py`
- `templates/standard.cls`
- `locale/en/LC_MESSAGES/messages.po`
- `locale/pt_BR/LC_MESSAGES/messages.po`
- `locale/en/LC_MESSAGES/messages.mo`
- `locale/pt_BR/LC_MESSAGES/messages.mo`
- `project.md`
- `docs/file-map.md`
- `sdd/history/`

This task should not:

- redesign unrelated sections;
- change the candidate JSON schema;
- introduce new required fields;
- expand layout options beyond `standard`;
- add decorative formatting that compromises ATS extraction.

## Required Behavior

### 1. Employment type must move into the experience metadata line
Current behavior in `src/hirepaper/generator.py` appends `employment_type` as:

```text
\resumeEntrySub{<label>: <value>}
```

That behavior should be removed for experience entries.

Instead, `employment_type` must be composed into the same metadata line as
`location`.

Required rendering policy:

- when both `location` and `employment_type` exist:
  - render `<location> | <employment_type>`
- when only `location` exists:
  - render `<location>`
- when only `employment_type` exists:
  - render `<employment_type>`
- when both are empty:
  - render an empty left metadata field cleanly

The separator must be a literal visible pipe with surrounding spaces:

```text
LATAM | CLT
```

### 2. Locale labels must not leak into the PDF

```text
label.employment_type : CLT
```

That is unacceptable in final output.

This task must determine and fix the actual cause. Possible causes include:

- stale compiled `.mo` files not matching the `.po` source;
- locale resource resolution not loading the expected catalog;
- fallback logic returning keys due to missing compiled translation data;
- rendering code using the wrong string at runtime.

Required outcome:

- final PDFs must never show raw translation keys such as
  `label.employment_type`;
- the locale system must resolve either the translated value or a deliberate
  default string, not the msgid token.

### 3. Preserve ATS-safe extraction
The header refinement must remain plain-text extractable.

Required extraction expectations:

- extracted text should preserve company, role, location, employment type, and
  period in a sensible reading order;
- the visible pipe separator must not introduce corruption or break parsing;
- no Type 3 font or extraction regression may be introduced.

### 4. Keep vertical density under control
Moving `employment_type` inline is partly a density improvement.

This task should reduce wasted vertical space by eliminating the extra metadata
sub-line when it only exists to show employment type.

The implementation should preserve readability and not crowd the left metadata
column excessively.

## Design Guidance

### Preferred implementation direction
The most coherent place to fix this is in `src/hirepaper/generator.py` by
changing the experience metadata composition before it is passed to
`\resumeEntry`.

Recommended direction:

- build a small helper that joins optional metadata fragments with `" | "`;
- pass the combined string as the fourth `\resumeEntry` argument for
  experience entries;
- stop emitting `employment_type` as `\resumeEntrySub`.

This keeps the layout logic close to the experience renderer and avoids special
LaTeX branching for a simple data composition rule.

### Template considerations
If the current `\resumeEntry` widths or alignment cause wrapping or collisions
for realistic values, the task may adjust `templates/standard.cls`.

Any template changes should stay narrow:

- only tune widths/spacing if necessary to support the corrected hierarchy;
- do not redesign the general experience block unless the current macro makes
  the required layout impossible.

### Locale/runtime considerations
If `.po` files are correct but `.mo` files are stale, the task should update the
compiled catalogs committed in the repo so runtime behavior matches source.

If the locale loader behavior itself is the issue, fix the loader/runtime path
instead of merely patching strings in the template.

## Acceptance Criteria
This task is complete only if all of the following are true:

1. `employment_type` is no longer rendered as a separate `resumeEntrySub` line
   for experience entries.
2. Experience metadata renders inline as `location | employment_type` when both
   fields are present.
3. PDFs no longer show raw translation keys such as `label.employment_type`.
4. Entries without `employment_type` still render cleanly without stray pipes.
5. ATS text extraction remains valid after the layout change.
6. The packaged binary still renders the same corrected behavior.

## Recommended Verification
At minimum verify:

```bash
./hirepaper-dev pdf generate data/candidate.json -o output/exp-layout-dev.pdf --density compact --locale pt-BR
./hirepaper-dev pdf check output/exp-layout-dev.pdf

pdftotext output/exp-layout-dev.pdf -

.venv/bin/python build.py
./hirepaper pdf generate data/candidate.json -o output/exp-layout-packaged.pdf --density compact --locale pt-BR
./hirepaper pdf check output/exp-layout-packaged.pdf
pdftotext output/exp-layout-packaged.pdf -
```

Also verify visually:

- the specific entry with `employment_type` renders inline with location;
- long role titles still align correctly with dates;
- no overlap or awkward wrapping appears in the experience header.

If practical, also verify English locale:

```bash
./hirepaper-dev pdf generate data/candidate.json -o output/exp-layout-en.pdf --density compact --locale en
./hirepaper-dev pdf check output/exp-layout-en.pdf
```

## Notes For The Implementing Agent
- Treat the raw `label.employment_type` output as a real bug, not as cosmetic
  polish.
- Preserve the current candidate data model; this is a rendering/layout fix.
- Do not add new schema fields just to solve formatting.
- If the fix reveals broader locale packaging drift, document exactly what was
  corrected and why.
