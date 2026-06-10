# 043 - Refine experience header layout and fix employment type rendering

**Date:** 2026-06-10  
**Agent:** opencode (deepseek-v4-flash)

## Context

The `standard` layout had two bugs in experience entries:

1. `employment_type` was rendered as a separate `\resumeEntrySub` line below
   technologies instead of being inline with `location` in the header metadata.
2. The locale key `label.employment_type` appeared raw in the PDF output instead
   of its translated value (`Type` / `Tipo`), caused by stale `.mo` files that
   predated the addition of that msgid.

## Changes Made

### `src/hirepaper/generator.py` — `_render_experience()`

- Removed the `exp.employment_type` block that emitted
  `\resumeEntrySub{<label>: <value>}` as a detached sub-line.
- Added a composited left-metadata string that joins `location` and
  `employment_type` with ` | ` (literal pipe with surrounding spaces).
- The composited string is passed as the 4th argument to `\resumeEntry`,
  which renders it as the left-side metadata below the company name.
- Edge cases handled:
  - Both present: `São Paulo, SP | CLT`
  - Only location: `São Paulo, SP`
  - Only employment_type: `CLT`
  - Neither: `""` (empty, renders cleanly)

### `src/hirepaper/generator.py` — `\mbox{}` removal from right-column fields

The `\mbox{}` LaTeX wrapper prevents line breaking — the box is rendered as a
single unbreakable unit. When used in the narrow right column (32% of textwidth)
of `\resumeEntry` / `\resumeVolunteer`, long text overflows the column boundary
instead of wrapping naturally inside the cell.

Removed `\mbox{}` from all fields rendered in the right column:

| Renderizador | Campo | Argumento `\resumeEntry` |
|---|---|---|
| `_render_experience` | `position` | #2 (coluna direita) |
| `_render_education` | `institution` | #2 (coluna direita) |
| `_render_projects` | `role` | #2 (coluna direita) |
| `_render_volunteer` | `position` | #2 (`\resumeVolunteer`, direita) |

Left-column fields (68% width) keep `\mbox{}` since they have ample space:
`company`, `degree`, `proj.name`, `organization`.

### `locale/en/LC_MESSAGES/messages.mo` and `locale/pt_BR/LC_MESSAGES/messages.mo`

Recompiled from `.po` sources with `msgfmt`. The stale `.mo` files (May 28)
did not contain the `label.employment_type` entry added in the `.po` files
(June 8). With the layout fix this label is no longer emitted for experience
entries, but the stale catalogs could still affect other code paths in the
future.

## Result

Before:
```
TechCorp Solutions    Senior Software Engineer
São Paulo, SP         mar 2021 -- Atualmente
Python, Django, ...
label.employment_type : CLT
```

After:
```
TechCorp Solutions    Senior Software Engineer
São Paulo, SP | CLT   mar 2021 -- Atualmente
Python, Django, ...
```

## Verification

```bash
./hirepaper-dev pdf generate data/candidate.json -o tmp/spec043-dev.pdf --density compact --locale pt-BR
./hirepaper-dev pdf check tmp/spec043-dev.pdf
# → PASS (15 checks, pt-BR compact Skills warning is pre-existing)

./hirepaper-dev pdf generate data/candidate.json -o tmp/spec043-en.pdf --density compact --locale en
./hirepaper-dev pdf check tmp/spec043-en.pdf
# → PASS

.venv/bin/python build.py
./hirepaper pdf generate data/candidate.json -o tmp/spec043-pkg.pdf --density compact --locale en
./hirepaper pdf check tmp/spec043-pkg.pdf
# → PASS
```

LaTeX extraction confirmed:
```latex
\resumeEntry{\mbox{TechCorp Solutions}}{Senior Software Engineer}{mar 2021 -- Atualmente}{São Paulo, SP | CLT}
\resumeEntry{\mbox{StartupXYZ}}{Software Engineer}{fev 2018 -- fev 2021}{Campinas, SP | PJ}
\resumeEntry{\mbox{WebDev Agency}}{Junior Software Engineer}{jan 2016 -- jan 2018}{São Paulo, SP}
```

No `label.employment_type` leak in any locale/density combination.

## Residual Risks

- The pt-BR compact density ATS check reports "Required sections not found:
  Skills" for the sample candidate. This is a pre-existing density/translation
  coverage issue, not caused by this change.
- Other code paths that call `locale.get('label.employment_type')` (outside
  experience rendering) will now correctly resolve to `Type` / `Tipo` thanks
  to the recompiled `.mo` files.
