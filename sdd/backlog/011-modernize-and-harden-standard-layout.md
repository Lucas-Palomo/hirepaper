# 011 - Modernize and harden the standard layout

## Status
Completed

## Context
The current `standard` layout works, but the resulting PDF still feels visually messy in important places and does not yet represent the desired balance between modern presentation and ATS safety.

This task is not about creating a new layout family. It is about improving the existing `standard` layout so that it looks more deliberate, more modern, and more readable while staying compatible with ATS parsing.

## Goal
Upgrade the current `standard` layout so it becomes:
- visually cleaner and more modern;
- more readable and better structured;
- safer for ATS extraction and parsing.

ATS safety is the first priority. Visual modernization must not reduce extraction quality or make the PDF harder for ATS systems to parse.

## Required File Handling
Update:

```text
templates/resume.cls
```

to contain the improved `standard` layout.

## Core Instruction For The Implementing Agent
Modernize the resume, but keep it ATS-safe first.

That means:
- prefer clean hierarchy, spacing, and typography over decorative complexity;
- avoid visual techniques that harm text extraction;
- preserve linear reading order;
- keep the PDF searchable and machine-readable;
- do not trade parsing safety for a more stylish look.

If there is tension between aesthetics and ATS safety, choose ATS safety.

## Scope
This task covers the `standard` layout only.

It may include changes to:
- `templates/resume.cls`
- supporting layout behavior in `templates/resume.tex`
- small generator adjustments when needed to support better structure in the same layout

It does not require:
- creating multiple layouts;
- changing the core data model;
- redesigning density policies from scratch.

## Primary Problems To Address
The implementing agent should specifically review and improve:

### 1. Visual clutter
The current layout feels cramped or uneven in some sections.

The task should improve:
- spacing rhythm between sections;
- spacing between entries;
- consistency of sub-lines and bullets;
- balance between dense content and readable structure.

### 2. Header quality
The header should look cleaner and be easier to scan.

It should avoid:
- visually noisy link presentation;
- contact information collapsing into an unreadable line;
- weak separation between candidate identity and supporting links.

### 3. Section structure
Sections should feel more coherent and less mechanically stacked.

The task should review:
- title hierarchy;
- divider usage;
- section spacing;
- how compact sections such as certifications and languages are rendered.

### 4. Experience readability
Experience entries should remain the strongest part of the document.

The task should improve:
- alignment and readability of role/company/date/location information;
- distinction between metadata, role summary, technologies, and bullets;
- bullet legibility and vertical rhythm.

### 5. ATS-safe rendering
The improved layout must remain ATS-safe.

Avoid or carefully justify:
- fragile multi-column structures;
- decorative glyphs that degrade extraction;
- hidden links;
- icon-driven meaning;
- layout tricks that break linear text order;
- structures known to produce poor extraction.

## Recommended Direction
The implementing agent should aim for a resume that feels:
- modern through restraint, not decoration;
- clear through spacing and hierarchy;
- professional through alignment and typography discipline;
- ATS-safe through simplicity of document structure.

Good modernization examples for this task:
- cleaner heading system;
- more controlled whitespace;
- better grouping of related information;
- calmer and more readable header;
- clearer experience blocks;
- less visually noisy link and metadata treatment.

Bad modernization examples for this task:
- icon-heavy header;
- decorative sidebars;
- multi-column visual experimentation;
- hidden or symbolic links;
- card-like resume sections;
- overly thin or overly stylized typography;
- anything that risks poor `pdftotext` output.

## ATS-Safe Constraints
The final layout should continue to respect these principles:
- text must remain extractable;
- reading order must remain sensible;
- section names must remain explicit;
- URLs or link meaning must remain visible enough for parsing and review;
- no dependence on graphical ornaments for meaning;
- no regression in metadata or extraction behavior validated by `ats-check`.

## Relationship With Existing Validation
The improved layout should continue to work with the existing:
- metadata embedding;
- `ats-check`;
- PDF generation flow;
- density behavior.

If layout changes reveal problems in extraction or validation, fix them as part of this task when they are directly caused by the layout update.

## Acceptance Criteria
The task should be considered complete only if:

1. `templates/resume.cls` is updated with the improved layout;
2. the `standard` layout looks cleaner, more modern, and more intentional;
3. the result remains ATS-safe in structure and extraction behavior;
4. header readability is improved;
5. section spacing and hierarchy are improved;
6. experience entries are easier to scan;
7. the updated layout still works with current generation and `ats-check`.

## Suggested Verification
The implementing agent should verify at least:

```bash
curriculum-gen generate data/candidate.json -o output/resume.pdf -l pt-BR --density compact
curriculum-gen generate data/candidate.json -o output/resume-full.pdf -l pt-BR --density full
curriculum-gen ats-check output/resume.pdf
curriculum-gen ats-check output/resume-full.pdf
```

The review should consider both:
- visual quality of the rendered PDF;
- ATS compatibility signals.

## Notes For The Implementing Agent
- The mission is not "make it fancy". The mission is "make it modern and clean without hurting ATS".
- Treat ATS safety as the first-order constraint and modernization as the second-order objective.
