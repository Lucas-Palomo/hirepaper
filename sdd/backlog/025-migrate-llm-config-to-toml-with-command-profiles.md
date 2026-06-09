# 025 - Migrate LLM config to TOML with command-specific profiles

## Status
Completed

## Context

The current LLM configuration flow is still shaped by the initial JSON-only
integration path. That creates two problems:

- `content match` and `content tailor` need larger operational limits than the
  lightweight global defaults, but the JSON config format does not make that
  distinction explicit.
- the project is likely to benefit from explicit environment-variable-backed
  secrets in the near future, and JSON is not a good long-term format for that
  configuration model.

The result is confusing UX: the config appears global, while some commands have
different runtime behavior.

## Goal

Introduce an env-first, TOML-override configuration model for LLM commands with
explicit command-specific sections.

## Scope

This task may update:

- `src/curriculum_gen/llm/config.py`
- `src/curriculum_gen/cli.py`
- `project.md`
- example config files in the repository root
- `pyproject.toml`
- `requirements.txt`
- `sdd/history/`

This task may add:

- TOML example configs
- command-profile-aware config resolution
- explicit environment variable references for secrets

This task should not:

- keep `--config` mandatory when environment-only configuration is sufficient
- preserve JSON compatibility just for a format that has not shipped

## Target Format

Preferred repository example format:

```toml
[llm]
base_url = "http://localhost:4000/v1"
model = "openai/gpt-4.1"
# api_key = "optional when CURRICULUM_GEN_LLM_API_KEY is set"

[llm.defaults]
temperature = 0.2
timeout_seconds = 60
max_tokens = 256

[llm.content_match]
timeout_seconds = 300
max_tokens = 16384

[llm.content_tailor]
timeout_seconds = 300
max_tokens = 16384
```

## Resolution Rules

Required base fields after merge:

- `base_url`
- `api_key`
- `model`

Optional numeric fields:

- `temperature`
- `timeout_seconds`
- `max_tokens`

Resolution precedence:

1. CLI flag override
2. `--config <path>` TOML file, or `./config.toml` when present
3. environment variables
4. command-specific TOML profile / environment profile
5. TOML defaults section / global environment defaults
6. top-level TOML `llm` table where applicable
7. command fallback for `content match` / `content tailor`
8. existing global loader defaults

## Acceptance Criteria

1. `--config` accepts TOML files as an optional override.
2. When `--config` is omitted, the CLI loads `./config.toml` if it exists and
   otherwise resolves config from environment variables alone.
3. `content match` resolves timeout/token settings from a command-specific
   profile when present.
4. `content tailor` resolves timeout/token settings from a command-specific
   profile when present.
5. `llm health` and `llm usage` keep using the global/default config path.
6. Supported environment variables can fully configure the CLI without any TOML
   file.
7. `config_example.toml` exists as the canonical file example.
8. CLI help and project docs describe the env-first TOML-override model.
