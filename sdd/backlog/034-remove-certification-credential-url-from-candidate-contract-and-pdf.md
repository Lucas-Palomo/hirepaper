# 034 - Remove certification `credential_url` from candidate contract and PDF rendering

## Status
Completed

## Context
The current candidate schema and rendering pipeline support an optional
`certifications[].credential_url` field.

Today, certifications are rendered in the PDF as a compact utility section. When
`credential_url` is present, the generator appends the visible cleaned URL after
the certification line.

In practice, this is creating more noise than value.

Observed current behavior in generated PDF extraction:

```text
Certifications
AWS Solutions Architect – Associate — Amazon Web Services
Jun 2023
aws.amazon.com/verify/credential Certified Kubernetes Administrator
(CKA) — CNCF
Nov 2022
```

This confirms two problems:

- the credential URL adds low-value visual and textual noise in a compact
  section;
- the extracted reading order becomes messy enough that the URL visually bleeds
  into the next certification entry.

For this layout, the verification URL is not a strong resume signal compared to:

- certification name;
- issuer;
- certification date.

The field currently harms scanability more than it helps.

## Goal
Remove `credential_url` from the canonical candidate contract and stop rendering
credential verification URLs in the PDF certifications section.

Target outcome:

- certifications remain concise and easy to scan;
- the candidate schema no longer advertises `credential_url` as part of the
  canonical data model;
- example/sample candidate files are updated;
- PDF rendering no longer appends certification URLs;
- extraction order for certifications becomes cleaner.

## Product Decision
`credential_url` should be removed from the canonical certification schema for
this project.

Rationale:

- certification verification URLs are low-signal in the current resume format;
- they create visible clutter in a compact section;
- they degrade extraction clarity in `pdftotext` output;
- the resume should prioritize human scanability and ATS-safe signal density,
  not expose every available source-system detail.

If the project later needs to preserve verification links for another workflow,
that should be handled through a different artifact or a separate optional
supporting channel, not the core resume PDF.

## Scope
This task may update:

- `src/curriculum_gen/models.py`
- `src/curriculum_gen/loader.py`
- `src/curriculum_gen/generator.py`
- `assets/schemas/candidate.schema.json`
- `assets/examples/candidate.example.json`
- `data/example.json`
- `data/candidate.json`
- `src/curriculum_gen/content_match.py`
- `src/curriculum_gen/content_tailor.py`
- `assets/schemas/content-tailor-plan.schema.json` if it still exposes
  certification URLs through tailoring payload contracts
- `project.md`
- `agents.md` only if examples or validation guidance need to mention the new
  canonical certification shape
- `sdd/history/`

This task should not:

- redesign the entire certifications section;
- remove certification name, issuer, or date;
- widen into a general project-wide URL cleanup effort;
- change project URLs or profile links outside certification scope.

## Required Contract Change
The canonical certification object should no longer include `credential_url`.

### Previous shape

```json
{
  "name": "AWS Solutions Architect – Associate",
  "issuer": "Amazon Web Services",
  "date": "2023-06",
  "credential_url": "https://aws.amazon.com/verify/credential"
}
```

### Target shape

```json
{
  "name": "AWS Solutions Architect – Associate",
  "issuer": "Amazon Web Services",
  "date": "2023-06"
}
```

Required outcomes:

- `assets/schemas/candidate.schema.json` no longer defines
  `certifications[].credential_url`;
- certification dataclasses/models no longer expose it as part of the canonical
  resume contract;
- loader behavior aligns with the canonical schema decision.

## PDF Rendering Requirement
The PDF generator must stop rendering certification verification URLs.

Required behavior:

- certifications render only their core visible signal;
- visible certification lines remain concise;
- no certification URL is appended after the date or on a separate line;
- extraction output for certifications should no longer contain those URLs.

This task is not complete if `credential_url` is removed from the schema but the
PDF generator still renders legacy URLs when present in input.

## LLM / Payload Alignment
The project already exposes candidate data to LLM-backed flows such as
`content match` and `content tailor`.

Those payloads and schemas should be aligned with the canonical candidate
contract.

Required behavior:

- certification payloads should no longer include `credential_url` as part of
  the canonical candidate representation;
- tailor conversion paths should not preserve or re-emit `credential_url` in the
  final candidate JSON if the field is removed from the canonical schema;
- any related plan/rewrite schema references should be updated if they expose
  this field.

## Fixture and Example Requirements
Update canonical examples and sample data to remove `credential_url` from
certifications.

Required updates:

- `assets/examples/candidate.example.json`
- `data/example.json`
- `data/candidate.json`

The updated examples should remain valid canonical reference inputs.

## Backward Compatibility Decision
This task changes the canonical candidate contract.

Preferred policy:

- remove `credential_url` from the canonical schema and samples;
- update runtime code accordingly;
- do not keep the field as part of the official current model.

The implementing agent may choose whether to tolerate legacy input containing
`credential_url` temporarily, but if so:

- it must be ignored for rendering;
- it must be documented explicitly in history as temporary migration tolerance;
- it must not remain part of the canonical schema or examples.

## Documentation Updates
Update `project.md` to reflect the canonical certification shape if it currently
implies or references certification URLs.

Update `agents.md` only if examples or verification guidance should mention the
simplified certification contract.

## Verification
Minimum verification should include schema/runtime validation plus PDF
extraction review.

### Loader / lint verification

```bash
./curriculum-gen-dev content lint data/candidate.json
./curriculum-gen-dev content lint data/example.json
```

### PDF generation verification

```bash
./curriculum-gen-dev pdf generate data/candidate.json --output /tmp/certifications-clean.pdf --density compact --locale en
./curriculum-gen-dev pdf check /tmp/certifications-clean.pdf
pdftotext /tmp/certifications-clean.pdf - | sed -n '/Certifications/,$p'
```

### Packaged verification

```bash
.venv/bin/python build.py
./curriculum-gen pdf generate data/candidate.json --output /tmp/certifications-clean-packaged.pdf --density compact --locale en
./curriculum-gen pdf check /tmp/certifications-clean-packaged.pdf
```

## Expected Verification Outcomes
The implementing agent should confirm:

1. canonical candidate fixtures no longer contain `credential_url`;
2. schema/model/loader are aligned with the simplified certification contract;
3. generated PDFs no longer display certification URLs;
4. extracted certification text is cleaner and no longer bleeds URL text into
   neighboring entries;
5. source and packaged execution remain consistent.

## Acceptance Criteria
1. `credential_url` is removed from the canonical certification schema.
2. Certification runtime models and loader paths are updated accordingly.
3. Example/sample candidate files no longer use `credential_url`.
4. PDF certification rendering no longer includes verification URLs.
5. LLM-facing candidate payloads and related conversion paths are aligned with
   the updated canonical contract.
6. ATS-safe visible-text behavior is preserved.
7. The change is verified in source mode and packaged mode.
8. A history entry records the decision, implementation, and verification.

## Notes For The Implementing Agent
- Treat this as a signal-to-noise reduction task.
- Optimize the certifications section for fast scanning, not completeness of
  source metadata.
- Verify the result with `pdftotext`, not only by visual PDF inspection.
