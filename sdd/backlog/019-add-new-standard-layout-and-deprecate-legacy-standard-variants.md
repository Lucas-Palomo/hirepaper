# 019 - Add new `standard` layout and deprecate legacy standard variants

## Status
Completed

## Context
The project currently exposes two standard-family layouts:

- `standard-headline-inline`
- `standard-headline-tabular`

Both remain functional and should stay available in the CLI for now, but they are no longer the right long-term direction for the product.

The next layout iteration should establish a single canonical standard layout that:
- becomes the default layout in the CLI;
- reflects a clearer product design direction;
- improves visual hierarchy and density handling;
- preserves ATS-safe extraction behavior.

The legacy standard variants will remain temporarily for compatibility and comparison, but they should be treated as deprecated layouts that will be removed in a future task.

## Goal
Implement a new canonical layout named:

```text
standard
```

This new layout must:
- follow the previously agreed Concept 1;
- become the default layout when `--layout` is omitted;
- remain ATS-safe;
- coexist temporarily with the two older standard-family layouts;
- trigger a deprecation warning when one of the older layouts is explicitly selected.

## Scope Boundary
This task is specifically about implementing a new layout and updating CLI/layout selection behavior around it.

It must not:
- remove `standard-headline-inline`;
- remove `standard-headline-tabular`;
- implement a two-column main-body layout;
- redesign content generation semantics unrelated to layout;
- introduce job matching or tailoring logic;
- change the candidate schema unless a small layout-driven addition is strictly necessary;
- treat the old layouts as already deleted.

A small schema addition is acceptable in this task if it is directly justified by the new layout and remains tightly scoped.

## Product Direction
The project should move from “multiple equivalent standard layouts” to:
- one canonical standard layout for normal use;
- two temporary legacy layouts kept available until later removal.

The implementing agent should optimize for:
- one strong default experience;
- explicit visual design choices;
- lower maintenance cost over time.

## Required Layout Concept
The new `standard` layout must follow **Concept 1: Main Flow + Utility Bands**.

That means:

### Core rule
The body should remain primarily single-column and reading-order predictable.

### Section strategy
Keep high-priority ATS/recruiter sections in the main linear flow:
- Profile
- Experience
- Education

Render lower-priority/supporting sections in more compact bands or dense linear groups:
- Skills
- Certifications
- Projects
- Awards
- Volunteer
- Languages
- Online / extra links

Important:
- this is not permission to create a long-running second sidebar column;
- the reading order must remain machine-friendly;
- compactness should come from hierarchy and grouping, not from ATS-fragile page composition.

## Visual Direction
The implementing agent is responsible for making explicit visual decisions.

This task does not ask the agent to merely “shuffle existing blocks around”.

The new layout should be intentionally designed with clear choices for:
- typography hierarchy;
- section heading treatment;
- spacing rhythm;
- contact/header composition;
- emphasis handling for role, company, location, and dates;
- visual treatment of compact utility sections;
- divider style and section separation;
- link presentation;
- page density balance.

The visual language should feel:
- professional;
- modern but restrained;
- ATS-safe rather than decorative;
- denser and more polished than the current legacy layouts;
- readable under real resume content, not just ideal sample content.

The agent should be expected to make design decisions explicitly rather than preserving old styling by inertia.

### Visual priority order
The implementing agent should preserve a clear visual priority order.

Recommended priority:
1. candidate name;
2. professional headline;
3. experience section and experience-entry hierarchy;
4. company / role / date / location structure within experience;
5. education;
6. projects / skills / certifications;
7. utility sections such as languages, online links, awards, volunteer.

This is important because secondary sections should not visually overpower the core career narrative.

### Density by section type
The layout should not apply one uniform density rhythm to every section.

Recommended behavior:
- `Experience`: allowed to breathe more and carry the strongest rhythm;
- `Education`: concise, but not visually collapsed;
- `Projects`: moderately compact;
- `Skills`, `Certifications`, `Languages`, `Online`, `Awards`: more compact and utility-oriented.

The goal is to make the document feel intentionally prioritized rather than mechanically spaced.

### One-page versus multi-page behavior
The goal of the new layout is not to force every resume into one page.

The goal is:
- better density;
- better hierarchy;
- better page-break behavior;
- better scanability.

The implementing agent should not treat “fits on one page” as automatic success if the cost is:
- overly compressed line spacing;
- crowded header treatment;
- tiny utility text;
- reduced bullet readability;
- weak page rhythm.

## Page-Break Behavior
The implementing agent must treat page-break behavior as a first-class layout concern.

This project cannot assume all resumes will fit neatly into one or two pages.

Some candidate inputs will legitimately produce longer documents, and the new `standard` layout must degrade coherently when that happens.

Without explicit page-break discipline, the PDF can break in visually inconsistent or semantically awkward places.

Examples of bad breaks:
- a section heading stranded at the bottom of a page with no meaningful content under it;
- a company/role line separated from its bullets;
- a project title on one page with its description or highlights pushed to the next;
- certifications, languages, or utility sections split in a way that makes entries look detached or incomplete;
- a nearly empty trailing page caused by poor spacing strategy.

### Required page-break principles
The new layout should aim for:
- section heading cohesion;
- entry cohesion;
- predictable spacing near page boundaries;
- graceful degradation for long resumes;
- no obviously broken visual rhythm at page transitions.

### Entry cohesion expectations
At minimum, the implementing agent should try to keep together when practical:
- a section title plus at least the beginning of its first entry;
- an experience header block (company, role, dates, location, metadata) with at least one bullet;
- a project title with its first descriptive line;
- compact utility entries that are visually understood as one unit.

This does not require impossible all-or-nothing page packing.

It does require the agent to actively prevent the most jarring split points.

### Practical guidance
The agent may use LaTeX techniques such as:
- controlled vertical spacing;
- penalties or no-break hints where appropriate;
- tighter grouping for compact sections;
- avoiding excessive fixed whitespace that creates brittle pagination.

The exact implementation is up to the agent, but the layout must not rely on luck for acceptable page transitions.

### Wrapping and overflow behavior
The implementing agent must explicitly account for long real-world values.

At minimum, the layout should degrade cleanly when handling:
- long headlines;
- long role titles;
- long company names;
- long certification names;
- long visible URLs;
- long project titles with stack text.

The layout must not allow these values to:
- overlap adjacent content;
- force incoherent alignment;
- create brittle one-line assumptions;
- break section hierarchy visually.

### Verification expectation for long outputs
The implementing agent should not validate only against the happy-path sample if it produces a short document.

They should also verify at least one longer-content scenario that exercises page breaks and confirm:
- section starts are not awkwardly stranded;
- experience entries do not split in obviously broken ways;
- utility sections remain readable across pages;
- no nearly empty orphaned final page appears without strong justification.

## Recommended Structural Shape
The implementing agent may tune details, but the layout should generally move in this direction:

1. Header
   - strong candidate name;
   - professional headline if present;
   - clean contact presentation;
   - links integrated compactly and visibly;
   - header density controlled across multiple lines when needed, not forced into one crowded row.

2. Profile
   - short, readable, full-width introduction.

3. Experience
   - full-width, strongest hierarchy in the document;
   - company, role, date, location, and technologies presented clearly;
   - optional contract/employment-type context may be shown as secondary metadata when present;
   - bullets remain easy to scan.

4. Education
   - full-width, concise, aligned with the main experience rhythm.

5. Utility sections
   - skills;
   - certifications;
   - projects;
   - awards;
   - volunteer;
   - languages;
   - online links.

These utility sections may be rendered more compactly than the core sections, but still in an extraction-safe order.

## Wireframe Reference
The implementing agent should use the following wireframe as a layout intention reference.

This is not pixel-precise, but it is deliberate enough to communicate structure, hierarchy, and density goals.

```text
+----------------------------------------------------------------------------------+
|                                   CANDIDATE NAME                                 |
|                        Professional Headline / Target Position                    |
|----------------------------------------------------------------------------------|
| Email: ...        Phone: ...        Location: ...                                 |
| LinkedIn: ...     GitHub: ...       Portfolio: ...                                |
+----------------------------------------------------------------------------------+

+----------------------------------------------------------------------------------+
| Profile                                                                          |
| Short full-width summary with controlled line length and strong scanability.     |
+----------------------------------------------------------------------------------+

+----------------------------------------------------------------------------------+
| Experience                                                                       |
| Company Name                                            Role Title               |
| Location                                                Date Range               |
| Technology stack / role context / optional contract type                         |
| - Achievement bullet                                                            |
| - Achievement bullet                                                            |
| - Achievement bullet                                                            |
|----------------------------------------------------------------------------------|
| Company Name                                            Role Title               |
| Location                                                Date Range               |
| Technology stack / role context / optional contract type                         |
| - Achievement bullet                                                            |
| - Achievement bullet                                                            |
+----------------------------------------------------------------------------------+

+----------------------------------------------------------------------------------+
| Education                                                                        |
| Institution                                             Degree / Date Range      |
| Location / GPA / Honors                                                         |
+----------------------------------------------------------------------------------+

+----------------------------------------------------------------------------------+
| Skills                                                                           |
| Category: item, item, item, item                                                |
| Category: item, item, item, item                                                |
+----------------------------------------------------------------------------------+

+----------------------------------------------------------------------------------+
| Projects                                                                         |
| Project Name — stack — visible URL                                               |
| Role / Date Range                                                                |
| Short description                                                                 |
| - Optional project highlight                                                     |
+----------------------------------------------------------------------------------+

+--------------------------------------+-------------------------------------------+
| Certifications                       | Languages / Online / optional utilities   |
| Cert — Issuer — Date                 | English: ...                              |
| Cert — Issuer — Date                 | Portuguese: ...                           |
| Visible credential URL if present    | Portfolio: ...                            |
+--------------------------------------+-------------------------------------------+

+----------------------------------------------------------------------------------+
| Optional compact sections: Awards / Volunteer / other utility sections           |
+----------------------------------------------------------------------------------+
```

### Wireframe interpretation rules
The wireframe implies:
- header may use multiple horizontal zones, but must remain extraction-safe;
- the header should be treated as a controlled multi-line block, not a single-line compression target;
- experience and education stay in the main single-column flow;
- utility sections become denser only after the core sections;
- the split near the bottom is local and compact, not a full-page parallel sidebar;
- visible URLs should remain explicit text, not icon-only affordances;
- links should preserve a labeled visible form such as `LinkedIn: linkedin.com/in/example`;
- optional employment/contract type should appear only as subordinate context, never as the dominant experience signal;
- spacing should prioritize scanability over visual decoration.

### What the wireframe is trying to prevent
The implementing agent should explicitly avoid:
- a true two-column body where experience runs on the left and support sections run permanently on the right;
- sidebar-first composition;
- decorative visual density that harms text extraction order;
- a crowded single-line header that sacrifices readability just to keep all contact and links on one row;
- rendering contract type so prominently that it competes with company, role, or dates in every experience entry;
- tiny utility text that looks elegant but becomes low-trust in real recruiter use.

## ATS-Safety Requirements
The new `standard` layout must preserve the project’s ATS-safety constraints:
- visible text extractable with `pdftotext`;
- sensible reading order;
- no hidden-link-only behavior;
- no Type 3 fonts;
- visible URLs remain present in extracted text;
- icons remain decorative only;
- section labels and contact information remain recoverable.

Links must remain visibly recoverable in extracted text with contextual labels where applicable.

Preferred pattern:

```text
LinkedIn: linkedin.com/in/example
GitHub: github.com/example
Portfolio: example.dev
```

Avoid:
- icon-only links;
- generic link text without visible destination;
- unlabeled dense URL clusters that become ambiguous in the header.

The implementation must be validated on extracted text, not only by visual appearance.

## CLI and Layout Selection Requirements

### 1. New layout name
The new canonical layout name must be:

```text
standard
```

### 2. Default behavior
If the user does not provide `--layout`, the CLI must default to:

```text
standard
```

### 3. Legacy layouts remain available
The following layout values must still work:
- `standard-headline-inline`
- `standard-headline-tabular`

### 4. Legacy layout warning
If the user explicitly selects one of the old layouts, the CLI should emit a warning indicating that:
- the layout is legacy/deprecated;
- it remains supported for now;
- it will be removed in a future release/task.

Recommended tone:
- concise;
- non-blocking;
- printed to stderr.

Example shape:

```text
Warning: layout 'standard-headline-inline' is deprecated and will be removed in a future release; use 'standard' instead.
```

## Implementation Direction
The implementing agent should:
- add a new template/class pair for `standard`;
- wire it into the layout map;
- make it the CLI default;
- preserve existing legacy layouts in the map;
- add runtime deprecation warnings for explicit legacy layout selection.

If the agent decides to support Brazilian-style employment context in the new layout, the preferred shape is a tightly scoped optional addition such as:

```text
experience.employment_type
```

Examples:
- `CLT`
- `PJ`
- `Contract`
- `Freelance`
- `Internship`
- `Temporary`

Rules for this field:
- it must remain optional;
- it must not become a required migration burden for existing JSON;
- it should render only when present;
- it should appear as secondary metadata, not as a primary heading element;
- if added, parsing/model changes should stay minimal and local to this task.

### Icon usage
If icons are used in the new layout:
- they should remain decorative only;
- they should be concentrated primarily in the header or similarly small support contexts;
- they must not become necessary for understanding the content;
- they must not dominate the text visually;
- they should not be scattered so heavily across utility sections that they add noise.

The layout should remain understandable and trustworthy even if the icons are mentally ignored.

### Optional-section fallback behavior
The new layout must remain coherent when optional sections are missing.

Examples:
- no projects;
- no certifications;
- no awards;
- no volunteer;
- no languages;
- no extra links.

The page should not look structurally incomplete or visually dependent on optional content being present.

This is especially important for utility-band treatment: the layout must collapse gracefully when one or more utility sections are absent.

If the implementation benefits from shared class/template structure, the agent may refactor carefully, but should avoid broad unrelated rewrites.

## Documentation Expectations
This task should update:
- `project.md`
- `agents.md` if command examples or expectations need it
- any user-facing layout references that still imply the old layouts are the primary standard options

The documentation should clearly state:
- `standard` is the default and canonical layout;
- the other two standard-family layouts are legacy/deprecated but still available temporarily.

## Acceptance Criteria
This task should be considered complete only if:

1. A new layout named `standard` exists.
2. The new layout follows the Main Flow + Utility Bands concept.
3. The new layout becomes the default when `--layout` is omitted.
4. `standard-headline-inline` still works.
5. `standard-headline-tabular` still works.
6. Explicit use of either legacy layout emits a deprecation warning.
7. The new layout passes ATS validation requirements.
8. Visual verification is performed, not just text extraction verification.
9. Documentation reflects `standard` as the canonical layout.

## Suggested Verification
The implementing agent should verify at least:

```bash
./curriculum-gen-dev pdf generate data/candidate.json -o output/standard-default.pdf --locale en
./curriculum-gen-dev pdf check output/standard-default.pdf

./curriculum-gen-dev pdf generate data/candidate.json -o output/standard-explicit.pdf --layout standard --locale en
./curriculum-gen-dev pdf check output/standard-explicit.pdf

./curriculum-gen-dev pdf generate data/candidate.json -o output/legacy-inline.pdf --layout standard-headline-inline --locale en
./curriculum-gen-dev pdf generate data/candidate.json -o output/legacy-tabular.pdf --layout standard-headline-tabular --locale en
```

And also:
- inspect extracted text from the new layout;
- render the new PDF to images and inspect visual hierarchy, spacing, and page balance;
- confirm legacy layouts emit the expected warning and still generate successfully.

## Notes For The Implementing Agent
- Treat this as a real layout-design task, not a minimal rename.
- The new `standard` layout should be an explicit design decision.
- Do not turn the main page body into a sidebar/two-column resume.
- Keep the old layouts alive for now, but make their legacy status clear at runtime.
