# 039 — Add consistent command descriptions to CLI help

**Date:** 2026-06-08
**Agent:** opencode (deepseek-v4-flash)

---

## Context
Several CLI commands appeared in help output without a visible description — `content lint`, `match`, `tailor`, `pdf generate`, `check`, `llm health`, `usage`, and all `help` aliases. This made the help surface less scannable than it should be for a published CLI.

## Changes
Added `help=` to every public command decorator in `src/hirepaper/cli.py`:

| Command | Help text |
|---|---|
| `help` (top-level) | Show this help message and exit. |
| `init` | Bootstrap a local config.toml from the bundled template. |
| `content help` | Show this help message and exit. |
| `content lint` | Validate candidate JSON structure and quality. |
| `content init` | Bootstrap a starter candidate JSON from the bundled example. |
| `content match` | Compare a candidate JSON against a vacancy with LLM analysis. |
| `content tailor` | Tailor a candidate JSON to a vacancy using LLM planning. |
| `pdf help` | Show this help message and exit. |
| `pdf generate` | Generate a PDF resume from a candidate JSON file. |
| `pdf check` | Validate a PDF for ATS safety and quality. |
| `llm help` | Show this help message and exit. |
| `llm health` | Check LLM connectivity with a minimal completion request. |
| `llm usage` | Show per-request token usage diagnostics. |

## Verification

```bash
./hirepaper-dev --help              # All top-level commands have descriptions
./hirepaper-dev content --help      # lint, init, match, tailor described
./hirepaper-dev pdf --help          # generate, check described
./hirepaper-dev llm --help          # health, usage described

.venv/bin/python build.py

./hirepaper --help                  # Same output in packaged binary
./hirepaper content --help
./hirepaper pdf --help
./hirepaper llm --help
```

All commands now display concise, action-oriented descriptions in both source and packaged mode. No behavioral changes were made.
