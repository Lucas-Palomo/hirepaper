# Project Context

## Overview
`hirepaper` is a Python library and CLI that generates ATS-safe resume PDFs from structured JSON.

The pipeline is:

```text
candidate JSON -> Python data model -> LaTeX template/class -> LuaLaTeX PDF -> pdf check
```

Architecture:

```
public API (hirepaper.api)  →  shared workflow services  →  formatters / renderers / file I/O
CLI commands (hirepaper.cli) →  thin adapter over public API
```

The project is no longer a blank slate. Treat the current schema, templates,
CLI, validation, and packaging flow as the baseline unless a backlog task
explicitly changes them.

## Runtime Commands

Root entry points:

- `./hirepaper-dev`: development entry point that runs from source via `PYTHONPATH=src`.
- `./hirepaper`: packaged entry point that delegates to `dist/hirepaper`.

CLI structure:

```bash
hirepaper init [--output <path>] [--force]
hirepaper doctor
hirepaper help
hirepaper content init [--output <path>] [--force]
hirepaper content help
hirepaper content lint <candidate_json>
hirepaper content match <candidate.json> <vacancy.txt> [--config <config.toml>]
hirepaper content tailor <candidate.json> <vacancy.txt> --output <tailored.json> [options]
hirepaper pdf help
hirepaper llm health [--config <config.toml>]
hirepaper llm usage [--config <config.toml>]
hirepaper llm help
hirepaper linkedin help
hirepaper linkedin generate <candidate.json> --output <report> --format txt|json [options]
hirepaper pdf generate <candidate_json> --output <pdf> [--log <archive.zip>]
hirepaper pdf check <pdf>
```

Build command:

```bash
.venv/bin/python build.py
```

The packaged binary bundles Python code plus project resources such as templates,
assets, and locale files. It still depends on host tools for PDF generation and
inspection.

LLM configuration is resolved with this precedence:
- CLI flag override such as `--timeout-seconds` / `--max-tokens`
- `--config <path>` TOML file, or `./config.toml` when present
- environment variables
- command fallback for `content match` / `content tailor`
- built-in global defaults

Supported environment variables:
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_TEMPERATURE`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_TOKENS`
- `LLM_CONTENT_MATCH_TIMEOUT_SECONDS`
- `LLM_CONTENT_MATCH_MAX_TOKENS`
- `LLM_CONTENT_TAILOR_TIMEOUT_SECONDS`
- `LLM_CONTENT_TAILOR_MAX_TOKENS`
- `LLM_LINKEDIN_GENERATE_TIMEOUT_SECONDS`
- `LLM_LINKEDIN_GENERATE_MAX_TOKENS`

LuaLaTeX execution is isolated with per-run temporary cache directories for font
and TeX cache state. The CLI sets temporary values for:
- `XDG_CACHE_HOME`
- `TEXMFVAR`
- `TEXMFCACHE`

External host dependencies:
- `lualatex`
- `luaotfload`
- `rsvg-convert`
- `pdftotext`
- `pdffonts`
- `exiftool`

`doctor` must remain the canonical environment check.

## Layouts
The current official layout is:

- `standard` — default and canonical layout (Main Flow + Utility Bands).

The CLI still exposes `--layout`, but only `standard` is currently supported.
The flag remains reserved for future layout expansion.

All layouts must remain ATS-safe:
- visible text must be extractable with `pdftotext`;
- fonts must expose Unicode mappings;
- no Type 3 fonts;
- icons must be decorative only and must not pollute extracted text;
- URLs must remain visible in extracted text;
- reading order should remain sensible.

When changing layout behavior, verify both visual output and extracted text.

## Density Policy
The supported densities are:

- `compact`: prioritizes essential resume content, hides lower-value optional sections.
- `full`: preserves more optional content while staying ATS-safe.

Density rules belong in `src/hirepaper/density.py`.

## PDF Generation
LuaLaTeX is the only supported PDF engine. The CLI runs it with temporary
writable cache directories. Generation must not report success for a broken
artifact.

## ATS Validation
`hirepaper pdf check` validates PDFs using:
- metadata via `exiftool`;
- text extraction via `pdftotext`;
- font inspection via `pdffonts`;
- required section, contact, URL, keyword, and placeholder checks.

## Packaging
The project uses `build.py` to build a one-file PyInstaller executable at:

```text
dist/hirepaper
```

After tasks that touch runtime code, templates, assets, locale behavior,
generation, validation, or packaging, rebuild the binary and smoke-test
`./hirepaper`.

## Source Layout

- `src/hirepaper/api.py`: Public library API with typed request/response dataclasses and importable workflow functions.
- `src/hirepaper/cli.py`: Thin CLI adapter over the API layer. Parses arguments, renders terminal output, maps exceptions to exit codes.

## Documentation Flow
Use `sdd/backlog/` for planned work and `sdd/history/` for completed work.
Backlog files define intent. History files record what actually changed, what
was decided, and how it was verified.

Do not leave stale agent instructions in multiple places. [agents.md](agents.md) is the
root instruction file for future agents. See [docs/file-map.md](docs/file-map.md) for the
project source layout and important paths.
