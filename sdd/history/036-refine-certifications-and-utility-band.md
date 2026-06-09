# 036 — Refine certifications and utility band (pipe separator, two-line entries, softened languages)

**Date:** 2026-06-08
**Agent:** opencode (deepseek-v4-flash)

---

## Context
Certifications were over-compressed into one overloaded line. Languages used bold labels that visually dominated the utility band. The two-column band lacked a visual separator between columns.

## Changes

### `standard.cls` — `\resumeCertification`
Changed from one-line (`Name — Issuer \hfill Date`) to two-line layout:
- Line 1: certification name (bold)
- Line 2: issuer `---` date (em-dash separator, no `\hfill`)

```latex
\newcommand{\resumeCertification}[3]{%
  \noindent
  {\fontsize{9.5}{11.5}\selectfont\textbf{#1}\par}%
  {\fontsize{9.5}{11.5}\selectfont #2 --- #3\vspace{3pt}\par}%
}
```

### `standard.cls` — `\resumeLanguage`
Removed `\textbf{}` from language label — renders as regular weight for softer visual tone.

### `generator.py` — utility band column specification
- Added `!{\color{subdued!40!white}\vrule}` as a vertical pipe separator between the two columns.
- Reduced left column from `0.66\textwidth` to `0.60\textwidth` (60% certifications, 4% spacing+pipe, 30% languages).

## Target structure
```
Certifications                    | Languages
AWS Solutions Architect – Assoc.  | Portuguese: Native
Amazon Web Services — Jun 2023    | English: Fluent (C2)
Certified Kubernetes Admin (CKA)  | Spanish: Intermediate (B1)
CNCF — Nov 2022                   |
```

## Verification
```bash
./curriculum-gen-dev pdf generate data/candidate.json --output /tmp/utility-band-pipe.pdf --density compact --locale en
./curriculum-gen-dev pdf check /tmp/utility-band-pipe.pdf      # PASS (15 checks)
pdftotext /tmp/utility-band-pipe.pdf -
```

All changes verified in source and packaged mode. ATS checks pass (15/15).
