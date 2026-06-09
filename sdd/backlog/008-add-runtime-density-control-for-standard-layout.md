# 008 - Add runtime density control for standard layout

## Status
Completed

## Context
The current `standard` layout can render a complete resume, but the generated PDF can become too dense for ATS and human scanning when the candidate JSON contains many sections, links, bullets, projects, awards, and volunteer entries.

The project should keep `candidate.json` focused only on candidate data. Rendering choices such as how much information to include in the PDF must not be stored in the candidate data file.

This task introduces runtime density control for the existing `standard` layout.

## Goal
Allow the CLI/generation flow to produce different ATS-friendly PDF densities from the same candidate data without modifying the input JSON.

Initial supported densities:
- `compact`
- `full`

Important: `full` must not mean dumping all available JSON content into the PDF. It means fuller ATS-optimized coverage with editorial limits.

## Scope
This task covers:
- adding a runtime `density` option;
- defining density policies for the existing `standard` layout;
- applying density rules in the generator;
- keeping the candidate JSON free from rendering configuration;
- optionally preparing for future external density policy files.

This task does not require creating a second layout.

## Non-Goals
- Do not add layout configuration to `candidate.json`.
- Do not create multiple visual layouts yet.
- Do not implement automatic page-count fitting in this task.
- Do not make `full` verbose or uncontrolled.

## Required CLI Behavior
Add a CLI option for density selection.

Expected shape:

```bash
curriculum-gen generate data/candidate.json -o output/resume.pdf -l pt-BR --density compact
curriculum-gen generate data/candidate.json -o output/resume.pdf -l pt-BR --density full
```

Accepted values:
- `compact`
- `full`

The default should be chosen deliberately and documented.

Recommended default:
- `compact`, because the current observed problem is excess density and poor page breaks.

If the implementing agent chooses `full` as default, it must document why.

## Candidate JSON Boundary
Do not add fields such as `layout`, `density`, `rendering`, or `policy` to `candidate.json`.

The candidate JSON should represent:
- who the candidate is;
- what the candidate has done;
- what evidence, skills, links, and credentials the candidate has.

It should not represent:
- how dense the PDF should be;
- which layout should be used;
- runtime rendering preferences.

Rendering decisions belong to CLI/configuration, not candidate data.

## Density Semantics
### `compact`
`compact` should produce a short, selective, highly scannable PDF.

Intent:
- reduce page pressure;
- avoid awkward section/page breaks;
- prioritize the strongest ATS and recruiter signals;
- keep the PDF concise.

Suggested policy:
- limit visible profile links;
- keep summary short;
- limit experience bullets per role;
- prioritize bullets with metrics, impact, and concrete technologies;
- show technologies where helpful;
- omit role summary if it makes entries too tall;
- limit projects;
- limit project bullets;
- keep skills concise;
- omit awards by default;
- omit volunteer by default;
- keep languages compact.

### `full`
`full` should produce a more complete professional resume while remaining ATS-safe and readable.

Intent:
- include broader evidence;
- preserve more candidate context;
- include secondary sections when useful;
- still apply editorial limits.

`full` must not:
- render every possible field without limits;
- produce dense paragraphs;
- include excessive links;
- allow huge bullet lists;
- sacrifice ATS parsing or human readability.

Suggested policy:
- include more links than `compact`, but still cap them;
- include role summaries when concise;
- include technologies per experience;
- include more experience bullets, but cap them;
- include more projects, but cap them;
- include awards when present;
- include volunteer when relevant and concise;
- keep certifications and languages compact.

## Suggested Internal Design
Introduce an internal density policy model, for example:

```python
@dataclass(frozen=True)
class DensityPolicy:
    max_links: int | None
    max_experience_items: int | None
    max_experience_bullets: int | None
    show_role_summary: bool
    show_experience_technologies: bool
    max_skills_per_category: int | None
    max_projects: int | None
    max_project_bullets: int | None
    show_awards: bool
    show_volunteer: bool
```

Initial policy direction:

```python
compact = DensityPolicy(
    max_links=3,
    max_experience_items=3,
    max_experience_bullets=2,
    show_role_summary=False,
    show_experience_technologies=True,
    max_skills_per_category=5,
    max_projects=1,
    max_project_bullets=1,
    show_awards=False,
    show_volunteer=False,
)

full = DensityPolicy(
    max_links=4,
    max_experience_items=None,
    max_experience_bullets=4,
    show_role_summary=True,
    show_experience_technologies=True,
    max_skills_per_category=8,
    max_projects=3,
    max_project_bullets=2,
    show_awards=True,
    show_volunteer=True,
)
```

These exact numbers may be adjusted by the implementing agent if the generated PDF shows a better balance with different values.

## Bullet Prioritization
When limiting bullets, the generator should prefer the strongest bullets.

Priority signals:
- metrics;
- quantified impact;
- action + result structure;
- technologies relevant to the role;
- leadership or ownership;
- production scale.

If structured `achievements` exist, they should generally take priority over plain `highlights`.

The generator should avoid showing weak bullets only because they appear first in the JSON.

## Optional Future Extension: External Policy File
Do not implement this unless it remains simple and clearly useful during the task.

Future shape may be:

```bash
curriculum-gen generate data/candidate.json \
  -o output/resume.pdf \
  -l pt-BR \
  --density full \
  --policy config/density.full.json
```

The external policy file would be rendering configuration, separate from candidate data.

If implemented, precedence should be documented clearly, for example:

```text
internal defaults < --density < --policy
```

For this task, `--density` alone is sufficient.

## Layout Adaptation Requirements
The density system must work with the current `standard` layout.

The implementation should not assume a future layout rewrite.

Density rules should help reduce:
- overfull lines;
- cramped sections;
- awkward page breaks;
- sections split in visually poor places.

This task may include small layout hardening changes if they directly support density behavior, such as:
- separating contact and links;
- improving skill category spacing;
- making section rendering conditional;
- avoiding empty sections;
- adding minimal page-break protection where appropriate.

Large visual redesigns should be deferred.

## Acceptance Criteria
The task should be considered complete only if:

1. `generate` accepts `--density compact|full`.
2. `candidate.json` remains free of rendering configuration.
3. `compact` and `full` produce visibly different output from the same JSON.
4. `compact` reduces content pressure compared to `full`.
5. `full` remains ATS-friendly and controlled, not verbose.
6. Density limits are implemented through explicit policies, not scattered magic numbers.
7. Empty or omitted sections are not rendered as blank headings.
8. Help output documents the density option.

## Suggested Verification
The implementing agent should verify:

```bash
curriculum-gen generate data/candidate.json -o output/resume-compact.pdf -l pt-BR --density compact
curriculum-gen generate data/candidate.json -o output/resume-full.pdf -l pt-BR --density full
```

Then compare:
- page count;
- section presence;
- number of bullets;
- project count;
- awards/volunteer visibility;
- header/link density;
- whether page breaks are less awkward.

## Notes For The Implementing Agent
- Treat `density` as runtime rendering configuration.
- Do not put presentation controls in the candidate JSON.
- `full` is not a content dump. It is a richer ATS-optimized resume with limits.
- The standard layout should remain usable before introducing multiple layouts.
