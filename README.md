# hirepaper

**JSON → LaTeX → PDF resume generator**

`hirepaper` takes a structured JSON resume, renders it through a LaTeX template, and produces an ATS-safe PDF — from the command line or as a Python library.

## Pipeline

```
candidate.json → Python data model → LaTeX template → LuaLaTeX → PDF → ATS validation
```

## Features

- Structured JSON input with schema validation
- ATS-safe PDF output (text extraction, fonts, metadata)
- LLM-powered content matching and tailoring against vacancy descriptions
- Two density modes: `compact` and `full`
- Clickable email (`mailto:`) and phone (`tel:`/WhatsApp) hyperlinks
- Locale support (en, pt-BR)
- Single-file binary packaging via PyInstaller
- Importable Python API for embedding in applications

## Prerequisites

- Python ≥ 3.10
- LuaLaTeX (`lualatex`, `luaotfload`)
- `rsvg-convert` (librsvg)
- `pdftotext`, `pdffonts` (poppler-utils)
- `exiftool`

## Install

```bash
pip install git+https://github.com/Lucas-Palomo/hirepaper.git
```

---

## CLI Usage

### Quick Start

```bash
# Run diagnostics
hirepaper doctor

# Bootstrap a starter candidate JSON
hirepaper content init --output my-candidate.json

# Validate candidate data
hirepaper content lint my-candidate.json

# Generate PDF resume
hirepaper pdf generate my-candidate.json --output resume.pdf --locale en

# ATS-safety check
hirepaper pdf check resume.pdf
```

### Commands

| Command | Description |
|---|---|
| `hirepaper init` | Bootstrap a local `config.toml` |
| `hirepaper doctor` | Environment diagnostics |
| `hirepaper content init` | Bootstrap a starter candidate JSON |
| `hirepaper content lint` | Validate candidate JSON quality |
| `hirepaper content match` | ATS-style LLM compatibility analysis |
| `hirepaper content tailor` | Tailor candidate to a vacancy |
| `hirepaper pdf generate` | Generate PDF from candidate JSON |
| `hirepaper pdf check` | ATS-safety validation on a PDF |
| `hirepaper llm health` | LLM connectivity test |
| `hirepaper llm usage` | Token usage diagnostic |
| `hirepaper linkedin generate` | LinkedIn-focused report generation |

---

## Library Usage

`hirepaper` exposes a public API under `hirepaper.api` for embedding workflows
directly in Python without invoking the CLI.

```python
from hirepaper.api import (
    generate_pdf_file,
    check_pdf_file,
    lint_candidate_file,
    bootstrap_candidate_file,
)
```

### End-to-end example

```python
from hirepaper.api import generate_pdf_file, lint_candidate_file, check_pdf_file

# Validate candidate data
result = lint_candidate_file("data/candidate.json")
assert result.fail == 0

# Generate PDF
pdf = generate_pdf_file(
    "data/candidate.json",
    output_path="output/resume.pdf",
    locale="en",
    density="compact",
)
assert pdf.build_status == "success"

# ATS check
exit_code = check_pdf_file("output/resume.pdf")
assert exit_code == 0
```

### Object-first usage

For callers who already have candidate data in memory, the API also accepts
`Candidate` dataclass objects directly:

```python
from hirepaper.api import generate_pdf, lint_candidate_data, match_candidate
from hirepaper.models import Candidate, Personal, Phone, Experience

candidate = Candidate(
    personal=Personal(
        name="Jane Doe",
        email="jane@example.com",
        phone=Phone(value="+1 555 123 4567", hyperlink="tel:+15551234567"),
        location="Austin, TX",
        headline="Senior Software Engineer",
    ),
    summary="Backend engineer focused on Python and APIs.",
    experience=[
        Experience(
            company="Example Corp",
            position="Senior Software Engineer",
            location="Austin, TX",
            start_date="2022-01",
            end_date=None,
            current=True,
            highlights=["Led API modernization."],
        )
    ],
)

result = generate_pdf(candidate, output_path="output/resume.pdf", locale="en")
```

See [docs/library.md](docs/library.md) for the full API reference.

---

## Development

```bash
# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run from source (without installing)
./hirepaper-dev --help

# Build packaged binary
.venv/bin/python build.py
```

## Documentation

- [project.md](project.md) — architecture, layout, density, packaging
- [docs/library.md](docs/library.md) — full library API reference
- [docs/content.md](docs/content.md) — `content` command reference
- [docs/pdf.md](docs/pdf.md) — `pdf` command reference
- [docs/content-match.md](docs/content-match.md) — `content match` detailed usage
- [docs/content-tailor.md](docs/content-tailor.md) — `content tailor` detailed usage
- [docs/file-map.md](docs/file-map.md) — source layout and important paths
- [agents.md](agents.md) — agent execution rules
- [sdd/backlog/](sdd/backlog/) — planned tasks
- [sdd/history/](sdd/history/) — completed task records

## Support

`hirepaper` is maintained as an independent project.

If it is useful to you, you can support ongoing development and maintenance via
GitHub Sponsors:

- [Sponsor on GitHub](https://github.com/sponsors/Lucas-Palomo)
