# 030 - Add `content init` command for example candidate bootstrap

**Date:** 2026-06-08
**Agent:** opencode (deepseek-v4-flash)

---

## Context

The project already had:
- a canonical candidate data model and loader;
- `content lint` for validating candidate JSON quality;
- a bundled candidate JSON Schema at `assets/schemas/candidate.schema.json`;
- example candidate fixtures under `data/`;
- a top-level `init` command for bootstrapping `config.toml`.

What was missing was an explicit onboarding path for candidate content itself. Users had to discover the example fixture manually, copy it by hand, and infer which file should become their working `candidate.json`.

## Changes Made

### 1. Canonical bundled example candidate asset

Created `assets/examples/candidate.example.json` as the single canonical runtime template for candidate bootstrap. The content mirrors `data/example.json`, which remains as a development fixture.

### 2. Resource helper

Added `example_candidate_path()` to `src/curriculum_gen/_resources.py`, following the existing pattern of `config_template_path()` and other resource helpers. It resolves the path to `assets/examples/candidate.example.json` in both source execution (via `sys._MEIPASS`) and packaged binary execution.

### 3. `content init` command

Added `curriculum-gen content init` as a subcommand of the `content` group in `src/curriculum_gen/cli.py`, closely following the pattern of the existing top-level `init` command:

- Default output: `./candidate.json`
- `--output <path>`: custom output path
- `--force`: overwrite existing file
- Refuses to overwrite without `--force`, with a clear error message suggesting the options
- Creates parent directories when needed
- On success, prints the destination path and guidance to use `content lint`

### 4. Documentation

- `project.md`: added `content init` to CLI structure, source layout, and command descriptions
- `agents.md`: added `content init` and `content lint` to the typical commands in the workflow section

## Decisions & Tradeoffs

- The canonical template lives at `assets/examples/candidate.example.json` rather than keeping only `data/example.json` as the development fixture, ensuring the packaged binary can access it via `sys._MEIPASS`.
- The bundled template is a copy of the existing `data/example.json` starter fixture. If the two diverge in the future, `data/example.json` should be consolidated to point to the canonical `assets/examples/` path.
- Placeholder detection warnings from `content lint` are expected and acceptable for a starter template file.

## Verification

```bash
# Source execution
./curriculum-gen-dev content init --output /tmp/curriculum-gen-candidate-init.json
./curriculum-gen-dev content lint /tmp/curriculum-gen-candidate-init.json

# Refuse overwrite
./curriculum-gen-dev content init --output /tmp/curriculum-gen-candidate-init.json
# → Error: candidate file already exists

# Force overwrite
./curriculum-gen-dev content init --output /tmp/curriculum-gen-candidate-init.json --force

# Build packaged binary
.venv/bin/python build.py

# Packaged execution
./curriculum-gen content init --output /tmp/curriculum-gen-candidate-init-packaged.json
./curriculum-gen content lint /tmp/curriculum-gen-candidate-init-packaged.json
```

All commands succeeded:
1. First `content init` created the file successfully
2. `content lint` confirmed the bootstrapped JSON is structurally valid (placeholder warnings expected)
3. Second `content init` failed with the expected file-exists error
4. `--force` overwrote the file successfully
5. Packaged binary also creates a valid starter candidate file

## Residual Risks

- `data/example.json` and `assets/examples/candidate.example.json` are currently duplicates. A future task should consolidate them so `data/example.json` is symlinked or removed in favor of the canonical bundled path.
