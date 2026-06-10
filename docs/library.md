# hirepaper as an Importable Library

`hirepaper` provides a stable public API under `hirepaper.api` for embedding
PDF generation, content analysis, and LinkedIn report workflows in Python
applications without depending on the CLI layer.

## Install

From the repository root:

```bash
pip install -e .
```

This installs the importable package as `hirepaper`.

For local development without installation, use the same module path strategy
as `./hirepaper-dev`:

```bash
PYTHONPATH=src python3 your_script.py
```

## Public API

The supported import surface is `hirepaper.api`:

```python
from hirepaper.api import (
    generate_pdf,
    generate_pdf_file,
    check_pdf_file,
    lint_candidate_data,
    lint_candidate_file,
    match_candidate,
    match_candidate_file,
    tailor_candidate,
    tailor_candidate_file,
    generate_linkedin_report,
    generate_linkedin_report_file,
    bootstrap_candidate_file,
    bootstrap_config_file,
)
```

## PDF Generation

### Object-first

```python
from hirepaper.api import generate_pdf, PDFGenerateResult
from hirepaper.models import Candidate

result: PDFGenerateResult = generate_pdf(
    candidate,
    output_path="output/resume.pdf",
    locale="en",
    density="compact",
    layout="standard",
    log=None,             # optional ZIP archive path
)
print(result.build_status)               # "success" | "failed"
print(result.artifact_validation_status)  # "passed" | "failed" | "not_run"
```

### File-first

```python
from hirepaper.api import generate_pdf_file

result = generate_pdf_file(
    "data/candidate.json",
    output_path="output/resume.pdf",
    locale="en",
    density="compact",
)
```

Raises `PDFGenerateError` on invalid input, missing locale, unknown density,
or build failure.

## Content Lint

### Object-first

```python
from hirepaper.api import lint_candidate_data

result = lint_candidate_data(candidate)
print(result.ok, result.warn, result.fail)   # counts
print(result.messages)                        # human-readable lines
```

### File-first

```python
result = lint_candidate_file("data/candidate.json")
```

## Content Match

### Object-first (returns structured report dict)

```python
from hirepaper.api import match_candidate
from hirepaper.llm.config import load_config

cfg = load_config("config.toml", profile="content_match")
report = match_candidate(
    candidate,
    vacancy_text,
    config=cfg,
    locale="en",
    strict=False,
    inference="medium",
)
print(report["score"])       # 0-100
print(report["rating"])      # "strong" | "good" | "partial" | "weak" | "poor"
```

### File-first (returns formatted report string + validated data + meta)

```python
report_str, validated, meta = match_candidate_file(
    "data/candidate.json",
    "data/vacancy.txt",
    locale="en",
    format="text",           # "text" | "md" | "json"
    output="output/match.txt",
)
print(report_str)
```

## Content Tailor

### Object-first (returns structured result with tailored candidate + report)

```python
from hirepaper.api import tailor_candidate

result = tailor_candidate(
    candidate,
    vacancy_text,
    config=cfg,
    mode="conservative",
    inference="medium",
    locale="en",
)
tailored = result["tailored_candidate"]
report = result["report_data"]
```

### File-first

```python
report_str, report_data, meta = tailor_candidate_file(
    "data/candidate.json",
    "data/vacancy.txt",
    output="output/tailored.json",
    report_output="output/report.txt",
    report_format="text",
)
```

## LinkedIn Generate

### Object-first (returns structured report dict)

```python
from hirepaper.api import generate_linkedin_report

report = generate_linkedin_report(
    candidate,
    config=cfg,
    locale="en",
)
print(report["profile_focus"])
print(report["headline"])
```

### File-first

```python
report_str, report_data, meta = generate_linkedin_report_file(
    "data/candidate.json",
    output="output/linkedin-report.txt",
    format="txt",             # "txt" | "md" | "json"
)
```

## Bootstrap Helpers

```python
from hirepaper.api import bootstrap_candidate_file, bootstrap_config_file

path = bootstrap_candidate_file("my-candidate.json", force=False)
path = bootstrap_config_file("config.toml", force=True)
```

Raises `FileExistsError` when the destination exists and `force=False`.

## PDF Check

```python
from hirepaper.api import check_pdf_file

exit_code = check_pdf_file("output/resume.pdf")
```

Returns `0` on pass (or pass with warnings), `1` on failure.

## Creating Candidate Objects Directly

You can also construct the dataclasses yourself instead of loading JSON.

```python
from hirepaper.models import Candidate, Experience, Personal, Phone

candidate = Candidate(
    personal=Personal(
        name="Jane Doe",
        email="jane@example.com",
        phone=Phone(value="+1 555 123 4567", hyperlink="tel:+15551234567"),
        location="Austin, TX",
        headline="Senior Software Engineer",
    ),
    summary="Backend engineer focused on Python, APIs, and platform reliability.",
    experience=[
        Experience(
            company="Example Corp",
            position="Senior Software Engineer",
            location="Austin, TX",
            start_date="2022-01",
            end_date=None,
            current=True,
            highlights=["Led API modernization and reduced latency in critical flows."],
        )
    ],
)
```

## End-to-End Example

The following example generates a PDF entirely through the library API,
without shelling out to `hirepaper`:

```python
from hirepaper.api import generate_pdf_file, lint_candidate_file, check_pdf_file

lint_result = lint_candidate_file("data/candidate.json")
assert lint_result.fail == 0, "candidate data failed lint"

pdf_result = generate_pdf_file(
    "data/candidate.json",
    output_path="output/end-to-end.pdf",
    locale="en",
    density="compact",
)
assert pdf_result.build_status == "success", "PDF generation failed"

exit_code = check_pdf_file("output/end-to-end.pdf")
assert exit_code == 0, "PDF ATS check failed"
```

## External Dependencies Still Matter

Even when using `hirepaper` as a library, some capabilities still rely on host
binaries:

- `lualatex`
- `luaotfload`
- `rsvg-convert`
- `pdftotext`
- `pdffonts`
- `exiftool`

For environment diagnostics, `hirepaper doctor` remains the canonical check.

## Architecture

```
public API (hirepaper.api)  →  shared workflow services  →  formatters / renderers / file I/O
CLI commands (hirepaper.cli) →  thin adapter over public API
```

The API layer owns all core orchestration. The CLI only parses arguments,
translates CLI options into typed API requests, renders human-readable output,
and converts exceptions into exit codes.
