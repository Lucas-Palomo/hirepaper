# 014 - Harden PDF build validation and density rules

## Status
Completed

## Context
Validation of generated resumes across both densities (`compact`, `full`) and both
headline layouts (`standard-headline-inline`, `standard-headline-tabular`) showed
that the final PDFs can be ATS-compatible when LuaLaTeX runs successfully.

However, the build path can still report success for a partially generated PDF
when LuaLaTeX fails after creating an output file. In the observed case, the TeX
font cache was not writable, `luaotfload` failed to load fonts, and the command
still printed `Generated:` because `_build_pdf()` only checked that a PDF file
existed and had non-zero size. The resulting PDF had metadata and pages, but no
extractable text and no listed fonts, making it ATS-unsafe.

The same validation also surfaced density and input-quality concerns. Some are
legitimate user choices, but the default density policies should do more to keep
the generated resume focused on the essential content. The tool should also make
ATS-oriented diagnostics more actionable when input content is too verbose or
structurally weak.

## Goal
Make PDF generation fail fast and clearly when the produced artifact is not
machine-readable, and refine the default density policies so generated resumes
prioritize essential content without relying on each user to manually prune every
optional section.

The final project should:
- never report `Generated:` for a PDF that has empty extracted text;
- detect common LuaLaTeX/font/cache failures before or during generation;
- make `doctor` validate the actual LuaLaTeX + `fontspec` + `DejaVu Sans` path;
- keep metadata keyword validation consistent across normal and custom fields;
- improve default density behavior for optional sections and isolated links;
- provide ATS-check diagnostics for bullets that are likely too long.

## Scope
This task may update:
- `src/curriculum_gen/cli.py`
- `src/curriculum_gen/ats_check.py`
- `src/curriculum_gen/generator.py`
- `src/curriculum_gen/density.py`
- `src/curriculum_gen/models.py`
- `src/curriculum_gen/loader.py`
- `templates/standard-headline-inline.*`
- `templates/standard-headline-tabular.*`
- `data/candidate.json`
- `data/example.json`
- backlog/history documentation

This task should not:
- introduce a new layout family;
- change LuaLaTeX as the only supported engine;
- remove ATS validation checks added in previous tasks;
- treat every user content choice as a generator bug.

## Primary Problems To Address

### 1. Build success criteria are too weak
`_build_pdf()` currently accepts a generated PDF when the file exists and has
non-zero size, even if the LaTeX process reported fatal errors.

Observed failure mode:
- `luaotfload` failed because there was no writable cache path;
- `fontspec` could not load `DejaVu Sans`;
- LaTeX still produced a small PDF file;
- the CLI copied the PDF and printed `Generated:`;
- `pdftotext` returned empty output;
- `pdffonts` listed no fonts.

Required behavior:
- do not report success for empty-text PDFs;
- fail generation if `pdftotext` returns empty output;
- fail generation if `pdffonts` lists no fonts;
- fail generation on fatal LaTeX/font errors even when a PDF exists;
- include a clear error message pointing to logs or likely missing/writable font
  cache problems.

### 2. `doctor` does not validate the real generation path
`doctor` checks that `lualatex`, `luaotfload`, `rsvg-convert`, `pdftotext`,
`pdffonts`, and `exiftool` exist, but it does not prove that a minimal document
using `fontspec` and `DejaVu Sans` can compile successfully.

Required behavior:
- compile a minimal LuaLaTeX document using `fontspec` and
  `\setmainfont{DejaVu Sans}`;
- verify that `pdftotext` extracts expected text from the minimal PDF;
- verify that `pdffonts` reports embedded Unicode-mapped fonts;
- report cache or font-loading failures explicitly.

### 3. Generation lacks post-build artifact validation
The CLI should perform a cheap artifact sanity check before considering a PDF
generated successfully.

Required behavior:
- after LaTeX compilation, inspect the PDF with `pdftotext`;
- inspect fonts with `pdffonts`;
- reject PDFs with empty text extraction;
- reject PDFs with no listed fonts;
- reject PDFs with Type 3 fonts;
- preserve full `ats-check` as the deeper validation command, but prevent the
  most obvious broken artifacts from being emitted as successful builds.

### 4. Keyword metadata sanitization is inconsistent
In `full` density, `Keywords` and `X-Keywords-*` can diverge for values with
special characters.

Observed examples:
- `C^2 (Care^2)` appears differently between `Keywords`, `X-Keywords-Skills`,
  and extracted text.
- `ats-check` reports `Keywords differ from union of X-Keywords-* fields`.
- `ats-check` can also report a missing keyword derived from the sanitized
  metadata form rather than the extracted text form.

Required behavior:
- use one canonical metadata sanitization path for standard `Keywords` and
  custom `X-Keywords-*` fields;
- preserve enough readable meaning for ATS review;
- avoid false warnings caused only by inconsistent escaping.

### 5. Decimal percentages are reported incorrectly
`ats-check` currently reports `99.9%` as `9%`.

Required behavior:
- detect integer and decimal percentages;
- report `99.9%` as `99.9%`;
- keep preserving checks conservative and explainable.

### 6. Required sections still include `Summary`
The generated resume uses `Profile`, but `ats-check` still expects `Summary` and
passes only by approximate matching.

Required behavior:
- treat `Profile` as the canonical required section for the current templates;
- optionally support `Summary` as an accepted alias;
- avoid relying on approximate matching for normal generated PDFs.

### 7. Diagnostics for empty extraction are not actionable enough
`ats-check` correctly fails when `pdftotext` returns empty output, but the message
does not explain likely build-level causes.

Required behavior:
- when text extraction is empty, include diagnostic hints such as:
  - PDF may be partially generated after LaTeX failure;
  - font loading may have failed;
  - `pdffonts` should be checked;
  - build logs may contain `luaotfload` or `fontspec` errors.

### 8. Default density rules include too much optional content
The default density behavior should favor essential resume content, especially in
`compact` mode.

Required behavior:
- make `compact` prioritize:
  - profile;
  - experience;
  - education;
  - skills;
  - strongest project or projects;
  - essential certifications when present.
- make optional sections such as awards, volunteer, languages, and extra links
  density-aware rather than always rendered when present.
- keep `full` capable of rendering more content, but avoid obviously poor output
  such as a nearly empty final page caused by a tiny optional section.

### 9. GPA and honors should not be packed into the degree column
Education currently renders degree, GPA, and honors together in the right column.
Long values wrap awkwardly and reduce readability.

Required behavior:
- render degree as the primary right-column education value;
- render GPA and honors on a separate education sub-line;
- keep the extracted text order sensible:
  - institution;
  - degree;
  - location;
  - date range;
  - GPA/honors.

### 10. Isolated extra link sections need a density rule
When `extra_links` contains only one item, rendering a standalone `Online` section
can create a visually weak final section or an almost empty final page.

Required behavior:
- treat this as a density policy rule, not as a layout-fit heuristic;
- in `compact`, hide the `Online`/extra links section when it contains only one
  link;
- in `compact`, render the `Online`/extra links section when it contains two or
  more links;
- in `full`, keep rendering `extra_links` whenever they are present;
- do not move a single extra link into the header automatically in this task;
- do not add a user-facing option for this behavior in this task.

Rationale:
- `compact` should favor essential content and avoid low-value standalone final
  sections.
- `full` should remain the mode that preserves optional user-provided content.
- Page-fit heuristics can be considered later, but they are more complex because
  they require measuring the final rendered PDF.

### 11. Bullet length should be diagnosable
Some input bullets can become too long for scanability and may reduce recruiter
readability even when ATS extraction is technically valid.

Required behavior:
- add this to `ats-check` as a warning, not a failure;
- frame the warning as content quality / scanability guidance, not as strict ATS
  incompatibility;
- warn when an extracted bullet appears unusually long;
- use a conservative threshold to avoid noisy warnings;
- a suggested initial threshold is more than 180 characters for a single bullet;
- if bullet reconstruction from `pdftotext` is ambiguous, prefer fewer warnings
  over false positives;
- do not add a separate `lint` or `content-check` command in this task.

Rationale:
- long bullets usually remain machine-readable, so they should not fail ATS
  validation;
- they can still reduce human scanability and may indicate weak input content;
- adding a warning to `ats-check` is pragmatic for now, while a dedicated content
  lint command can be considered later if these diagnostics grow.

## Required Behavior

### Build hardening
- A PDF must not be considered successfully generated unless text extraction is
  non-empty.
- A PDF must not be considered successfully generated if no fonts are listed.
- Fatal LaTeX/font errors must surface as generation failures.
- Error messages should identify the failing validation step and point to logs
  when `--log` is used.

### Doctor hardening
- `doctor` must validate a real minimal LuaLaTeX/fontspec/DejaVu Sans compile.
- `doctor` must validate extraction and font inspection for that minimal PDF.
- `doctor` must identify likely cache/font permission problems.

### Density behavior
- `compact` should be stricter about optional sections.
- Optional sections should not create low-value final pages by default.
- Education GPA/honors should be rendered separately from the degree.
- In `compact`, a single `extra_links` item should be hidden; two or more
  `extra_links` items should render normally.
- In `full`, `extra_links` should render whenever present.

### ATS diagnostics
- Decimal percentages must be reported accurately.
- `Profile` must be accepted as the canonical required section.
- Empty extraction diagnostics should point toward likely build causes.
- Bullet length/content verbosity must produce actionable `ats-check` warnings,
  using conservative thresholds and never causing a failure.

## Acceptance Criteria
1. Generation fails when LuaLaTeX produces a PDF with empty `pdftotext` output.
2. Generation fails when `pdffonts` reports no fonts for the produced PDF.
3. Generation does not silently accept fatal `luaotfload`/`fontspec` failures.
4. `doctor` compiles and validates a minimal `fontspec` + `DejaVu Sans` PDF.
5. `doctor` reports actionable cache/font-loading failures.
6. `ats-check` reports decimal percentages correctly.
7. `ats-check` treats `Profile` as a normal required section.
8. Metadata keyword comparison no longer warns for escaping-only differences.
9. `compact` renders a more essential resume by default.
10. GPA and honors render on a separate education sub-line.
11. A single `extra_links` item does not create a standalone low-value final
    section in compact output.
12. `full` still renders a single `extra_links` item when present.
13. `ats-check` warns, but does not fail, when a bullet is unusually long.
14. The four validation combinations pass after changes:
    - `compact` + `standard-headline-inline`
    - `compact` + `standard-headline-tabular`
    - `full` + `standard-headline-inline`
    - `full` + `standard-headline-tabular`

## Suggested Verification
```bash
./curriculum-gen doctor

./curriculum-gen generate data/candidate.json -o output/validation/compact-inline.pdf --density compact --layout standard-headline-inline --locale en
./curriculum-gen generate data/candidate.json -o output/validation/compact-tabular.pdf --density compact --layout standard-headline-tabular --locale en
./curriculum-gen generate data/candidate.json -o output/validation/full-inline.pdf --density full --layout standard-headline-inline --locale en
./curriculum-gen generate data/candidate.json -o output/validation/full-tabular.pdf --density full --layout standard-headline-tabular --locale en

./curriculum-gen ats-check output/validation/compact-inline.pdf
./curriculum-gen ats-check output/validation/compact-tabular.pdf
./curriculum-gen ats-check output/validation/full-inline.pdf
./curriculum-gen ats-check output/validation/full-tabular.pdf

pdftotext output/validation/compact-inline.pdf -
pdffonts output/validation/compact-inline.pdf
pdfinfo output/validation/compact-inline.pdf
```

The implementing agent should also test:
- a simulated build failure, such as an unavailable font or unwritable TeX font
  cache, and verify that generation fails instead of producing a successful
  empty-text PDF;
- compact output with exactly one `extra_links` item and confirm the `Online`
  section is omitted;
- compact output with two `extra_links` items and confirm the `Online` section
  is rendered;
- full output with exactly one `extra_links` item and confirm the `Online`
  section is rendered;
- a deliberately long bullet and confirm `ats-check` emits a warning without
  failing the PDF.
