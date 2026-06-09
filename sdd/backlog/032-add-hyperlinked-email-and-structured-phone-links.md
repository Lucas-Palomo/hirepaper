# 032 - Add hyperlinked email and structured phone links

## Status
Completed

## Context
The project’s PDF header already renders visible contact information for:

- email
- phone
- location
- labeled profile links

However, email and phone are currently treated as plain visible text in the
candidate model and rendered header. That means the PDF exposes the values for
human reading and ATS extraction, but does not consistently provide actionable
hyperlinks for direct contact actions.

For email, the desired behavior is straightforward:
- keep the visible email text;
- make it clickable via `mailto:` in the PDF.

For phone, the current schema is too limited:

```json
"phone": "+55 11 99999-9999"
```

A plain string does not let the candidate declare which contact hyperlink should
be used in the PDF. In practice, a candidate may want:

- `tel:` dialing behavior;
- `https://wa.me/...` for WhatsApp;
- another explicit contact URL.

That choice should not be guessed implicitly by layout code.

The candidate contract should become explicit by turning `personal.phone` into a
structured object.

## Goal
Add hyperlink support for email and phone in generated PDFs, and update the
canonical candidate schema so `personal.phone` becomes an object with visible
value plus explicit hyperlink target.

Target outcome:

- email remains visible text and becomes clickable with `mailto:` in the PDF;
- phone remains visible text and becomes clickable with its explicit hyperlink;
- the candidate schema, loader, example candidate, and PDF rendering are all
  updated consistently.

## Product Decision
`personal.phone` should become a structured object in the canonical candidate
contract.

Target shape:

```json
"phone": {
  "value": "+55 11 99999-9999",
  "hyperlink": "https://wa.me/5511999999999"
}
```

Rationale:

- visible phone text and click behavior are different concerns;
- the project should not guess whether the right action is `tel:` or WhatsApp;
- an explicit hyperlink keeps the data model deterministic;
- the same structure can support different contact-link strategies while
  preserving visible ATS-safe text.

## Scope
This task may update:

- `src/curriculum_gen/models.py`
- `src/curriculum_gen/loader.py`
- `src/curriculum_gen/generator.py`
- `templates/standard.tex`
- `templates/standard.cls` only if a helper macro improves header link handling
- `assets/schemas/candidate.schema.json`
- `assets/examples/candidate.example.json`
- `data/example.json`
- `data/candidate.json` if the canonical sample should remain loadable under the
  new schema
- `project.md`
- `agents.md` if command examples or verification guidance need schema examples
- `sdd/history/`

This task should not:

- redesign unrelated parts of the candidate model;
- remove visible contact text from the PDF;
- hide email or phone behind generic anchor text;
- invent phone hyperlinks automatically from the visible number when the source
  data does not provide one;
- widen into a general-purpose contact-method redesign beyond what is required
  for email and phone hyperlinks.

## Schema Change
The canonical candidate schema must change `personal.phone` from a string to an
object.

### Previous shape

```json
"phone": "+55 11 99999-9999"
```

### Target shape

```json
"phone": {
  "value": "+55 11 99999-9999",
  "hyperlink": "https://wa.me/5511999999999"
}
```

### Required semantics
- `value`
  - required
  - visible text rendered in the PDF
  - must remain human-readable
- `hyperlink`
  - required
  - target hyperlink embedded in the PDF
  - may be a `tel:` link, `https://wa.me/...`, or another explicit URL chosen by
    the candidate

### Required validation
The updated `candidate.schema.json` must require:

- `personal.phone` to be an object;
- `value` to be a non-empty string;
- `hyperlink` to be a non-empty string;
- no additional properties on the phone object.

## Loader and Model Requirements
The Python model and loader must match the schema change.

Required outcomes:

- add a dedicated phone/contact dataclass or equivalent explicit model type;
- parse `personal.phone.value` and `personal.phone.hyperlink` through the loader;
- fail clearly when the phone object is missing required fields;
- keep runtime behavior deterministic and aligned with the canonical schema.

The implementation should not leave the loader accepting only the old string
shape while the schema claims otherwise.

## Email Hyperlink Requirement
Email should remain a string in the candidate schema unless the implementing
agent finds a compelling task-scoped reason to change it.

Required PDF behavior:

- visible text remains the literal email address;
- the rendered PDF wraps it with a `mailto:` hyperlink;
- extracted text must still show the visible email address clearly.

Target rendered meaning:

```text
Email: joao.silva@email.com
```

with a clickable `mailto:joao.silva@email.com` target.

## Phone Hyperlink Requirement
Phone should render using the new structured object.

Required PDF behavior:

- visible text remains `phone.value`;
- hyperlink target is exactly `phone.hyperlink`;
- the PDF should not display the raw hyperlink target in place of the visible
  phone number;
- extracted text must still show the visible phone number clearly.

Target rendered meaning:

```text
Phone: +55 11 99999-9999
```

with a clickable target such as:

```text
https://wa.me/5511999999999
```

or:

```text
tel:+5511999999999
```

The visible text should remain the human-readable phone string.

## PDF Rendering Requirements
This task must apply the hyperlink behavior in the generated PDF header.

Required behavior:

- email contact item uses `\href{mailto:...}{visible-email}`;
- phone contact item uses `\href{phone.hyperlink}{phone.value}`;
- location remains visible text only;
- existing labeled profile links remain visible labeled URLs as they work today.

The rendered contact block must remain ATS-safe:

- visible contact data remains extractable with `pdftotext`;
- visible labels remain readable;
- hyperlink behavior must not replace visible text with opaque link-only content.

## Fixture and Example Requirements
This task must update the canonical example candidate artifacts so users have a
correct reference for the new contract.

Required updates:

- `assets/examples/candidate.example.json`
- `data/example.json`
- any canonical sample input used by normal project verification, including
  `data/candidate.json` if it is expected to remain valid under the current CLI

The updated examples should demonstrate the intended phone structure clearly.

Example acceptable fixture shape:

```json
"personal": {
  "name": "Your Name",
  "email": "you@email.com",
  "phone": {
    "value": "+55 11 99999-9999",
    "hyperlink": "https://wa.me/5511999999999"
  },
  "location": "City, State"
}
```

## Backward Compatibility Decision
This task changes the canonical candidate contract.

Preferred policy for this task:

- migrate the canonical schema and fixtures to the new phone-object contract;
- update the loader and generator accordingly;
- do not keep the old string shape as the official canonical form.

The implementing agent may choose whether to accept the legacy string shape
transitionally in the loader, but if that compatibility is retained it must be
explicitly documented in history as a temporary migration aid, not the canonical
contract.

The primary project artifacts and docs must reflect the new object shape.

## Documentation Updates
Update `project.md` to reflect:

- the candidate schema expectation for `personal.phone`;
- that generated PDFs now embed clickable email and phone hyperlinks while
  preserving visible text.

Update `agents.md` only if command examples, fixture expectations, or validation
examples should mention the new phone object explicitly.

## Verification
Minimum verification should include schema/runtime validation plus PDF behavior.

### Loader / lint verification

```bash
./curriculum-gen-dev content lint data/candidate.json
./curriculum-gen-dev content lint data/example.json
```

### PDF generation verification

```bash
./curriculum-gen-dev pdf generate data/candidate.json --output /tmp/contact-hyperlinks.pdf --density compact --locale en
./curriculum-gen-dev pdf check /tmp/contact-hyperlinks.pdf
pdftotext /tmp/contact-hyperlinks.pdf -
exiftool /tmp/contact-hyperlinks.pdf
```

### Packaged verification

```bash
.venv/bin/python build.py
./curriculum-gen pdf generate data/candidate.json --output /tmp/contact-hyperlinks-packaged.pdf --density compact --locale en
./curriculum-gen pdf check /tmp/contact-hyperlinks-packaged.pdf
```

### Manual PDF hyperlink check
The implementing agent should also manually verify in a PDF viewer that:

- clicking the email opens a `mailto:` target;
- clicking the phone opens the configured hyperlink target;
- visible text remains the email address and phone number, not the raw hyperlink
  destination.

If GUI verification is not possible in the environment, the history entry must
state that limitation explicitly.

## Expected Verification Outcomes
The implementing agent should confirm:

1. updated candidate fixtures load successfully;
2. `content lint` succeeds on the updated canonical fixtures;
3. generated PDFs still pass ATS checks;
4. extracted text still contains visible email and visible phone text;
5. PDF hyperlinks are applied to email and phone in source mode and packaged
   mode.

## Acceptance Criteria
1. `assets/schemas/candidate.schema.json` defines `personal.phone` as an object
   with required `value` and `hyperlink` fields.
2. The Python model and loader are updated to match the new canonical schema.
3. `assets/examples/candidate.example.json` is updated to the new phone-object
   shape.
4. Canonical sample candidate data is updated to the new phone-object shape.
5. Generated PDFs apply `mailto:` hyperlinks to email while preserving visible
   email text.
6. Generated PDFs apply the configured hyperlink to phone while preserving
   visible phone text.
7. ATS-safe visible-text behavior is preserved.
8. Documentation is updated.
9. A history entry records the implementation and verification.

## Notes For The Implementing Agent
- Keep visible contact text as the primary artifact; hyperlinks are a PDF
  usability enhancement, not a replacement for readable content.
- Treat phone hyperlink behavior as explicit data supplied by the candidate,
  not inferred behavior.
- Verify both rendered appearance and extracted text after the change.
- If a helper abstraction is needed for contact rendering, keep it scoped to the
  current task rather than redesigning all personal fields.
