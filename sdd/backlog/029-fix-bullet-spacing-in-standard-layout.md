# 029 - Fix bullet spacing in standard layout

## Status
Completed

## Context
The `standard` layout renders experience/project/volunteer highlights using a
custom `\resumeHighlights` LaTeX command that outputs raw `-- item\par` inside
a `\par\noindent` block. This approach has two problems:

1. Spacing inconsistency: the first bullet can get extra `\parskip` glue from
   the initial `\par` in `\resumeHighlights`, while subsequent bullets are
   separated only by their own `\par`. The difference in leading space makes
   the first bullet appear visually detached from the rest.

2. Duplicated list logic: the class already defines a complete
   `\setlist[itemize]` configuration with `leftmargin=0pt`, `label={--\ }`,
   `topsep=0.5pt`, `itemsep=0.3pt`, and `before={\fontsize{9.5}{11.5}\selectfont}`
   — but no code was using it for bullet rendering.

## Goal
Make bullet spacing uniform across all items in a highlight block by switching
from manual `-- item\par` to LaTeX's `itemize` environment, which manages
paragraph spacing consistently.

## Changes

### Modified: `templates/standard.cls`
- `\resumeHighlights` now uses `\begin{itemize}...\end{itemize}` instead of
  `\par\noindent\fontsize{...}\selectfont ...\par`.
- `\setlist[itemize]` updated: `label={}` (empty), `labelwidth=0pt` — the
  bullet marker `-- ` is embedded in the item text to keep text flush with
  the left margin, identical to the original positioning.

### Modified: `src/curriculum_gen/generator.py`
- `_render_bullets()` now generates `\item -- {text}` instead of `-- {text}\par`.
  The `-- ` prefix is part of the item text, not the itemize label, preserving
  the original flush-left alignment.

## Verification

```bash
python3 -m py_compile src/curriculum_gen/*.py src/curriculum_gen/llm/*.py
./curriculum-gen-dev pdf generate data/candidate.json --output /tmp/bullet-test.pdf --density compact --locale en
pdftotext /tmp/bullet-test.pdf - | grep -E "^– |^-- "
```

- `py_compile` passed.
- LuaLaTeX compilation succeeded.
- All bullets are visible in `pdftotext` extraction.
- ATS safety preserved: `–` (en-dash) label is extracted as text.

## Acceptance Criteria
1. All bullets in a highlight block have uniform leading space.
2. PDF compiles without errors.
3. Bullet text is extractable by `pdftotext`.
4. No regression in other layout features.
