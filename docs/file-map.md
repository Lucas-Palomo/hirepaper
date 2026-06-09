# File Map

Important paths in the `hirepaper` project.

## Source Layout

- `src/hirepaper/cli.py`: Typer CLI with top-level `init` and `doctor` commands plus subcommand groups (`content`, `pdf`, `llm`), build orchestration.
  - `hirepaper init` — bootstraps a local `config.toml` from the bundled template.
  - `hirepaper doctor` — canonical environment diagnostics and dependency checks.
  - `hirepaper help`, `hirepaper content help`, `hirepaper pdf help`, `hirepaper llm help` — explicit help aliases.
  - `hirepaper content init [--output <path>] [--force]` — bootstraps a starter candidate JSON from `assets/examples/candidate.example.json`.
  - `hirepaper content lint <json>` — candidate data quality checks.
  - `hirepaper content match <candidate.json> <vacancy.txt> [--config <toml>]` — ATS-style LLM analysis. See [docs/content-match.md](content-match.md).
  - `hirepaper content tailor <candidate.json> <vacancy.txt> --output <tailored.json>` — vacancy-tailored JSON generation. See [docs/content-tailor.md](content-tailor.md).
  - `hirepaper llm health [--config <toml>]` — LLM path health check.
   - `hirepaper llm usage [--config <toml>]` — per-request token usage diagnostic.
   - `hirepaper linkedin help` — explicit help alias.
   - `hirepaper linkedin generate <json> --output <report> --format txt|json` — LinkedIn-focused report generation.
  - `hirepaper pdf generate <json> --output <pdf>` — JSON-to-PDF generation.
  - `hirepaper pdf check <pdf>` — ATS-safe PDF validation.

- `src/hirepaper/generator.py`: JSON model to LaTeX rendering.
- `src/hirepaper/ats_check.py`: PDF ATS-safety validation.
- `src/hirepaper/content_match.py`: ATS-style LLM matching engine.
- `src/hirepaper/content_tailor.py`: candidate-tailoring orchestration.
- `src/hirepaper/linkedin_generate.py`: LinkedIn-focused report generation.
- `src/hirepaper/density.py`: compact/full rendering policies.
- `src/hirepaper/models.py`: candidate data model.
  - `personal.phone` is a `Phone` object with `value` and `hyperlink`.
- `src/hirepaper/loader.py`: JSON loading and validation.
- `src/hirepaper/locale.py`: localized labels and dates.
- `src/hirepaper/llm/config.py`: LLM config loader with profiles.

- `templates/`: LaTeX templates and classes.
  - `standard.tex` / `standard.cls` — canonical `standard` layout.
- `assets/icons/`: decorative SVG icons converted at build time.
- `assets/schemas/candidate.schema.json`: candidate JSON Schema.
- `assets/examples/config.example.toml`: bundled LLM config template.
- `assets/examples/candidate.example.json`: canonical starter example candidate.
- `assets/prompts/`: LLM prompt templates for content match/tailor/linkedin generate.
- `locale/`: gettext locale files.

- `data/candidate.json`: sample candidate input.
- `data/candidate-tailored.json`: sample candidate tailored input.
- `data/vacancy.txt`: sample vacancy input.

- [docs/content.md](content.md): command reference for `content init`, `lint`, `match`, `tailor`.
- [docs/content-match.md](content-match.md): detailed usage for `content match`.
- [docs/content-tailor.md](content-tailor.md): detailed usage for `content tailor`.
- [docs/pdf.md](pdf.md): command reference for `pdf generate` and `pdf check`.

- `sdd/backlog/`: pending task definitions.
- `sdd/history/`: completed task history and decision records.
