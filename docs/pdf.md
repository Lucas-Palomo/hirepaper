# hirepaper pdf

Generate and validate PDF artifacts.

## Subcommands

- `generate` — Generate a PDF from candidate JSON
- `check` — Validate ATS safety of a PDF

---

## pdf generate

Generate a PDF resume from a candidate JSON file.

The input candidate file accepts **JSONC** format — standard JSON with `//`
line comments and `/* */` block comments. Comments are stripped during parsing.

```bash
hirepaper pdf generate <candidate.json> --output <pdf> [options]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `candidate` | positional | required | Path to candidate JSON |
| `--output`, `-o` | string | **required** | Path for the generated PDF |
| `--locale`, `-l` | string | `en` | Output locale (`en`, `pt-BR`) |
| `--density` | string | `compact` | Rendering density (`compact`, `full`) |
| `--layout` | string | `standard` | Visual layout (currently only `standard`) |
| `--log` | string | — | Save build diagnostics as ZIP archive |

The pipeline converts candidate JSON to LaTeX, then compiles with LuaLaTeX. Icons are converted from SVG via `rsvg-convert`. The generated PDF is validated automatically (text extraction, font embedding). If validation fails, `pdf generate` exits non-zero.

### Density

- `compact` — Prioritizes essential content (experience, education, skills, strongest projects). Hides lower-value optional sections.
- `full` — Preserves more optional content (awards, volunteer, languages, extra links).

### Log archive

When `--log <path>` is provided, the command saves a ZIP archive containing the LaTeX source, candidate JSON, compiler stdout/stderr, and intermediate build artifacts. This is useful for debugging layout issues.

---

## pdf check

Validate a PDF for ATS safety.

```bash
hirepaper pdf check <pdf>
```

| Argument | Type | Description |
|----------|------|-------------|
| `pdf` | positional | Path to the PDF file |

Checks that the PDF:
- Contains extractable text
- Has fonts with Unicode mapping
- Contains no Type 3 fonts
- Includes required resume sections
- Preserves contact info (email, phone, location)
- Preserves visible URLs
- Contains expected keywords from candidate data
- Contains no template placeholder text
- Preserves numeric metrics
- Has correct generation metadata

Exits non-zero if any check fails.
