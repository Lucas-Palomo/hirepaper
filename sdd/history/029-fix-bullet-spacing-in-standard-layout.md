# 029 - Fix bullet spacing in standard layout

**Date:** 2026-06-06
**Agent:** opencode (deepseek-v4-flash)

---

## Context

The `\resumeHighlights` command in `standard.cls` used `\par\noindent` then
relied on raw `-- item\par` for each bullet. This bypassed LaTeX's `itemize`
spacing model entirely.

The class already had a detailed `\setlist[itemize]` configuration:
- zero left margin, `--` label, controlled `topsep`/`itemsep`/`parsep`
- `\fontsize{9.5}{11.5}\selectfont` applied via `before=`

But `generator.py`'s `_render_bullets()` never used `itemize` — it emitted
`-- item\par` directly. The first bullet could receive extra `\parskip` glue
from the initial `\par` in `\resumeHighlights`, making it appear with a
larger leading space than subsequent bullets.

## Changes

### Modified: `templates/standard.cls`

```latex
% Before:
\newcommand{\resumeHighlights}[1]{%
  \par\noindent
  \fontsize{9.5}{11.5}\selectfont
  #1%
  \par%
}
\setlist[itemize]{leftmargin=0pt, labelindent=0pt, itemindent=0pt,
  labelwidth=0.6em, topsep=0.5pt, itemsep=0.3pt, parsep=0pt,
  label={--\ }, before={\fontsize{9.5}{11.5}\selectfont}}

% After:
\newcommand{\resumeHighlights}[1]{%
  \begin{itemize}
    #1%
  \end{itemize}%
}
\setlist[itemize]{leftmargin=0pt, labelindent=0pt, itemindent=0pt,
  labelwidth=0pt, topsep=0.5pt, itemsep=0.3pt, parsep=0pt,
  label={}, before={\fontsize{9.5}{11.5}\selectfont}}
```

- `\setlist[itemize]` label changed from `{--\ }` to `{}` (empty) and
  `labelwidth` from `0.6em` to `0pt`. The bullet marker is no longer a
  separate label — it becomes part of the item text to avoid indentation.

### Modified: `src/curriculum_gen/generator.py`

```python
# Before:
bullets = "\n".join(f"-- {item}\\par" for item in items)

# After:
bullets = "\n".join(f"\\item -- {item}" for item in items)
```

## Verification

- `py_compile` passed.
- LuaLaTeX compilation succeeded, PDF renders on 2 pages.
- `pdftotext` confirms all bullet text is extractable with `– ` prefix.
- Bullets now use consistent `itemize` spacing for every item.
- Bullet text starts at the same left margin as surrounding content (entry
  titles, company names, description text).
