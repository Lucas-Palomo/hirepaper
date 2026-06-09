# 040 — Add `linkedin` command group and `linkedin generate` report workflow

**Date:** 2026-06-09

**Context:** The project needed a dedicated LinkedIn command group to generate LinkedIn-focused profile reports from canonical candidate JSON, distinct from the `content tailor` pipeline.

## Changes Made

### New files
- `src/hirepaper/linkedin_generate.py` — LinkedIn report generation orchestration module following `content_tailor.py` patterns:
  - Candidate loading and lint gating
  - Prompt loading (built-in default or `--prompt` override)
  - Repeatable `--extra-context` support
  - Structured payload construction for the LLM
  - Schema validation against `linkedin-report.schema.json`
  - Text (human-readable) and JSON output rendering
  - Optional `--log` archive with StagedLogArchive
  - Spinner feedback during LLM call
- `assets/schemas/linkedin-report.schema.json` — JSON Schema for LinkedIn report validation (disclaimer, profile_focus, headline, about, top_skills, experience_highlights, project_highlights, keywords, cautions, grounding_notes)

### Modified files
- `src/hirepaper/cli.py`:
  - Added `linkedin_app` Typer group with `help` and `generate` subcommands
  - Implemented `_cmd_linkedin_generate` with destination preflight, lint gating, LLM orchestration
- `src/hirepaper/llm/config.py`:
  - Added `linkedin_generate` to `_KNOWN_COMMAND_PROFILES`
  - Added `linkedin_generate` fallback config (300s timeout, 60000 tokens)
  - Added `_profile_env_prefix` support for `LLM_LINKEDIN_GENERATE_*` env vars
- `assets/examples/config.example.toml`:
  - Added `[llm.linkedin_generate]` profile section
  - Updated comments to reference `linkedin generate` and its env vars
- `docs/file-map.md`:
  - Added `linkedin generate` to CLI command listing
  - Added `linkedin_generate.py` to source layout
  - Updated prompts dir description
- `project.md`:
  - Added `linkedin` commands to CLI listing
  - Added `LLM_CONTENT_LINKEDIN_*` env vars
- `README.md`:
  - Added `linkedin generate` to command table

### Existing assets reused
- `assets/prompts/linkedin-generate-default.txt` — already existed, used as default prompt

## Design Decisions

1. **Separate module, not embedded in content_tailor**: LinkedIn output is a report, not a candidate JSON. Keeping it in its own module (`linkedin_generate.py`) maintains clear separation of artifact contracts.

2. **Single LLM call (no plan/rewrite split)**: Unlike `content tailor`, LinkedIn generation is a single-stage process — the model produces the full report in one response. No structural actions or iterative rewriting is needed.

3. **Schema validation copied (not imported) from content_tailor**: The `_validate_against_schema`, `_resolve_schema_ref`, etc. functions are duplicated rather than shared to avoid coupling between the two modules. If validation logic needs to be unified later, it can be extracted into a shared utility.

4. **Profile `linkedin_generate` in LLM config**: Uses the same config resolution pattern as `content_match` and `content_tailor`, with its own TOML section and env var prefix.

## Verification

```bash
# Source entry point
./hirepaper-dev linkedin --help       # shows help with generate subcommand
./hirepaper-dev linkedin help         # same help surface
./hirepaper-dev linkedin generate data/candidate.json --output /tmp/test.txt --format html  # rejected: bad format
./hirepaper-dev linkedin generate data/candidate.json --output /tmp/test.txt                 # rejected: missing --format
./hirepaper-dev linkedin generate data/candidate.json --format txt                           # rejected: missing --output
./hirepaper-dev linkedin generate data/nonexistent.json --output /tmp/test.txt --format txt  # rejected: missing candidate

# Packaged binary
.venv/bin/python build.py
./hirepaper linkedin --help           # same help surface
./hirepaper linkedin help             # same help surface
./hirepaper linkedin generate data/candidate.json --output /tmp/test.txt --format html  # rejected: bad format
./hirepaper linkedin generate data/nonexistent.json --output /tmp/test.txt --format txt # rejected: missing candidate
```

## Residual Risks

- The `linkedin generate` command requires an LLM with a working configuration (env vars or config.toml). Without it, the command fails at LLM config resolution, which is expected behavior.
- The full LLM-based generation path (with real model) was not tested in this session because no LLM endpoint is configured in the development environment.
- The initial prompt and schema may need refinement after real-world usage.
