# 009 - Add ATS-safe PDF validation command

## Status
Completed

## Context
The generated PDF can look visually acceptable while still being unsafe for ATS parsing.

A recent PDF generated in `full` mode showed corrupted text extraction, with examples like:

```text
Prole
StackOverow
Senior Software Engineer  Distributed Systems
Feb 2018  Feb 2021
Certied
```

This indicates that the PDF may have font encoding, glyph mapping, engine, or layout issues. The project must validate the technical quality of the generated PDF, not only whether LaTeX compilation succeeds.

This task adds a separate CLI command called `ats-check`.

## Goal
Provide a local ATS compatibility validation command that checks whether a generated PDF is safe for text extraction and basic ATS parsing signals.

The command must not claim to fully simulate a real ATS. Different ATS products use different parsers and ranking heuristics.

Instead, this command should validate objective technical signals that strongly affect ATS compatibility.

## Command
Add a new CLI command:

```bash
curriculum-gen ats-check <pdf_file>
```

Expected usage:

```bash
curriculum-gen ats-check output/resume.pdf
```

The command should inspect the PDF and report clear `OK`, `WARN`, and `FAIL` diagnostics.

## Dependency Policy
Do not use external resume-specific ATS libraries for this task.

Do not use:
- `leverparser`
- `dsresumatch`
- `pyresparser`
- commercial resume parsing APIs
- any library that claims to score or simulate ATS behavior without being necessary for the technical checks

The validation should initially rely on local, objective PDF tooling such as:
- `pdftotext`
- `pdffonts`

Python may orchestrate these tools and analyze their output.

## Required Checks
### 1. Text extraction check
Run text extraction for the target PDF.

Preferred tool:

```bash
pdftotext <pdf_file> -
```

The command should fail clearly if text extraction cannot run or returns empty output.

### 2. Corrupted character detection
Detect obvious extraction corruption.

Examples of problematic output include:
- control characters inside words;
- broken ligature extraction such as `Prole`;
- broken dash extraction such as `` or ``;
- replacement characters;
- suspicious non-printable characters.

The check does not need to be perfect, but it should catch common extraction failures observed in the current PDF.

### 3. Font check
Run font inspection for the target PDF.

Preferred tool:

```bash
pdffonts <pdf_file>
```

The command should report:
- whether Type 3 fonts are present;
- whether fonts appear to have Unicode mapping when that information is available.

Type 3 fonts should be treated as a failure for ATS-safe output.

### 4. Required section check
Verify that the extracted text contains expected resume sections.

Initial required sections:
- `Summary`
- `Experience`
- `Education`
- `Skills`

The check may be locale-aware later, but this task can start with the labels currently expected for the generated PDF.

### 5. Contact visibility check
Verify that the extracted text contains visible contact data.

At minimum, check for:
- email-like text;
- phone-like text;
- location or other contact line presence if practical.

### 6. Link visibility check
Verify that links are not hidden behind generic labels only.

The check should warn if extracted text contains only generic link labels such as:
- `[link]`
- `[credential]`

The check should prefer visible URLs or explicit labels with URLs.

### 7. Placeholder check
Fail if generated placeholders remain in the PDF text.

Examples:
- `SUMMARY`
- `{SUMMARY}`
- `{EXPERIENCE}`
- `{SKILLS}`
- any obvious template placeholder.

### 8. Keyword preservation check
Verify that important technical keywords remain intact in extracted text.

Initial keywords to check:
- `Python`
- `Kafka`
- `PostgreSQL`
- `Docker`
- `Kubernetes`
- `AWS`
- `FastAPI`
- `Django`
- `React`
- `Terraform`
- `GitHub Actions`
- `Prometheus`
- `Grafana`

Missing keywords should be reported as warnings unless the command later receives an expected-keywords configuration.

## Output Behavior
The command should print a readable diagnostic report.

Example shape:

```text
ATS compatibility check: output/resume.pdf

[OK] Text extraction succeeded
[FAIL] Corrupted extraction characters detected
[OK] No Type 3 fonts found
[WARN] Some fonts may not expose Unicode mapping
[OK] Required sections found: Summary, Experience, Education, Skills
[OK] Contact information found
[WARN] Generic hidden link labels found: [link], [credential]
[OK] Technical keywords found: Python, Kafka, PostgreSQL, Docker

Result: FAIL
```

Exit code behavior:
- `0` when no failures are found;
- non-zero when one or more failures are found;
- warnings alone should not fail the command unless the implementing agent documents a stricter mode.

## Optional Report Files
The command may support saving diagnostic artifacts later, but this is not required for the first implementation.

Potential future flags:

```bash
curriculum-gen ats-check output/resume.pdf --save-report logs/ats-check.txt
curriculum-gen ats-check output/resume.pdf --save-text logs/pdftotext.txt
curriculum-gen ats-check output/resume.pdf --save-fonts logs/pdffonts.txt
```

For this task, terminal output is sufficient.

## Relationship With `generate`
`ats-check` should be a separate command.

Do not make PDF generation depend on ATS validation by default.

Future integration may add:

```bash
curriculum-gen generate data/candidate.json -o output/resume.pdf --ats-check
```

But that is not required in this task.

## Relationship With `doctor`
`doctor` should check whether required tools are available.

After this task, `doctor` should include checks for:
- `pdftotext`
- `pdffonts`

This is an environment readiness check only. The actual PDF validation belongs to `ats-check`.

## Possible Follow-Up Fixes
This task is primarily about validation, but its results may drive later fixes.

Likely follow-up areas:
- switch default LaTeX engine from `pdflatex` to `xelatex`;
- use `fontspec` and Unicode-safe fonts;
- avoid Type 3 fonts;
- replace special dashes and symbols with ASCII-safe equivalents;
- make links visible in extracted text;
- reduce table-based layout where it harms text extraction;
- improve header line separation;
- ensure `Summary` renders real content.

## Acceptance Criteria
The task should be considered complete only if:

1. `curriculum-gen ats-check <pdf_file>` exists.
2. The command runs `pdftotext` and analyzes extracted text.
3. The command runs `pdffonts` and detects Type 3 fonts.
4. Corrupted extraction characters are detected.
5. Required sections are checked.
6. Contact visibility is checked.
7. Generic hidden link labels are reported.
8. Important technical keywords are checked.
9. The command returns a non-zero exit code when failures are found.
10. No resume-specific ATS simulation library is introduced.

## Suggested Verification
The implementing agent should verify:

```bash
curriculum-gen ats-check output/resume.pdf
```

If possible, also test against:
- a known-good PDF;
- a PDF with corrupted extraction;
- a missing or invalid PDF path.

## Notes For The Implementing Agent
- Do not market this command as a complete ATS simulator.
- Call it an ATS compatibility check or ATS-safe PDF validation.
- Keep checks objective and explainable.
- Prefer deterministic local validation over opaque scoring.
