# 013 - Layout refinement for ATS safety

## Status
Completed

## Context
After adopting LuaLaTeX as the single engine (task 012), the generated PDF is technically ATS-compatible, but the visual layout was still not refined enough for reliable ATS extraction. The original task 012 scope included layout improvements that grew beyond a single task, so they were split into this dedicated task.

Observed layout issues that affect ATS extraction confidence:

- FontAwesome icons in the header still polluted extracted text with unrelated characters (`ć`, `×`, `Ȱ`, etc.) — they could not be removed within the engine task alone.
- The single inline header layout (`resume.tex`) forced all contact info and links into one line, which became visually crowded with more than 3 links and extracted in mixed order.
- The original `Liberation Serif` font has mixed serif/sans-serif usage that is less reliable for OCR-based ATS systems.
- There was no visual separation between experience/project entries, making the extracted text harder to parse.
- The locale labels for contact fields (Email, Phone, Location) were hardcoded in English in the template, not respecting `--locale`.
- The link model (`header: true/false` per link) mixed layout concern into data, making the schema less intuitive.

## Goal
Refine the layout and template system to produce PDFs that are both visually professional and as safe as possible for ATS extraction.

The final project should:
- provide at least one layout option that arranges contact info and links in a clean, extractable format;
- replace font-based icon glyphs with decorative-only image icons that do not appear in extracted text;
- use a single consistent sans-serif font throughout the document for better OCR reliability;
- standardise font sizes (body 10–12pt, section titles 14pt, name 16pt);
- respect locale settings for contact field labels;
- separate the link data model into headline links and extra links at the schema level;
- add subtle visual separators between experience/project entries;
- disable hyphenation to prevent word breaks across lines;
- ensure both layouts pass the ATS check with zero failures.

## Scope
This task may update:
- `src/curriculum_gen/cli.py`
- `src/curriculum_gen/generator.py`
- `src/curriculum_gen/models.py`
- `src/curriculum_gen/loader.py`
- `templates/` (new layout files and modifications)
- `assets/icons/` (SVG icons)
- `locale/` (new label keys)
- `data/candidate.json` and `data/example.json`

This task should not:
- change the LuaLaTeX engine setup or PDF metadata handling (task 012 owns that);
- remove the ATS validation improvements done in task 012;
- introduce a new density policy or section layout family beyond the headline variants.

## Required Behavior

### Layouts
Two official layouts, selectable via `--layout`:
- `standard-headline-inline` (default): contact info and links in a single flow, items spread evenly across the full line width via `\hfill`. Name centered, headline centered, separator rule below headline.
- `standard-headline-tabular` (`--layout standard-headline-tabular`): each contact item (Email, Phone, Location) paired with a link in a tabular row, side by side. Each row shows icon + label: URL.

Both layouts must:
- use `DejaVu Sans` as the single consistent font via `fontspec`;
- disable hyphenation via `\usepackage[none]{hyphenat}`;
- include the separator rule below the headline (not below the contact block);
- show dashed separators (`\xleaders` + `\hbox{- \ }`) centred at 55% width between experience/project entries, never after the last entry;
- use `0.65\textwidth + 0.35\textwidth` for `\resumeEntry` and `\resumeVolunteer` tabulars;
- use `0.60\textwidth + 0.40\textwidth` for `\resumeContactTable` (tabular layout only).

### Icons
Replace `fontawesome5` glyph icons with local decorative SVG icons:
- `assets/icons/envelope.svg`, `phone.svg`, `pin.svg`, `link.svg`
- Converted to PDF at build time via `rsvg-convert`
- Icons must be invisible in `pdftotext` output
- Text labels must always accompany icons (e.g., `Email:`, `Phone:`, `LinkedIn:`)

### Font
- Single face: `DejaVu Sans` (regular, bold) via `\setmainfont{DejaVu Sans}`
- Body text: 10pt (default via `\LoadClass[10pt]`)
- Section titles: 14pt (`\fontsize{14}{17}\selectfont`)
- Name: 16pt (`\fontsize{16}{20}\selectfont`)
- Headline: 11pt (`\fontsize{11}{14}\selectfont`)
- Contact and sub-lines: 10pt (`\fontsize{10}{12}\selectfont`)

### Locale
Contact field labels must use locale keys:
- `label.email` → "Email" (en) / "E-mail" (pt-BR)
- `label.phone` → "Phone" (en) / "Telefone" (pt-BR)
- `label.location` → "Location" (en) / "Localização" (pt-BR)
- `section.links` → "Online" (en) / "Links" (pt-BR)

### Link Data Model
- `personal.links`: links displayed in the headline
- `personal.extra_links`: links displayed in a dedicated "Online"/"Links" section at the end of the document
- Remove `header: bool` from `Link` dataclass

### Entry Separators
Between each experience/project entry, render a dashed line:
- Centred at 55% of `\linewidth`
- Dashes via `\xleaders\hbox{- \ }\hfill`
- Colour: `subdued!40!white`
- Vertical margin: 4pt top and bottom
- No separator after the last entry

## Acceptance Criteria
1. Both layouts compile without LaTeX errors.
2. `curriculum-gen ats-check` passes for both layouts (zero failures).
3. `pdftotext` output contains no FontAwesome garbage characters.
4. `pdftotext` output contains no `[link]` or `[credential]`.
5. Contact fields show correct locale labels for `en` and `pt-BR`.
6. Fonts are DejaVu Sans only (checked via `pdffonts`).
7. No Type 3 fonts present.
8. SVG icons are invisible in extracted text.
9. Dashed separators appear between entries, not after the last one.
10. `--layout standard-headline-tabular` produces the paired row format.

## Suggested Verification
```bash
./curriculum-gen doctor
./curriculum-gen generate data/candidate.json --output output/resume.pdf --locale en
./curriculum-gen ats-check output/resume.pdf
pdftotext output/resume.pdf -
pdffonts output/resume.pdf

./curriculum-gen generate data/candidate.json --output output/resume-tabular.pdf --locale en --layout standard-headline-tabular
./curriculum-gen ats-check output/resume-tabular.pdf
pdftotext output/resume-tabular.pdf -

./curriculum-gen generate data/candidate.json --output output/resume-pt.pdf --locale pt-BR
pdftotext output/resume-pt.pdf - | grep -E "E-mail|Telefone|Localização|Links"
```
