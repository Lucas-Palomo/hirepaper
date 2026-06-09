# hirepaper content

Analyze and transform candidate source data.

## Subcommands

- `init` — Bootstrap a starter candidate JSON
- `lint` — Validate candidate data quality
- `match` — ATS-style LLM compatibility analysis
- `tailor` — Tailor candidate JSON to a vacancy

---

## content init

Bootstrap a starter candidate JSON file from the bundled example template.

```bash
hirepaper content init [--output <path>] [--force]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output` | string | `candidate.json` | Output path for the starter JSON |
| `--force` | flag | `false` | Overwrite existing file |

The generated file is a ready-to-edit example. Validate it with `hirepaper content lint`.

---

## content lint

Validate candidate JSON quality.

```bash
hirepaper content lint <candidate_json>
```

| Argument | Type | Description |
|----------|------|-------------|
| `candidate_json` | positional | Path to the candidate JSON file |

Checks structure, required sections, placeholder text, density balance, and keyword coverage. Exits non-zero on failure.

---

## content match

ATS-style LLM compatibility analysis comparing a candidate JSON against a raw vacancy text.

```bash
hirepaper content match <candidate.json> <vacancy.txt> [options]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `candidate` | positional | required | Path to candidate JSON |
| `vacancy` | positional | required | Path to vacancy text file |
| `--config` | string | — | TOML config override |
| `--locale`, `-l` | string | `en` | Response locale (`en`, `pt-BR`) |
| `--format` | string | `text` | Output format (`text`, `md`, `json`) |
| `--output` | string | — | Save rendered result to file |
| `--log` | string | — | Save execution log as ZIP archive |
| `--prompt` | string | — | Custom plain-text prompt file |
| `--strict` | flag | `false` | Restrict to explicit evidence only |
| `--inference` | string | `medium` | Inference level (`low`, `medium`, `high`) |
| `--timeout-seconds` | int | — | Override request timeout |
| `--max-tokens` | int | — | Override response token limit |
| `--verbose`, `-v` | count | `0` | Increase verbosity |

See [docs/content-match.md](content-match.md) for detailed usage, output formats, and examples.

---

## content tailor

Generate a vacancy-tailored candidate JSON using LLM planning and deterministic local application.

```bash
hirepaper content tailor <candidate.json> <vacancy.txt> --output <tailored.json> [options]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `candidate` | positional | required | Path to candidate JSON |
| `vacancy` | positional | required | Path to vacancy text file |
| `--output` | string | **required** | Path for tailored JSON |
| `--config` | string | — | TOML config override |
| `--locale`, `-l` | string | `en` | Report locale |
| `--mode` | string | `conservative` | Mode (`conservative`, `rewrite`) |
| `--inference` | string | `medium` | Level (`low`, `medium`, `high`) |
| `--extra-context` | string | — | Extra text source (repeatable) |
| `--report-output` | string | — | Save report separately |
| `--report-format` | string | `text` | Report format (`text`, `md`, `json`) |
| `--log` | string | — | Save execution log as ZIP |
| `--prompt` | string | — | Custom plan-stage prompt |
| `--timeout-seconds` | int | — | Override request timeout |
| `--max-tokens` | int | — | Override response token limit |
| `--force` | flag | `false` | Overwrite existing output |
| `--quiet` | flag | `false` | Suppress terminal report |

See [docs/content-tailor.md](content-tailor.md) for detailed usage, modes, and examples.
