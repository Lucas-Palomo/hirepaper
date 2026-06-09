# hirepaper content tailor

Generate a vacancy-tailored `candidate.json` using an LLM for planning and
local deterministic application of the resulting changes.

## Usage

```bash
hirepaper content tailor <candidate.json> <vacancy.txt> --output <tailored.json> [options]
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `candidate` | positional | required | Path to the candidate JSON file |
| `vacancy` | positional | required | Path to the vacancy text file |
| `--output` | string | **required** | Path to the tailored JSON (primary artifact) |
| `--config` | string | — | TOML config override (otherwise uses `./config.toml` when present or environment variables) |
| `--locale`, `-l` | string | `en` | Report locale (`en`, `pt-BR`) |
| `--mode` | string | `conservative` | Tailoring mode: `conservative` or `rewrite` |
| `--inference` | string | `medium` | Inference level: `low`, `medium`, `high` |
| `--extra-context` | string | — | Additional context file (repeatable) |
| `--report-output` | string | — | Save the tailoring report separately |
| `--report-format` | string | `text` | Report format: `text`, `md`, or `json` |
| `--log` | string | — | Save execution logs as a ZIP archive |
| `--prompt` | string | — | Custom prompt file for the planning stage |
| `--timeout-seconds` | integer | profile | LLM request timeout in seconds |
| `--max-tokens` | integer | profile | Maximum response token count |
| `--force` | flag | `false` | Allow overwrite of existing files |
| `--quiet` | flag | `false` | Suppress the detailed terminal report |
| `--verbose`, `-v` | count | `0` | Verbosity level (curl, debug, full HTTP trace) |

## Modes

### conservative (default)

Allowed actions:
- Reorder sections, entries, and bullets
- Keep or remove optional content
- Prioritize or deprioritize skills, projects, and experiences
- Rewrite `headline`, `summary`, and `target_role` conservatively

Not allowed:
- Rewrite experience or project bullets
- Merge N:1 bullets
- Broad semantic expansion

### rewrite

Everything `conservative` can do, plus:
- Rewrite experience bullets (`experience_bullet`) and project text
  (`project_description`, `project_bullet`)
- Merge N:1 bullets when all source claims remain grounded in evidence
- Rewrite `headline`, `summary`, and `target_role` more aggressively

Forbidden in both modes:
- Invent facts, metrics, dates, technologies, or employers
- Expand one bullet into many (1:N)
- Alter factual identity data such as names, companies, roles, dates, or certifications

### Comparison Table

| Action | conservative | rewrite |
|--------|-------------|---------|
| Reorder sections/items | Yes | Yes |
| Remove optional content | Yes | Yes |
| Prioritize/deprioritize | Yes | Yes |
| Rewrite headline | Yes (conservative) | Yes (aggressive) |
| Rewrite summary | Yes (conservative) | Yes (aggressive) |
| Rewrite target_role | Yes (conservative) | Yes (aggressive) |
| Rewrite experience bullets | No | Yes |
| Rewrite project description | No | Yes |
| Rewrite project highlights | No | Yes |
| Merge N:1 bullets | No | Yes |

## Inference Levels

| Level | Description |
|-------|-------------|
| `low` | Near-literal wording with minimal semantic equivalence |
| `medium` | Common technical equivalence allowed when justified |
| `high` | Broader semantic reformulation, always grounded and explainable |

`--mode` controls **what** may be rewritten; `--inference` controls **how**
freely the model may reformulate text.

## Examples

Basic tailoring in conservative mode:

```bash
hirepaper content tailor data/candidate.json data/vacancy.txt \
  --output output/tailored.json
```

With report and logs:

```bash
hirepaper content tailor data/candidate.json data/vacancy.txt \
  --output output/tailored.json \
  --report-output output/tailor-report.txt \
  --report-format text \
  --log output/tailor-log.zip
```

Markdown report:

```bash
hirepaper content tailor data/candidate.json data/vacancy.txt \
  --output output/tailored.json \
  --report-format md \
  --report-output output/tailor-report.md
```

Rewrite mode with extra context:

```bash
hirepaper content tailor data/candidate.json data/vacancy.txt \
  --output output/tailored.json \
  --mode rewrite \
  --extra-context README.md \
  --extra-context docs/file-map.md
```

JSON report with quiet terminal output:

```bash
hirepaper content tailor data/candidate.json data/vacancy.txt \
  --output output/tailored.json \
  --report-format json \
  --report-output output/tailor-report.json \
  --quiet
```

Force overwrite of existing files:

```bash
hirepaper content tailor data/candidate.json data/vacancy.txt \
  --output output/tailored.json \
  --force
```

## Internal Flow

1. Validate output destinations before any LLM call
2. Load and validate the candidate JSON via `load_candidate`
3. Run `content lint` — failures abort, warnings continue
4. Load the vacancy text and any extra context files
5. Build a payload with stable IDs for all mutable items
6. Send the payload, schemas, and vacancy to the LLM, which returns a structured plan
7. Validate the plan against `content-tailor-plan.schema.json`
8. Apply structural actions locally (removals, reordering, prioritization)
9. If the plan includes `rewrite_requests`, issue focused LLM rewrite calls and validate them against `content-tailor-rewrite-response.schema.json`
10. Assemble the final JSON locally; the LLM never emits the final candidate JSON directly
11. Validate the final JSON against `candidate.schema.json`, `load_candidate`, and `content lint`
12. Generate the report and save artifacts

## Stable IDs

The payload sent to the LLM includes deterministic IDs for mutable items:

| Prefix | Item |
|--------|------|
| `exp_` | Experience entry |
| `exp_`_hl_ | Experience highlight |
| `exp_`_ach_ | Experience achievement |
| `proj_` | Project entry |
| `proj_`_hl_ | Project highlight |
| `skill_cat_` | Skill category |
| `skill_cat_`_item_ | Individual skill |
| `cert_` | Certification |
| `award_` | Award |
| `vol_` | Volunteer entry |
| `lang_` | Language |
| `link_` | Personal link |
| `extra_link_` | Extra link |

The LLM uses these IDs in the plan to reference items unambiguously.

## Text Report Structure

```
========================================
           LLM-BASED CANDIDATE TAILORING REPORT
========================================

DISCLAIMER
------------------------------------------------------------
This tailoring uses an LLM and may contain subjective judgment.

MODE:       CONSERVATIVE
INFERENCE:  MEDIUM

EXECUTIVE SUMMARY
------------------------------------------------------------
...

TARGET ROLE
------------------------------------------------------------
Senior Backend Engineer

KEY CHANGES
------------------------------------------------------------
  * Structural changes
    - Removed experience_entry: exp_2 — Less relevant
    - Reordered ...

REWRITES
------------------------------------------------------------
  * Headline [headline]
    Emphasize backend architecture and leadership

REMOVED / DEPRIORITIZED SECTIONS
------------------------------------------------------------
  * awards [REMOVED]
    No relevant awards for this vacancy

LINT STATUS
------------------------------------------------------------
  Before: PASS
  After:  PASS

WARNINGS
------------------------------------------------------------
  ! ...
```

## JSON Output Structure (report)

```json
{
  "disclaimer": "...",
  "mode": "conservative",
  "inference": "medium",
  "summary": "...",
  "target_role": "Senior Backend Engineer",
  "key_changes": [
    { "title": "Structural changes", "details": ["..."] }
  ],
  "rewrites": [
    { "target_kind": "headline", "target_refs": ["headline"],
      "summary": "...", "grounding": ["..."] }
  ],
  "removed_or_deprioritized_sections": [
    { "section_name": "awards", "decision": "removed", "reason": "..." }
  ],
  "grounding_notes": [...],
  "lint_status_before": { "status": "pass", "ok": 10, "warn": 0, "fail": 0 },
  "lint_status_after": { "status": "pass", "ok": 12, "warn": 0, "fail": 0 },
  "warnings": []
}
```

## Logs

`--log <path>` saves a ZIP archive containing:

- `meta.json` — execution metadata
- `candidate-input-payload.json` — candidate payload with stable IDs sent to the LLM
- `vacancy.txt` — original vacancy text
- `extra-context-N.txt` — extra context files when provided
- `candidate-schema.json`
- `tailor-plan-schema.json`
- `tailor-report-schema.json`
- `rewrite-response-schema.json`
- `prompt.txt` — prompt used for the plan stage
- `plan-raw-response.json` — raw LLM response for the plan
- `validated-plan.json` — validated plan
- `rewrite-responses.json` — rewrite responses when applicable
- `final-tailored-candidate.json` — final tailored candidate JSON
- `tailor-report.json` — generated report
- `lint-before.json` / `lint-after.json` — lint summaries before and after tailoring

## Behavior

- `--output` is required. The command fails if it is omitted.
- Overwrite of existing files happens only with `--force` or interactive TTY confirmation.
- If `content lint` fails on the original candidate, the command aborts before any LLM call.
- If `content lint` fails on the final tailored JSON, the command fails and does not emit a success message.
- Lint warnings do not block success.
- `--quiet` suppresses only the detailed terminal report; critical messages and saved-path confirmations remain visible.
