# 011 — Modernize and harden the standard layout

**Date:** 2026-05-28
**Agent:** opencode (deepseek-v4-flash)

---

## Context

The existing `standard` layout worked but felt visually cramped and uneven.
Section spacing, header presentation, and experience entry readability needed
improvement. The task was to modernize without harming ATS extraction quality.

## Changes

A new `resume.cls` was created inspired by the wireframe semantics of
Awesome CV, replacing the previous layout entirely.

### Header (centered)

```
              João Silva (centro)
  Senior Software Engineer — ... (centro)
ć email  |  × phone  |  Ȱ location (centro)
] linkedin.com/in/...  |  a github.com/... (centro)
──────────────────────────────────── (accent rule)
```

- Name in `\LARGE\bfseries`, headline in `\small\itshape\color{subdued}`
- Contact with `\faIcon{envelope}`, `\faIcon{phone}`, `\faIcon{map-marker-alt}`
- Links with `\faIcon{linkedin}` etc. + clean URL (no `https://`)
- All centered via `\centering`

### Experience entries

```
TechCorp Solutions                 Senior Software Engineer
São Paulo, SP                      Mar 2021 -- Present
```

- Tabular with `p{0.7\textwidth}` left + `p{0.27\textwidth}` right columns
- Left column `\raggedright`, right column `\raggedleft`
- Row gap tightened with `\\[-3pt]`

### Sections

- Accent color (`#1a6b8a`) section headings
- Thin extended rule in `accentcolor!40!white`
- Bullets: `\textendash` with `itemsep=2pt`

### Technical details

- **Class**: `templates/resume.cls`
- **Font Awesome**: `fontawesome5` with `\faIcon{}` for all icons
- **Engine**: xelatex (default), pdflatex (backward compatible)

## Verification

```bash
./curriculum-gen generate data/candidate.json -o output/resume.pdf
./curriculum-gen ats-check output/resume.pdf
```

ats-check: PASS with 2 warnings (generic link labels, no explicit URLs — both expected).
