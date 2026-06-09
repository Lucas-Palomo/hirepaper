# 001 — Pipeline Initialization (JSON → LaTeX → PDF)

**Date:** 2026-05-27
**Agent:** opencode (deepseek-v4-flash)

---

## Context

The `curriculum-gen` project generates resumes from structured data.
The `sdd/` directory contained two instruction files (`agent.md` and `agent-context.md`)
that defined the scope, constraints, and degree of autonomy for the first iteration.

## Architecture Decisions

### 1. Language and dependencies

**Decision:** Pure Python with the standard library. No external dependencies.

**Rationale:** The pipeline is simple (read JSON → transform → write .tex). The standard
library (`json`, `pathlib`, `dataclasses`) covers everything. Avoiding dependencies
reduces installation friction and failure points.

### 2. Directory structure

```
curriculum-gen/
├── data/              → input data (JSON)
├── templates/         → LaTeX class and template
├── src/               → Python source code
│   ├── models.py      → data model dataclasses
│   ├── loader.py      → JSON loading and validation
│   └── generator.py   → Candidate → LaTeX transformation
├── output/            → generated artifacts (.tex, .pdf)
├── generate.py        → CLI entry point
└── sdd/               → decision support documents
```

**Rationale:** Clear separation between data, presentation, and logic. The generator
does not know the `.cls` structure — it only invokes LaTeX commands defined in the
template.

### 3. JSON Schema

**Decision:** Explicit schema with named fields, no generic abstractions.

```json
{
  "personal": { "name", "email", "phone", "location", "links": [...] },
  "target_role": "...",
  "summary": "...",
  "experience": [{ "company", "position", "start_date", "end_date", "current", "highlights": [...] }],
  "education": [{ "institution", "degree", "location", "start_date", "end_date", "gpa?" }],
  "skills": { "categories": [{ "name", "items": [...] }] },
  "projects": [{ "name", "description", "technologies": [...], "url?" }],
  "certifications": [{ "name", "issuer", "date" }],
  "languages": [{ "language", "proficiency" }]
}
```

**Rationale:** Explicit preference from `agent-context.md` ("explicit JSON fields over
highly abstract structures"). Makes validation easier, avoids ambiguity, and is
self-documenting.

**Trade-off:** Less flexible for unforeseen data. For a first iteration,
clarity is worth the cost.

### 4. LaTeX Class (resume.cls)

**Decision:** Custom class (`.cls`) instead of a standalone `.tex` template.

**Rationale:** Reuse and isolation. Commands like `\resumeEntry`, `\resumeSkillCategory`,
`\resumeCertification`, etc. encapsulate visual formatting. If the layout changes,
only the `.cls` needs updating — the `.tex` template and the Python generator stay
the same.

**Font decision:** Computer Modern (LaTeX default) with `pdflatex`, no `fontspec`
or TrueType/OpenType fonts.

**Rationale:** Portability. `pdflatex` and CM are available in every TeX distribution.
`fontspec` + `xelatex` requires system-installed fonts, which failed on the first
attempt (TexGyreTermes was not available).

### 5. Template mechanism

**Decision:** Simple placeholders in `.tex` (`{NAME}`, `{EXPERIENCE}`, etc.)
replaced by string replacement in the Python generator.

```python
result = template_text.replace("{NAME}", candidate.personal.name)
```

**Rationale:** The template has ~15 placeholders. `string.Template` or Jinja2 would be
overkill for this case. Direct replacement is straightforward, deterministic, and
introduces no dependencies.

**Trade-off:** If the number of placeholders grows significantly (30+), migrating to
Jinja2 would be worthwhile. For now, simplicity matters more.

### 6. Compilation pipeline

**Decision:** `generate.py` copies `resume.cls` to the output directory before
compiling, so LaTeX can find it.

**Decision:** Use `-interaction=nonstopmode` without `-halt-on-error`, checking PDF
existence at the end instead of relying on the return code.

**Rationale:** `pdflatex` can return non-zero even when the PDF is generated
successfully (e.g., fonts being generated on-the-fly by `mktexpk`). Checking
for the file's existence is more robust.

### 7. Special character escaping

**Decision:** The generator applies `_escape_tex()` to text before inserting it
into the template, replacing `&`, `%`, `$`, `#`, `_`, `{`, `}` with their
escaped forms.

**Rationale:** Real resume data may contain these characters (e.g., "80%",
"C#", "AT&T"). Without escaping, LaTeX silently breaks.

---

## Verified Behavior

```
$ python generate.py --input data/candidate.json --output output/resume
Generated: output/resume.tex
Generated: output/resume.pdf  (2 pages, ~74KB)
```

The generated PDF contains: header with name/contact/links, profile, 3 work
experiences, education, 4 skill categories, 2 projects, 2 certifications,
3 languages.

---

## Deferred Decisions / Not Implemented

- **JSON-customizable template:** The user cannot (yet) choose section ordering
  or colors via JSON. This would be the natural next evolution.
- **Multiple templates:** Only one layout (`.cls`) exists for now.
- **Advanced validation:** No date, email, or URL format validation is performed.
  `loader.py` only checks for required field presence.
- **Automated tests:** No test suite. The pipeline was verified manually.
- **Continuous integration:** Not configured.
