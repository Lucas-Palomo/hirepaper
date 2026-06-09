# 025 - Migrate LLM config to TOML with command-specific profiles

**Date:** 2026-06-05
**Agent:** Codex GPT-5

---

## Context

The previous configuration work still communicated the wrong UX:

- `--config` looked mandatory
- JSON was still treated as a supported format
- the repository shipped config files that blurred the difference between a
  local override and an example
- environment-variable-only execution was not supported cleanly

The intended model is simpler:

- environment variables are the base configuration
- `./config.toml` is an optional local override by convention
- `--config <path>` is an optional explicit TOML override
- `content match` and `content tailor` still get command-specific operational
  fallbacks when timeout/token settings are not provided

## Changes

### Modified: `src/curriculum_gen/llm/config.py`

- Removed JSON config support entirely.
- Reworked the loader into an env-first, TOML-override resolver.
- Added default `config.toml` discovery when no `--config` path is provided.
- Added environment-variable support for all base fields:
  - `LLM_BASE_URL`
  - `LLM_API_KEY`
  - `LLM_MODEL`
  - `LLM_TEMPERATURE`
  - `LLM_TIMEOUT_SECONDS`
  - `LLM_MAX_TOKENS`
- Added command-profile environment variables:
  - `LLM_CONTENT_MATCH_TIMEOUT_SECONDS`
  - `LLM_CONTENT_MATCH_MAX_TOKENS`
  - `LLM_CONTENT_TAILOR_TIMEOUT_SECONDS`
  - `LLM_CONTENT_TAILOR_MAX_TOKENS`
- Kept TOML command profiles:
  - `[llm.content_match]`
  - `[llm.content_tailor]`
- Made TOML values override environment values.

### Modified: `src/curriculum_gen/cli.py`

- Removed `--config` as a mandatory requirement from:
  - `content match`
  - `content tailor`
  - `llm health`
  - `llm usage`
- This intentionally supersedes the earlier JSON-only, `--config`-required
  policy introduced in tasks 020 and 021.
- Updated help text to explain the actual behavior:
  - use `./config.toml` when present
  - otherwise resolve from environment variables
  - `--config` is an optional TOML override

### Modified: `src/curriculum_gen/content_match.py`

- Updated command logging metadata so the synthetic command string only includes
  `--config` when a real config path was used.
- Kept per-run `--timeout-seconds` / `--max-tokens` overrides layered on top of
  the resolved config.

### Added: `config_example.toml`

- Added the canonical repository example config file.
- Documented supported environment variables and precedence inside the file.
- Positioned the file as a template to copy to `config.toml` when a local
  override is desired.
- The documented environment namespace uses the shorter `LLM_*` prefix.

### Removed: `config.toml` and `config.json`

- Removed tracked config files that were communicating the wrong contract and
  could be mistaken for supported checked-in runtime configuration.

### Modified: `project.md`

- Updated runtime command examples so `--config` is optional.
- Documented the env-first, TOML-override resolution model.
- Replaced references to repository `config.toml` with `config_example.toml`.

### Modified: `agents.md`

- Added an explicit LLM config policy section so future work does not regress
  the env-first behavior.

### Modified: `pyproject.toml` and `requirements.txt`

- Kept conditional `tomli` support for Python versions below 3.11.

## Decisions and Tradeoffs

- **No JSON compatibility:** the project has not launched, so carrying a second
  config format only adds ambiguity and maintenance cost. TOML is now the only
  supported file format.
- **Env-first resolution:** this reduces friction for local/CI usage and makes
  secrets straightforward without forcing a file to exist.
- **TOML as override, not requirement:** `config.toml` is now a convenience
  layer rather than a mandatory prerequisite.
- **Example file, not live file:** `config_example.toml` is clearer than
  checking in a real `config.toml` because it distinguishes documentation from
  runtime state.
- **Keep command fallbacks:** `content match` and `content tailor` still need
  stronger operational limits than lightweight global defaults, so their
  fallbacks remain explicit in config resolution.

## Verification

```bash
PYTHONPATH=src python -m py_compile \
  src/curriculum_gen/llm/config.py \
  src/curriculum_gen/cli.py \
  src/curriculum_gen/content_match.py

LLM_BASE_URL=http://localhost:4000/v1 \
LLM_API_KEY=test-key \
LLM_MODEL=gpt-4 \
PYTHONPATH=src python - <<'PY'
from curriculum_gen.llm.config import load_config

for profile in (None, "content_match", "content_tailor"):
    cfg = load_config(profile=profile)
    print(profile, cfg.source_format, cfg.timeout_seconds, cfg.max_tokens, cfg.model)
PY

LLM_BASE_URL=http://localhost:4000/v1 \
LLM_API_KEY=test-key \
LLM_MODEL=gpt-4 \
LLM_TIMEOUT_SECONDS=45 \
LLM_MAX_TOKENS=700 \
PYTHONPATH=src python - <<'PY'
from curriculum_gen.llm.config import load_config
cfg = load_config(profile="content_match")
print(cfg.timeout_seconds, cfg.max_tokens)
PY

LLM_BASE_URL=http://localhost:4000/v1 \
LLM_API_KEY=test-key \
LLM_MODEL=gpt-4 \
PYTHONPATH=src python - <<'PY'
from curriculum_gen.llm.config import load_config
cfg = load_config("config_example.toml", profile="content_match")
print(cfg.source_format, cfg.config_path, cfg.timeout_seconds, cfg.max_tokens)
PY

./curriculum-gen-dev content match --help
./curriculum-gen-dev content tailor --help
./curriculum-gen-dev llm health --help
./curriculum-gen-dev llm usage --help

.venv/bin/python build.py

./curriculum-gen content match --help
./curriculum-gen content tailor --help
./curriculum-gen llm health --help
```

Observed results:

- env-only configuration resolves successfully without any `config.toml`
- the shorter `LLM_*` environment namespace works as the primary contract
- `content_match` and `content_tailor` still resolve to `300` / `16384` when
  no timeout/token settings are provided
- global environment defaults such as `45` / `700` are respected when set
- `config_example.toml` loads as a TOML override successfully
- source and packaged CLI help both expose the optional `--config` contract
- build completed successfully

## Residual Risks

- No real networked LLM call was executed in this task, so verification covered
  loader behavior, CLI exposure, packaging, and local resolution logic only.
- `content match` currently still logs a synthetic command string rather than a
  shell-escaped exact invocation; that predates this task.
