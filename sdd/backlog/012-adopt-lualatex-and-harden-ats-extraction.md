# 012 - Adopt LuaLaTeX and harden ATS extraction

## Status
Completed

## Context
The generated PDF currently passes the existing `ats-check` command, but manual inspection of `pdftotext` output revealed ATS extraction regressions that should be fixed before calling the output fully ATS-safe.

The project should also simplify its LaTeX engine support. Instead of maintaining compatibility branches for `pdflatex` and `xelatex`, the project should make `lualatex` the single officially supported rendering engine.

LuaLaTeX is a good fit for this project because it supports Unicode and OpenType fonts through `fontspec`, like XeLaTeX, while also being a modern and programmable TeX engine. The project does not need Lua-specific behavior immediately, but choosing one modern engine reduces conditional code and makes ATS validation more deterministic.

The `resume.tex` used during the analysis that led to this task was manually copied/extracted from the `logs/` directory into the project root only to make review easier. That root-level file was temporary and is not produced there by the generator. Implementing agents should not rely on any root-level `resume.tex`; they should regenerate fresh artifacts with `--log` whenever they need to inspect the produced `.tex`, `.log`, or engine output.

Observed extraction issues include:
- FontAwesome icons in the header extracting as unrelated characters such as `ć`, `×`, `Ȱ`, `]`, `a`, `p`, and `ç`;
- generic link labels such as `[link]` and `[credential]` instead of visible URLs;
- at least one unescaped percent sign in generated achievement text, causing `25%` to extract as `25`;
- table-based entry layout producing less stable reading order in some sections.

These are not catastrophic failures, but they reduce confidence that generated PDFs are robust across ATS parsers.

## Goal
Make LuaLaTeX the single official PDF rendering engine and improve the generated LaTeX/layout so the resulting PDF is more reliably ATS-safe.

The final project should:
- render PDFs through `lualatex` by default;
- stop advertising or supporting `pdflatex` and `xelatex` as official engines;
- preserve all candidate text exactly enough for ATS keyword matching;
- avoid decorative glyph noise in extracted text;
- expose URLs or meaningful link text in extracted text;
- preserve a sensible linear reading order;
- continue to pass `curriculum-gen ats-check`.

## Scope
This task may update:
- `src/curriculum_gen/cli.py`
- `src/curriculum_gen/generator.py`
- `src/curriculum_gen/ats_check.py`
- `templates/resume.tex`
- `templates/resume.cls`
- project docs, backlog references, and verification instructions that mention `pdflatex` or `xelatex`
- tests or fixtures if the implementing agent adds them

This task should not:
- introduce a new layout family;
- change the candidate JSON schema unless absolutely necessary;
- depend on a commercial or resume-specific ATS parser;
- keep best-effort compatibility with legacy engines if it complicates the official LuaLaTeX path.

## Engine Policy
After this task, `lualatex` is the only officially supported engine.

Required behavior:
- default generation engine should be `lualatex`;
- the `--engine` CLI option is deprecated by this change and should be removed;
- generation should always use `lualatex`;
- `doctor` should check only for `lualatex` as the LaTeX engine requirement;
- help text should not present `pdflatex` or `xelatex` as supported choices;
- metadata should report `lualatex` as the generation engine;
- code paths that exist only to support `pdflatex` or `xelatex` should be removed or simplified where practical.

Do not keep a best-effort `--engine` compatibility path. A single-engine project should have a single rendering path.

## Primary Problems To Address

### 1. Migrate rendering to LuaLaTeX
Review the LaTeX class and template for LuaLaTeX compatibility.

The implementing agent must update the current LaTeX template files themselves, not only the Python command that invokes the engine:

```text
templates/resume.cls
templates/resume.tex
```

Bring both files into a LuaLaTeX-first shape. Remove or simplify engine branches, package choices, metadata commands, font setup, and template assumptions that exist only for `pdflatex` or `xelatex`.

Important areas:
- font loading through `fontspec`;
- PDF metadata generation;
- package compatibility;
- Unicode handling;
- generated PDF text extraction through `pdftotext`;
- font inspection through `pdffonts`.

Avoid engine-conditional blocks unless they are still necessary under the new single-engine policy.

### 2. Escape generated achievement text consistently
The generated `resume.tex` contained an unescaped percent sign:

```tex
\item Developed real-time notification system using WebSockets — improving user engagement by 25%
```

In LaTeX, `%` starts a comment. The extracted PDF text therefore loses the percent sign and can drop following text depending on line structure.

Fix the generator so all achievement paths escape TeX special characters consistently, including composed achievements built from `action`, `result`, and `metrics`.

Likely area:

```text
src/curriculum_gen/generator.py
```

Specifically review `_render_achievement_bullet`.

### 3. Replace font-based icons with an ATS-safe visual alternative
The current header uses FontAwesome icons for email, phone, location, and social links.

These icons are visually useful but extract as noisy unrelated characters in `pdftotext`, because the FontAwesome fonts do not expose useful Unicode mappings for those glyphs.

Do not simply remove the visual concept of icons unless no safe alternative is practical. The implementing agent should first investigate whether the icon treatment can be preserved without using icon fonts.

Preferred direction:
- replace FontAwesome/font-glyph icons with ATS-safe decorative image icons, if they can be embedded without polluting `pdftotext` output;
- keep explicit visible text labels or meaningful adjacent text for every contact/link item;
- ensure the icon is decorative only and never the sole carrier of meaning;
- remove the `fontawesome5` dependency if font icons are no longer used.

Examples of acceptable extracted text:

```text
Email: joao.silva@email.com | Phone: +55 11 99999-9999 | Location: São Paulo, SP
LinkedIn: linkedin.com/in/joaosilva | GitHub: github.com/joaosilva
```

The rendered PDF may still show small icons next to those labels, but those icons must not appear as garbage characters in extracted text.

If image icons are used, prefer a simple, maintainable asset strategy:
- small monochrome PDF/PNG assets checked into the project; or
- generated vector/raster assets that are stable and deterministic enough for the build;
- no remote image loading during resume generation.

If image icons prove fragile, too complex, or harmful to extraction, fall back to text-only labels and document why.

ATS safety should take precedence over icon styling.

### 4. Make links visible and meaningful in extracted text
The PDF currently exposes generic labels such as:

```text
[link]
[credential]
```

This is weak for ATS and human review of extracted text.

Project and certification links should render with visible, meaningful text, preferably the clean URL already used in the header.

Examples:
- `github.com/fastapi-admin/fastapi-admin`
- `blog.joaosilva.dev`
- `aws.amazon.com/verify/credential`

Avoid hiding important link destinations behind `[link]` or `[credential]`.

### 5. Improve linear reading order where tables hurt extraction
The standard layout uses `tabular` for experience, education, and volunteer entries.

The current extraction is mostly readable, but dates, locations, roles, and education details can appear in a less natural order.

Review whether these blocks can be rendered with simpler linear LaTeX while preserving visual quality.

Preferred output shape in extracted text:

```text
Company
Role
Location
Date range
Technologies
Bullets...
```

The visual layout may still be clean and modern, but it must not depend on fragile multi-column parsing.

### 6. Strengthen ATS validation to catch these regressions
The existing `ats-check` passed despite the issues above.

Enhance validation where practical so it can warn or fail on:
- suspicious icon-extraction garbage near contact lines;
- known generic link labels;
- missing percent signs for metrics that are expected from metadata or source content, if feasible;
- obvious LaTeX comment loss patterns in generated text;
- lack of visible URLs when source links exist, if the check has enough metadata to infer this;
- PDFs whose metadata reports a non-`lualatex` generation engine.

Do not overfit to a single sample resume. Keep checks explainable and conservative.

## Required Behavior
After this task, a generated compact PDF from `data/candidate.json` should have clean extracted text and should be generated with LuaLaTeX.

At minimum, `pdftotext` output should:
- include `25%`, `80%`, `40%`, `90%`, `99.9%`, and `60%` where present in the source data;
- not include FontAwesome garbage characters before contact/link text;
- not include `[link]` or `[credential]` as the only visible destination text;
- include visible contact data;
- include visible project and credential URLs;
- preserve the core section names and technical keywords.

At minimum, PDF metadata should:
- include `X-App: curriculum-gen`;
- include `X-Engine: lualatex`;
- preserve candidate author, subject, and keyword metadata.

## Acceptance Criteria
The task should be considered complete only if:

1. `lualatex` is the default and only officially supported rendering engine.
2. The `--engine` option is removed from the generate command.
3. `doctor`, CLI help, and generation behavior reflect the new LuaLaTeX-only policy.
4. `doctor` checks only `lualatex` as the required LaTeX engine.
5. Generated achievements escape TeX special characters correctly in all paths.
6. Header contact extraction no longer contains FontAwesome garbage characters.
7. The agent evaluates an image-based or otherwise ATS-safe icon alternative before choosing text-only labels.
8. Project and certification links expose meaningful visible text or clean URLs.
9. The standard layout preserves a sensible extracted reading order.
10. `curriculum-gen ats-check` passes for the LuaLaTeX-generated PDF.
11. `pdftotext` output from the generated PDF is manually reviewed and documented in the completion notes.
12. The validator is improved if any issue can be caught objectively without making the check brittle.
13. No documentation or task verification command continues to recommend `pdflatex`, `xelatex`, or an `--engine` override.

## Suggested Verification
The implementing agent should verify at least:

```bash
./curriculum-gen doctor
./curriculum-gen generate data/candidate.json --output output/resume.pdf --locale en --density compact --log
./curriculum-gen ats-check output/resume.pdf
pdftotext output/resume.pdf -
pdffonts output/resume.pdf
pdfinfo output/resume.pdf
```

Verify the deprecated `--engine` option is no longer accepted:

```bash
./curriculum-gen generate data/candidate.json --output output/resume.pdf --locale en --engine xelatex --density compact
```

If possible, also verify:

```bash
./curriculum-gen generate data/candidate.json --output output/resume-full.pdf --locale en --density full --log
./curriculum-gen ats-check output/resume-full.pdf
pdftotext output/resume-full.pdf -
```

Manual review should explicitly check the generation engine metadata, contact header, project links, credential links, percentages, section ordering, and keyword preservation.

The `--log` flag is required for this verification because it persists the generated `resume.tex` and related LaTeX build artifacts under `logs/`. Inspect those fresh files rather than relying on any manually copied or stale root-level `resume.tex` artifact.

## Notes For The Implementing Agent
- LuaLaTeX and XeLaTeX are both modern Unicode-capable engines, but this project should standardize on LuaLaTeX to reduce variability.
- Passing the current validator is necessary but not sufficient.
- Treat `pdftotext` output as a first-class artifact.
- Do not preserve FontAwesome/font-based icons if they continue to pollute extraction.
- Image icons are acceptable only when they are decorative, local, maintainable, and absent from extracted text.
- Prefer plain, explicit text over decorative symbols for ATS-facing content.
- Keep the resume visually professional, but make extraction quality the deciding constraint.
