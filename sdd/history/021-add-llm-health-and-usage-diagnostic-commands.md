# 021 - Add `llm health` and `llm usage` diagnostic commands

**Date:** 2026-06-04
**Agent:** opencode (deepseek-v4-flash)

## Context
Task 020 introduced `content match` and `content tailor` as LLM-backed content commands, but there was no dedicated CLI surface for LLM infrastructure diagnostics. Operators had no way to check proxy reachability or inspect token usage without invoking a content-domain command. Task 021 introduces a top-level `llm` command group for operational checks.

## Changes Made

### New top-level group: `src/curriculum_gen/cli.py`
- Added `llm_app` Typer group registered as `llm` at the top level.
- `llm health --config <json>` — performs a minimal completion request to infer proxy/LLM health. Reports `HEALTHY` or `UNHEALTHY` with check details.
- `llm usage --config <json>` — sends a diagnostic request and reports `prompt_tokens`, `completion_tokens`, and `total_tokens`.
- Both commands follow the same `--config` policy from task 020 (mandatory, explicit, no env fallback).
- Both support `--verbose` / `-v` with the same three-level scheme.
- All `llm` imports are lazy (inside `_run_llm_health()` and `_run_llm_usage()`), keeping help and non-LLM commands free of LiteLLM startup noise.

### Extended: `src/curriculum_gen/llm/client.py`
- Refactored internal helpers: `_setup_verbose()` for debug logging, `_complete()` for the shared LiteLLM completion call, `_extract_text()` and `_extract_usage()` for response parsing.
- `_print_curl()` now accepts a `messages` parameter to support different prompts per command.
- Added `check_health(config, verbose)` — uses a diagnostic prompt (`You are a diagnostic assistant for curriculum-gen.` / `Reply with a short confirmation.`). Returns the response text; raises `LLMClientError` on failure.
- Added `get_usage(config, verbose)` — same diagnostic request, extracts usage block via `_extract_usage()` (tries attribute access `.usage.prompt_tokens` first, falls back to dict access). Returns `dict[str, int]` with `prompt_tokens`, `completion_tokens`, `total_tokens`.
- `send_hello()` refactored to use shared helpers — behavior unchanged.
- `_extract_usage()` now returns ALL usage fields dynamically via `_obj_to_dict()` (recursively converts nested objects), instead of only three hardcoded fields.
- Added `litellm.suppress_debug_info = True` and `litellm.set_verbose = False` in `_complete()` to suppress LiteLLM's "Give Feedback" banner on request failures — keeps runtime output clean.
- Added `_StderrFilter` plus `_filtered_stderr()` context manager to suppress LiteLLM auxiliary stderr noise during diagnostic execution.
- Expanded stderr filtering to cover the entire diagnostic flow (`send_hello()`, `check_health()`, `get_usage()`), not just the raw completion call.
- Filtered the residual `Failed to fetch remote model cost map ...` warning so offline diagnostic failures still present the CLI's own normalized error output as the primary result.

### Updated: `src/curriculum_gen/cli.py`
- `_run_llm_health()` — output reworked: header states `Method: minimal completion request (no dedicated proxy health endpoint)`, success is `[OK] Completion request succeeded — inferred health: HEALTHY`, failure is `[FAIL] Completion request failed — inferred health: UNHEALTHY`. Every output line makes the inference explicit.
- `_run_llm_usage()` — now renders all usage fields dynamically via `_print_usage()`, handling nested dicts with indentation.

### Updated: `project.md`
- CLI structure block now includes `llm health --config <json>` and `llm usage --config <json>`.
- Source layout section documents both commands as LLM infrastructure diagnostics.

## Decisions and Tradeoffs
- **Fallback health approach**: Uses a minimal completion request instead of a dedicated proxy health endpoint. The latter is not portable across LiteLLM deployments. The output explicitly states what was checked (`Health inferred from minimal completion request (no dedicated proxy health endpoint)` / `[OK] Minimal completion request succeeded`).
- **Shared diagnostic prompt**: Both `check_health()` and `get_usage()` use the same lightweight prompt (`You are a diagnostic assistant...` / `Reply with a short confirmation.`), keeping token costs low and responses deterministic.
- **Refactored client internals**: `_complete()`, `_extract_text()`, `_extract_usage()` extracted as shared helpers. `send_hello()` now delegates to these, reducing duplication.
- **Response handling discipline**: Attribute access (`.usage.prompt_tokens`) is tried first before dict access, matching the AC requirement to not assume plain `dict`.
- **Runtime output discipline**: Combines `litellm.suppress_debug_info = True` with stderr filtering around the full diagnostic execution path to prevent LiteLLM banners and `model cost map` warnings from polluting normal CLI error output.
- **Richer usage output**: `_extract_usage()` returns all usage fields from the response via `_obj_to_dict()`, and `_print_usage()` renders them recursively with indentation for nested objects (e.g., `Prompt Tokens Details` / `Completion Tokens Details`).

## Acceptance Criteria Status
| # | Criterion | Status |
|---|-----------|--------|
| 1 | New top-level `llm` command group exists | ✅ |
| 2 | `curriculum-gen llm health --config <json>` exists | ✅ |
| 3 | `curriculum-gen llm usage --config <json>` exists | ✅ |
| 4 | Both commands require `--config` and fail clearly without it | ✅ |
| 5 | Both reuse explicit JSON config policy from task 020 | ✅ |
| 6 | `llm health` reports clear healthy/unhealthy result | ✅ |
| 7 | `llm usage` reports token usage for a diagnostic request | ✅ |
| 8 | `llm usage` prints prompt, completion, and total tokens | ✅ |
| 9 | Both fail clearly when config loading fails | ✅ |
| 10 | Both fail clearly when request fails | ✅ |
| 11 | `llm usage` fails clearly if no usable usage info | ✅ (via `_extract_usage`) |
| 12 | Implementation does not assume LiteLLM responses are raw `dict` | ✅ |
| 13 | Help output does not emit LiteLLM startup warnings | ✅ |
| 14 | Health output states explicitly that health was inferred from request success | ✅ |
| 15 | Runtime failures do not dump unrelated LiteLLM banners around CLI error output | ✅ |
| 16 | `project.md` reflects new `llm` group | ✅ |

## Verification

### Help surface (all pass, no LiteLLM noise)
```
$ ./curriculum-gen-dev --help             → shows llm group
$ ./curriculum-gen-dev llm --help         → shows health, usage
$ ./curriculum-gen-dev llm health --help  → --config + --verbose shown
$ ./curriculum-gen-dev llm usage --help   → --config + --verbose shown
```

### Missing --config (all pass, exit 1)
```
$ ./curriculum-gen-dev llm health    → Error: --config is required for 'llm health'
$ ./curriculum-gen-dev llm usage     → Error: --config is required for 'llm usage'
```

### Missing/invalid config file (all pass, exit 1)
```
$ ./curriculum-gen-dev llm health --config /tmp/missing.json
  → Error: config file not found: /tmp/missing.json
$ printf '{bad json' > /tmp/bad-config.json
$ ./curriculum-gen-dev llm health --config /tmp/bad-config.json
  → Error: invalid config JSON: ...
```

### Request failure with valid config (pass, exit 1 — no proxy running)
```
$ printf '{"base_url":"http://localhost:4000/v1","api_key":"test","model":"gpt-4","timeout_seconds":3}' > /tmp/v.json
$ ./curriculum-gen-dev llm health --config /tmp/v.json
  → LLM health check
    Model: gpt-4
    Endpoint: http://localhost:4000/v1
    Method: minimal completion request (no dedicated proxy health endpoint)
    [FAIL] Completion request failed — inferred health: UNHEALTHY
    Error: LLM request failed: ...
$ ./curriculum-gen-dev llm usage --config /tmp/v.json
  → LLM usage diagnostic
    Model: gpt-4
    Endpoint: http://localhost:4000/v1
    Error: LLM request failed: ...
```

### Runtime output normalization (pass)
```
$ ./curriculum-gen-dev llm health --config /tmp/v.json
  → no LiteLLM "Give Feedback" banner
  → no LiteLLM "Failed to fetch remote model cost map" warning
  → CLI-owned error output remains primary
$ ./curriculum-gen-dev llm usage --config /tmp/v.json
  → no LiteLLM "Give Feedback" banner
  → no LiteLLM "Failed to fetch remote model cost map" warning
  → CLI-owned error output remains primary
```

### Verbose level 1 (pass — curl shown in output)
```
$ ./curriculum-gen-dev llm health --config /tmp/v.json -v
  → LLM health check + curl command with masked key
```

### Existing commands unaffected
- `./curriculum-gen-dev --help` — all groups shown
- `./curriculum-gen-dev content match --help` — works
- `./curriculum-gen-dev content lint --help` — works

## Residual Risks
- Health check uses a completion request fallback, not a dedicated proxy health endpoint. If the model responds but the proxy has degraded upstream connectivity, the result may be misleadingly healthy.
- Both commands require a running LiteLLM Proxy to fully verify the success path (token reporting, healthy exit code).
- `_extract_usage()` assumes the usage block structure matches OpenAI's standard (`prompt_tokens`, `completion_tokens`, `total_tokens`). Non-standard proxies may fail with "no usable usage information".
- The stderr filter currently targets known LiteLLM noise patterns observed in this environment. Future LiteLLM versions could emit different auxiliary warnings that would need to be added explicitly if they start polluting normal CLI output.

## Follow-up Items
- Rebuild packaged binary (`python3 build.py`) when environment permits.
- Validate `llm health` and `llm usage` success paths against a running LiteLLM Proxy.
- Consider adding a dedicated proxy health endpoint check if LiteLLM Proxy exposes one consistently.
