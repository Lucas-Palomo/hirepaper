# hirepaper content match

ATS-style LLM compatibility analysis comparing a candidate JSON against a raw
vacancy text.

## Usage

```bash
hirepaper content match <candidate.json> <vacancy.txt> [options]
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `candidate` | positional | required | Path to the candidate JSON file |
| `vacancy` | positional | required | Path to the vacancy text file |
| `--config` | string | — | TOML config override (otherwise uses `./config.toml` when present or environment variables) |
| `--locale`, `-l` | string | `en` | Analysis locale (`en`, `pt-BR`) |
| `--format` | string | `text` | Output format: `text`, `md`, or `json` |
| `--output` | string | — | Save the rendered result to this path |
| `--log` | string | — | Save execution logs as a ZIP archive |
| `--prompt` | string | — | Custom prompt file (replaces the default prompt) |
| `--strict` | flag | `false` | Restrict analysis to explicit evidence only (requires `--inference=low`) |
| `--inference` | string | `medium` | Inference level: `low`, `medium`, `high` |
| `--timeout-seconds` | integer | profile | LLM request timeout in seconds |
| `--max-tokens` | integer | profile | Maximum response token count |
| `--verbose`, `-v` | count | `0` | Verbosity level (curl, debug, full HTTP trace) |

## Examples

Basic analysis with text output:

```bash
hirepaper content match data/candidate.json data/vacancy.txt
```

Save JSON output and logs:

```bash
hirepaper content match data/candidate.json data/vacancy.txt \
  --format json \
  --output output/match-result.json \
  --log output/match-log.zip
```

Save Markdown report:

```bash
hirepaper content match data/candidate.json data/vacancy.txt \
  --format md \
  --output output/match-report.md
```

Strict mode with low inference:

```bash
hirepaper content match data/candidate.json data/vacancy.txt \
  --strict --inference low
```

Use a custom prompt:

```bash
hirepaper content match data/candidate.json data/vacancy.txt \
  --prompt my-prompt.txt
```

## Text Report Structure

```
========================================
           LLM-BASED ATS COMPATIBILITY ANALYSIS
========================================

DISCLAIMER
------------------------------------------------------------
This analysis uses an LLM and may contain subjective judgment.

SCORE:      85/100
RATING:     GOOD
VERDICT:    ...

EXECUTIVE SUMMARY
------------------------------------------------------------
...

STRENGTHS
------------------------------------------------------------
  1. Title
     - evidence

GAPS
------------------------------------------------------------
  1. Title  [SEVERITY]
     - evidence

MATCHED REQUIREMENTS
------------------------------------------------------------
  1. Requirement (priority) -> matched [confidence]
     - evidence

UNMATCHED REQUIREMENTS
------------------------------------------------------------
  1. Requirement (priority) -> not_matched [confidence]
     - evidence

INFERENCES
------------------------------------------------------------
  1. Claim
     Basis: ...
     Confidence: ...
```

## JSON Output Structure

```json
{
  "disclaimer": "...",
  "score": 85,
  "rating": "good",
  "verdict": "...",
  "summary": "...",
  "strengths": [
    { "title": "...", "evidence": ["..."] }
  ],
  "gaps": [
    { "title": "...", "severity": "medium", "evidence": ["..."] }
  ],
  "matched_requirements": [
    { "requirement": "...", "priority": "must_have",
      "assessment": "matched", "confidence": "high", "evidence": ["..."] }
  ],
  "unmatched_requirements": [ ... ],
  "inferences": [
    { "claim": "...", "basis": "...", "confidence": "medium" }
  ]
}
```

## Behavior

- The command exits non-zero if `content lint` fails on the candidate input.
- `--strict` requires `--inference=low` and restricts analysis to explicit evidence.
- `--inference` controls the model's semantic freedom:
  - `low`: near-literal matching
  - `medium`: common technical equivalence
  - `high`: broader semantic reformulation, still grounded in evidence
- The disclaimer is added automatically to the human-readable report and is not expected to be authored manually.
- `--log` saves artifacts such as `meta.json`, schemas, prompt, candidate payload, vacancy text, raw response, validated result, and usage data.
