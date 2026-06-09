# 020 - Add initial LiteLLM Proxy config and hello-world content commands

**Date:** 2026-06-04
**Agent:** opencode (deepseek-v4-flash)

## Context
The project had `content match` and `content tailor` as stub commands that simply printed "not yet implemented". Task 020 introduces the first LLM integration path using a LiteLLM Proxy-compatible endpoint configured exclusively through a JSON config file.

## Changes Made

### New package: `src/curriculum_gen/llm/`
- `__init__.py` — empty package marker.
- `config.py` — `LLMConfig` dataclass + `load_config()` function. Validates:
  - File existence and readability;
  - Valid JSON parsing;
  - Required fields: `base_url`, `api_key`, `model` (non-empty strings);
  - Optional fields: `temperature` (default 0.2), `timeout_seconds` (default 60), `max_tokens` (default 256);
  - Numeric type checks for optional numeric fields.
- `client.py` — `send_hello()` function using `litellm.completion` (imported lazily inside the function, not at module level). Sends a deterministic hello-world prompt (`system`: connectivity test assistant, `user`: short confirmation request). Returns the model response text. Handles both `ModelResponse` objects (via attribute access `.choices[0].message.content`) and plain dicts (via fallback). Wraps exceptions in `LLMClientError`.

### Updated: `src/curriculum_gen/cli.py`
- No module-level imports from the `llm` package — all LLM imports are deferred inside `_run_content_hello()` to avoid triggering LiteLLM initialization for non-LLM commands or help text.
- Shared helper `_run_content_hello(command_name, config_path)`:
  - Loads config (exits with error on failure);
  - Prints connectivity test header (command name, model, endpoint);
  - Calls `send_hello()` and prints response;
  - Exits with error on request/response failures.
- `content match` command: accepts optional `candidate` (Path) and `vacancy` (Path) positional arguments + `--config` option. Requires `--config` or fails with clear error.
- `content tailor` command: same signature and behavior.
- Both commands explicitly describe in help text that candidate/vacancy args are not yet used (connectivity-test-only phase).

### Updated: `pyproject.toml` and `requirements.txt`
- Added `litellm` as a runtime dependency.

### Updated: `project.md`
- CLI structure block now includes `content match` and `content tailor`.
- Source layout section updated to reflect the new commands with honest documentation that they are connectivity tests only.

### Verbosity levels: `src/curriculum_gen/llm/client.py` and `src/curriculum_gen/cli.py`
- `--verbose` / `-v` converted from boolean to multi-level count option (`-v`, `-vv`, `-vvv`).
- **Level 1** (`-v`): prints a curl command equivalent (with API key masked via `_mask_key()`) to stderr, then dumps the full API response as formatted JSON using `model_dump()`/`dict()`.
- **Level 2** (`-vv`): enables `litellm._turn_on_debug()` but suppresses `httpx`/`httpcore`/`openai` low-level loggers to reduce noise.
- **Level 3** (`-vvv`): full debug including HTTP transport traces.
- Added `_mask_key()` helper to avoid leaking full API keys in curl output.
- Added `_print_curl()` helper to render the equivalent curl command.
- Added `_dump_response()` helper to serialize the LiteLLM response object to JSON.

## Decisions and Tradeoffs
- **Preferred CLI shape**: Chose the future-oriented shape (`candidate` + `vacancy` positional args) even though they are not used yet. This preserves the public interface direction and avoids a breaking change later. Help text explicitly marks them as unused in this phase.
- **No environment variable fallback**: Strictly adheres to the product decision — only `--config` is accepted. No `OPENAI_API_KEY` or similar implicit discovery.
- **Minimal abstraction**: The `llm/` module is thin — `config.py` handles file I/O and validation, `client.py` wraps a single litellm call. Easy to replace when real match/tailor logic lands.
- **Lazy litellm import**: `from litellm import completion` is deferred inside `send_hello()` so that merely importing `client.py` does not trigger LiteLLM network initialization. The `cli.py` module also defers its `llm` imports inside `_run_content_hello()`, so top-level help, non-LLM commands, and `content --help` never touch LiteLLM at import time.
- **Response type robustness**: The `send_hello()` function tries attribute access (`response.choices[0].message.content`) first, then falls back to dict-like access. This accepts both LiteLLM's `ModelResponse` object and plain dict responses, matching AC #13.
- **PyInstaller compatibility**: The new `llm/` package is a sub-package of `curriculum_gen`, so it is automatically included in the PyInstaller build without spec changes. The `litellm` library is installed in the venv and will be bundled by PyInstaller's hook mechanism.
- **Three-level verbosity**: `--verbose` uses `count=True` to support `-v`, `-vv`, `-vvv`. Level 1 is intentionally lightweight (curl + full JSON response), level 2 adds LiteLLM internal debug without HTTP noise, and level 3 exposes raw HTTP traces. The API key is masked at level 1 to prevent credential leakage in debug output.

## Acceptance Criteria Status
| # | Criterion | Status |
|---|-----------|--------|
| 1 | `content match` exists as a public CLI command | ✅ |
| 2 | `content tailor` exists as a public CLI command | ✅ |
| 3 | Both commands require `--config=<json file>` | ✅ |
| 4 | Invoking without `--config` fails clearly and exits non-zero | ✅ |
| 5 | Invoking with missing config path fails clearly and exits non-zero | ✅ |
| 6 | Invoking with invalid JSON config fails and exits non-zero | ✅ |
| 7 | Invoking with missing required config fields fails and exits non-zero | ✅ |
| 8 | With valid config, each command sends a basic test prompt through LiteLLM | ✅ (verified via request error with valid config — proxy needed for full success) |
| 9 | With successful model response, each command prints returned text | ⚠️ (depends on running proxy, cannot fully verify offline) |
| 10 | Output does not falsely claim real matching/tailoring was performed | ✅ |
| 11 | Implementation does not depend on provider-specific environment variables | ✅ |
| 12 | Command help and project docs reflect temporary hello-world scope honestly | ✅ |
| 13 | LiteLLM success response accepted even when not a plain `dict` | ✅ (uses `.choices[0].message.content` attribute access) |
| 14 | `--help` does not emit LiteLLM startup warnings before showing help text | ✅ |

## Verification

### Help surface (all pass)
```
$ ./curriculum-gen-dev content --help         → match, tailor, lint listed
$ ./curriculum-gen-dev content match --help    → args + --config shown
$ ./curriculum-gen-dev content tailor --help   → args + --config shown
```

### Missing --config (all pass, exit 1)
```
$ ./curriculum-gen-dev content match           → Error: --config is required for 'content match'
$ ./curriculum-gen-dev content tailor          → Error: --config is required for 'content tailor'
```

### Missing config file (all pass, exit 1)
```
$ ./curriculum-gen-dev content match --config /tmp/missing.json
  → Error: config file not found: /tmp/missing.json
```

### Invalid JSON (pass, exit 1)
```
$ printf '{bad json' > /tmp/bad-config.json
$ ./curriculum-gen-dev content match --config /tmp/bad-config.json
  → Error: invalid config JSON: ...
```

### Missing required field (pass, exit 1)
```
$ printf '{"base_url":"...","api_key":"test"}' > /tmp/missing-field.json
$ ./curriculum-gen-dev content match --config /tmp/missing-field.json
  → Error: invalid config — missing required field(s): model
```

### Empty required field (pass, exit 1)
```
$ printf '{"base_url":"","api_key":"","model":""}' > /tmp/empty-fields.json
$ ./curriculum-gen-dev content match --config /tmp/empty-fields.json
  → Error: invalid config — required field 'model' must be a non-empty string
```

### Request failure with valid config (pass, exit 1 — expected, no proxy running)
```
$ printf '{"base_url":"http://localhost:4000/v1","api_key":"test-key","model":"gpt-4","temperature":0.2,"timeout_seconds":5,"max_tokens":64}' > /tmp/valid-config.json
$ ./curriculum-gen-dev content match --config /tmp/valid-config.json
  → LLM connectivity test: content match
    Model: gpt-4
    Endpoint: http://localhost:4000/v1
    Error: LLM request failed: ...
```

### Existing commands unaffected (pass)
- `./curriculum-gen-dev --help` — all groups shown
- `./curriculum-gen-dev content lint --help` — works

## Residual Risks
- Real vacancy-based matching/tailoring is deferred to a future task.
- The `LLMClientError` message includes the raw litellm exception text, which may expose internal details. Acceptable for this phase since the commands are developer/operator-facing connectivity tests.
- PyInstaller build was not re-run in this session due to environment restrictions, but the module structure is standard and should bundle correctly.

## Follow-up Items
- Rebuild packaged binary (`python3 build.py`) when environment permits.
- Implement real vacancy analysis once the LLM integration pattern is validated against a running LiteLLM Proxy.
