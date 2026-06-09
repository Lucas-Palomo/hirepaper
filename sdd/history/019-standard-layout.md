# 019 - Add new `standard` layout and deprecate legacy standard variants

**Date:** 2026-05-30
**Agent:** opencode (deepseek-v4-flash)

## Context
The project had two legacy standard-family layouts (`standard-headline-inline`, `standard-headline-tabular`) that were becoming maintenance overhead. The product direction called for a single canonical layout with better visual hierarchy, density handling, and page-break behavior.

## Changes Made

### New templates: `templates/standard.cls` and `templates/standard.tex`
- Created a new `standard` layout following **Concept 1: Main Flow + Utility Bands**.
- **Header**: 18pt bold centered name, 11pt subdued headline with thin rule, compact contact block with email/phone/location first line and labeled links below.
- **Main flow sections** (Profile, Experience, Education): full-width, strongest hierarchy, company/position bold with location/dates subdued.
- **Utility sections** (Skills, Certifications, Projects, Languages, Awards, Volunteer, Online): rendered more compactly after the main flow, with 9.5pt font size and tighter spacing.
- **Two-column bottom band**: Certifications (left column) + Languages/Online (right column) rendered side-by-side via tabular, matching the wireframe layout.
- **Page-break protection**: `\needspace{3\baselineskip}` before every section heading; `\nobreak` after entry start to prevent orphaned entry headers.
- **Typography**: DejaVu Sans, 10pt base, teal-blue accent color, clean section rules.
- **Section ordering**: Profile → Experience → Education → Skills → Projects → Certifications+Languages/Online (band) → Awards → Volunteer.
- **Compact utility rendering**: Certifications, Awards rendered as one-line entries; Skills as inline `category: items`; Languages as inline.

### Updated: `src/curriculum_gen/cli.py`
- Added `"standard"` to `_LAYOUT_MAP` — maps to `standard.tex` / `standard.cls`.
- Changed default `--layout` from `"standard-headline-inline"` to `"standard"`.
- Added `_LEGACY_LAYOUTS` set (`standard-headline-inline`, `standard-headline-tabular`).
- Emits a deprecation warning to stderr when a legacy layout is explicitly selected:
  ```
  Warning: layout 'standard-headline-inline' is deprecated and will be removed in a future release; use 'standard' instead.
  ```

### Updated: `src/curriculum_gen/generator.py`
- **Experience sub-line**: Combined technologies, role_summary, and employment_type into a single `\resumeEntrySub` line separated by ` / ` (matching wireframe: "Technology stack / role context / optional contract type").
- **Education**: Changed `_render_education` to merge degree + date_range into the right column and location + GPA + honors into the sub-line (matching wireframe: "Institution | Degree / Date Range" on row 1, "Location / GPA / Honors" on row 2).
- **Collapsible band logic**: Band content (`{BAND}`) is built in Python inside `generate_latex()`. When both certifications and languages/online have content → two-column tabular; when only one side → regular section; when neither → empty. `\resumeSectionRule` is prepended before all band variants to create a visual transition from Projects.
- **Projects layout**: Changed from `\resumeEntry` tabular to plain paragraph format — `Name | Role` (bold), `url \hfill period` + `keywords` as `\resumeEntrySub` lines. Avoids tabular column width mismatch that caused bullets to appear wider than period text.
- **Bullets**: Replaced `itemize` with plain `\par` paragraphs using `-- ` prefix. Eliminates `leftmargin` indentation that shifted bullet text right. Now all text (title, sub-lines, bullets) starts at the same left margin.

### Updated: `src/curriculum_gen/density.py`
- **Compact mode**: Enabled `show_languages=True` so the two-column band renders `certifications | languages` in compact mode (same as full density). `min_extra_links_for_section` kept at 2 to avoid showing Online section in compact.

### New model field: `experience.employment_type`
- Added `employment_type: Optional[str] = None` to `Experience` model.
- Parsed from JSON in `loader.py`.
- Rendered as part of the combined experience sub-line.
- Added `label.employment_type` locale key to both `en` and `pt_BR` translations.

### Updated documentation
- `project.md`: Canonical layout is now `standard`; legacy layouts marked deprecated.
- `agents.md`: Updated command examples and validation section to use `standard` as default.

## Decisions & Tradeoffs
- **Main Flow + Utility Bands** — The canonical layout keeps high-priority sections (Profile, Experience, Education) in the main linear flow and renders supporting sections more compactly afterward. This is ATS-safe and creates a clear reading priority.
- **Two-column bottom band** — Certifications and Languages/Online are rendered side-by-side using a `tabular` with two `\parbox[t]` cells. This matches the wireframe while keeping the band local and compact (not a full-page sidebar).
- **Collapsible band** — The band logic lives in `generate_latex()` rather than the template. It checks which sections have content and either renders a two-column tabular (both sides), a regular section (one side only), or nothing (neither). This ensures graceful collapse when optional sections are absent, matching the backlog requirement.
- **Asymmetric column widths** — Band columns use 66% | 30% split (4% gap) to give certifications more horizontal space and push languages to the right, improving visual balance when the right column has fewer entries.
- **Headline-style section rule** — `\resumeSectionRule` uses the same decorative line as the headline (`\color{accentcolor!50!white}\rule{\textwidth}{0.5pt}`) to separate Projects from the band, creating a clear rhythm break while remaining purely visual (no text extraction pollution).
- **Experience sub-line merged** — Technologies, role_summary, and employment_type are combined into a single `\resumeEntrySub` line with ` / ` separators, matching the wireframe's "Technology stack / role context / optional contract type" pattern.
- **Education entry restructured** — Degree and date_range are now combined in the right column, with location + GPA + honors as the sub-line. This required changing `_render_education`, which also improves legacy layouts slightly.
- **Page-break protection** — Used `\needspace{1.5\baselineskip}` with `\nopagebreak[3]` before and after section headings. Reduced from 3\baselineskip to avoid needlessly forcing page breaks for compact content.
- **Spacing tuning for one-page fit** — Compact mode fits on one page even with languages enabled. Changes: top/bottom margins 0.3in/0.25in, section heading 12pt with 6pt/1pt spacing, name 16pt, `\parskip` 0.5pt, tight entry and itemize spacing throughout. Full density renders 2 pages with well-distributed content.
- **Certification entry spacing** — `\resumeCertification` `\vspace` set to 5pt, giving comfortable breathing room between entries, especially when URLs are present.
- **Languages enabled in compact** — `show_languages=True` in compact policy so the band renders `certifications | languages` consistently across both density modes.
- **`\resumeBandSection`** — Added a compact section heading command (11pt, no rule) for use inside the two-column band, preventing the full-width section rule from breaking the column layout.
- **`employment_type` as optional field** — Added to the model with zero migration burden. Only renders when present, always as secondary metadata.
- **Deprecation warning on stderr** — Non-blocking, printed to stderr so pipelines can still capture stdout cleanly.
- **Section ordering** — Skills placed before Projects/Certifications since skills are higher-signal for ATS scanning.
- **Margin consistency** — `\resumeHighlights` switched from `itemize` to plain `\par\noindent` paragraphs with `-- ` prefix. Eliminates the `leftmargin` shift that caused bullet text to appear wider than other content. All elements (section headings, titles, sub-lines, bullets, descriptions) now start at the same left edge.
- **Overflow prevention** — `\setlength{\emergencystretch}{0.5em}` added globally to allow LaTeX flexible line breaking when `[none]{hyphenat}` prevents hyphenation. Prevents overfull boxes in profile text and other paragraphs without switching to ragged right.
- **Document margins** — Left/right margins set to 0.40in (narrower than the initial 0.55in) to give text more breathing room while maintaining consistent alignment across all elements.
- **Entry tabular spacing** — Row spacing in `\resumeEntry` tightened from `\\[-2pt]` to `\\[-6pt]` to bring (Company|Role) closer to (Location|Period). Post-tabular `\vspace` increased from `1pt` to `5pt` for clearer separation before keywords/bullets. Same adjustments applied to `\resumeVolunteer`.
- **Section rule spacing** — Space after the section heading rule increased from `2pt` to `5pt` (`\vspace{5pt}` in `\titleformat`). Band section (`\resumeBandSection`) post-title spacing increased from `1pt` to `3pt`. Ensures uniform breathing room between the section rule and the first content line across all sections.

## Visual Design Choices
- **Name**: 18pt bold, centered — the strongest visual element.
- **Section headings**: 13pt bold accent with thin rule — clear but not competing with entry content.
- **Two-column band headings**: 11pt bold accent, no rule — lighter visual weight inside the column layout.
- **Experience entries**: Company/role bold with location/dates subdued — familiar, scannable hierarchy.
- **Entry spacing**: 3pt after entries, 1.5-2pt within — dense enough for compact resumes without compression.
- **Utility sections**: 9.5pt font, tighter spacing, one-line entries where possible.
- **Bullets**: en-dash with 1.1em left margin, 1.5pt item separation.
- **Links**: Labeled visible URLs (`LinkedIn: linkedin.com/in/...`), blue hyperlinks.

## Verification

### Default layout generation + ATS check
```
$ ./curriculum-gen-dev pdf generate data/candidate.json -o output/standard-default.pdf --locale en
→ Generated: output/standard-default.pdf

$ ./curriculum-gen-dev pdf check output/standard-default.pdf
→ PASS (15 checks passed)
```

### Explicit standard layout
```
$ ./curriculum-gen-dev pdf generate data/candidate.json -o output/standard-explicit.pdf --layout standard --locale en
→ Generated: output/standard-explicit.pdf
→ ATS check: PASS (15 checks passed)
```

### Legacy layouts with deprecation warnings
```
$ ./curriculum-gen-dev pdf generate data/candidate.json -o output/legacy-inline.pdf --layout standard-headline-inline --locale en
→ Warning: layout 'standard-headline-inline' is deprecated ... (stderr)
→ Generated: output/legacy-inline.pdf

$ ./curriculum-gen-dev pdf generate data/candidate.json -o output/legacy-tabular.pdf --layout standard-headline-tabular --locale en
→ Warning: layout 'standard-headline-tabular' is deprecated ... (stderr)
→ Generated: output/legacy-tabular.pdf
```

### Compact mode — one page (with languages)
```
$ ./curriculum-gen-dev pdf generate data/candidate.json -o output/standard-compact.pdf --locale en
→ Generated: output/standard-compact.pdf
→ Page count: 1
→ ATS check: PASS (15 checks passed)
→ Band: certifications | languages (two-column, 66% | 30%)
```

### Full density — two pages, well-distributed
```
$ ./curriculum-gen-dev pdf generate data/candidate.json -o output/standard-full.pdf --density full --locale en
→ Generated: output/standard-full.pdf
→ Page count: 2
→ ATS check: PASS with warnings (1 warning, 15 ok)
```

Page 2 contains: second project, certifications + languages (two-column band, 66% | 30%), awards, volunteer — no empty trailing page.

### Section transition
A headline-style rule (`\resumeSectionRule`) separates Projects from the band in both density modes. The rule is purely decorative (accent color, full width, 0.5pt) and does not pollute text extraction.

### Packaged binary
```
$ ./curriculum-gen pdf generate data/candidate.json -o /tmp/packaged-standard.pdf
→ Generated: /tmp/packaged-standard.pdf
→ 1 page
```

### Text extraction
All sections present in sensible reading order. Contact info, URLs, percentages, and keywords all recoverable. No placeholder leakage.

### Fonts
- No Type 3 fonts.
- DejaVuSans / DejaVuSans-Bold, CID TrueType, Identity-H encoding, embedded subset.
- ATS-safe.

## Residual Risks
- Legacy layouts (`standard-headline-inline`, `standard-headline-tabular`) still function but should be removed in a future breaking-change task.
- The `standard` layout has not been tested with very long resumes (5+ pages). Page-break behavior should be monitored in real-world usage.
- `employment_type` is new and untested with real candidate data beyond the test fixture.

## Follow-up Items
- Remove legacy layouts in a future task.
- Fine-tune band column widths as more real-world candidate data becomes available.
