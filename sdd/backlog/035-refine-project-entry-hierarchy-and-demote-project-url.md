# 035 - Refine project entry hierarchy and demote project URL in `standard` layout

## Status
Completed

## Context
The current `standard` layout renders project entries using the generic
`\resumeEntry` structure, and `proj.url` is currently injected into the same
header block as the project identity metadata.

In practice, that gives the project URL too much visual weight.

Today, the effective hierarchy is close to:

```text
Project Name                    Role
Visible URL                     Period
Technologies
Description
Bullets
```

This makes the URL compete with:

- project name;
- role;
- period;
- description;
- highlights.

That is the wrong priority order for this section. The URL is useful, but it is
supporting utility information, not part of the primary identity of the project
entry.

## Goal
Refine the `Projects` section hierarchy so the URL is demoted to a final utility
sub-line, while the main header focuses on project identity and core metadata.

Target effective structure:

```text
Project Name                    Role
Technologies                    Period

Description
Bullets
URL: github.com/example/project
```

This should improve scanability and reduce visual noise while preserving visible
URLs and ATS-safe extraction.

## Product Decision
Project URLs should remain visible in the PDF, but they should not occupy a
primary header slot in the project entry.

Required priority order for each project entry:

1. project name
2. role
3. technologies / keywords
4. period
5. description
6. bullets/highlights
7. URL as final utility detail

Rationale:

- the project should be read first as work, not as a link;
- technologies are more useful than the URL during the first scan pass;
- the URL is still valuable, but mostly as follow-up reference;
- moving the URL to the end preserves utility while removing unnecessary visual
  competition.

## Scope
This task may update:

- `src/curriculum_gen/generator.py`
- `templates/standard.cls`
- `templates/standard.tex` if needed
- `project.md` if project layout behavior should be clarified
- `sdd/history/`

This task should not:

- remove project URLs from the candidate schema;
- hide project URLs entirely;
- redesign unrelated sections;
- widen into a full projects data-model refactor.

## Current Undesired Structure
Current effective structure:

```text
FastAPI Admin                   Core contributor
github.com/fastapi-admin/...    Jan 2023 -- Jun 2024
Python, FastAPI, SQLAlchemy
Description
Bullets
```

Problems with this structure:

- the URL is promoted to a structural header position;
- the link visually competes with role and period;
- the project block starts to feel like a link card instead of a project entry;
- long URLs create disproportionate visual noise in the main project header.

## Target Structure
Target effective structure:

```text
FastAPI Admin                   Core contributor
Python, FastAPI, SQLAlchemy     Jan 2023 -- Jun 2024

Admin panel integration for FastAPI applications with role-based access control and automatic CRUD generation
- Designed RBAC system supporting fine-grained permission assignment across 10+ resource types
URL: github.com/fastapi-admin/fastapi-admin
```

### Required URL label
When a project URL is present, it should render explicitly as:

```text
URL: {visible-url}
```

Example:

```text
URL: github.com/fastapi-admin/fastapi-admin
```

The visible URL should continue to follow current project conventions such as
cleaned display text from `_clean_url()`.

## Required Behavior

### 1. Header hierarchy
The first project line must prioritize:

- project name on the left;
- role on the right when present.

The URL must not appear in the first line.

### 2. Metadata line
The second project line should carry:

- technologies / keywords on the left when present;
- period on the right when present.

The URL must not displace technologies from this metadata line.

### 3. Description and bullets in main flow
Project description and highlights should remain in the main body flow below the
header/metadata lines.

They should continue to read as the main explanatory content of the project.

### 4. URL as final utility sub-line
If `proj.url` is present, it must render after the description and bullets as a
final utility sub-line in this form:

```text
URL: {visible-url}
```

Required behavior:

- the visible label must be exactly `URL:`;
- the visible destination must remain human-readable;
- the hyperlink target should still point to the full original URL;
- if no project URL exists, no `URL:` line should be rendered.

### 5. ATS-safe text preservation
The change must preserve:

- visible project name;
- visible role;
- visible technologies when present;
- visible period when present;
- visible description and bullets;
- visible project URL when present;
- sensible extraction order in `pdftotext`.

The task is not complete if the visual hierarchy improves but visible URLs are
lost or extraction order regresses.

## Recommended Implementation Direction
The exact implementation is up to the implementing agent, but project rendering
should no longer use the URL as the fourth field in the main `\resumeEntry`
header block.

Acceptable directions may include:

- keeping a two-line project header and moving URL into a trailing
  `\resumeEntrySub`-style line;
- adding a dedicated project macro with explicit lines for header, metadata, and
  utility URL;
- rendering the URL after bullets as a subdued final line.

Preferred outcome:

- clear hierarchy;
- reduced visual noise;
- stable handling of long URLs;
- preserved ATS-safe visible text.

## Verification
Minimum verification should include visual and ATS-safe extraction checks.

### Source-mode generation

```bash
./curriculum-gen-dev pdf generate data/candidate.json --output /tmp/project-layout.pdf --density compact --locale en
./curriculum-gen-dev pdf check /tmp/project-layout.pdf
pdftotext /tmp/project-layout.pdf - | sed -n '/Projects/,$p'
pdftoppm -png /tmp/project-layout.pdf /tmp/project-layout
```

### Fixture coverage
The implementing agent should verify at least:

- one project with URL, role, technologies, description, and bullets;
- one project with URL but no role if available, or a temporary fixture;
- one project with no URL.

This is necessary to confirm the optional `URL:` line behaves correctly.

### Packaged verification

```bash
.venv/bin/python build.py
./curriculum-gen pdf generate data/candidate.json --output /tmp/project-layout-packaged.pdf --density compact --locale en
./curriculum-gen pdf check /tmp/project-layout-packaged.pdf
```

## Expected Verification Outcomes
The implementing agent should confirm:

1. project URLs no longer appear in the primary project header block;
2. project entries render with name/role first and technologies/period second;
3. project URLs render only as a final `URL: {url}` utility line when present;
4. extracted text still preserves readable project ordering and visible URLs;
5. source and packaged execution behave consistently.

## Acceptance Criteria
1. Project entries in the `standard` layout no longer place `proj.url` in the
   main header slot.
2. Project entries render with project name and role on the first line.
3. Project entries render technologies/keywords and period on the second line.
4. Project description and bullets remain in the main body flow.
5. Project URLs render only as a final utility line in the exact visible form
   `URL: {url}` when present.
6. ATS-safe visible-text behavior is preserved.
7. The change is verified in source mode and packaged mode.
8. A history entry records the implementation, rationale, and verification.

## Notes For The Implementing Agent
- Treat the project URL as supporting utility information, not identity.
- Prefer hierarchy and scanability over aggressive compaction.
- Validate both rendered appearance and extracted text.
