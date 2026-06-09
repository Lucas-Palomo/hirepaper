# 031 - Fix header link wrap consistency in `standard` layout

## Status
Completed

## Context
The current `standard` layout renders header links inline in the contact block.
In `src/curriculum_gen/generator.py`, `_render_links()` joins header link items
with `\hfill`, and each item currently renders as:

```text
Label: visible-url
```

That works when the line fits comfortably, but under tighter widths or longer
link labels/URLs LaTeX can wrap in visually inconsistent places.

The main failure mode is this:

```text
Label:
visible-url
```

This break is undesirable because:

- it visually detaches the label from the destination;
- it makes the header look unstable and low-quality;
- it creates inconsistent scan behavior across otherwise similar resumes;
- it weakens the intended ATS-safe, human-readable visible-link pattern.

If a link item must wrap, the preferred behavior is:

```text
Label: visible-url
```

or, when there is no room for the full item on the current line:

```text
<line break>
Label: visible-url
```

That is, the link item should move as a unit to the next line rather than
breaking between `Label:` and `visible-url`.

## Goal
Make header link wrapping consistent in the `standard` layout so that a header
link item behaves like an atomic labeled unit.

Required visual rule:

- never render a wrapped header link as `Label:` on one line and the URL on the
  next line;
- if wrapping is necessary, the entire `Label: visible-url` item should move to
  the next line as a unit whenever practical.

## Scope
This task may update:

- `src/curriculum_gen/generator.py`
- `templates/standard.tex`
- `templates/standard.cls`
- `src/curriculum_gen/density.py` only if a layout-safe wrapping policy needs a
  small density-aware adjustment
- `project.md` if the header behavior description needs clarification
- `sdd/history/`

This task should not:

- redesign the entire `standard` layout;
- move header links into a separate section by default;
- change the candidate data model;
- hide visible link destinations;
- convert header links into icon-only presentation;
- solve unrelated header spacing issues unless they are a direct consequence of
  the wrapping fix.

## Problem Definition
Current undesired behavior:

```text
LinkedIn:
linkedin.com/in/example
```

Target behavior when a break is needed:

```text
LinkedIn: linkedin.com/in/example
```

or:

```text
GitHub: github.com/example   <fits on current line>
<next line starts>
Portfolio: example.dev
```

The core rule is consistency:
- breaks may occur between header items;
- breaks must not occur between a link label and its visible URL.

## Required Behavior

### 1. Atomic header link items
Each rendered header link item should behave as a single unbreakable unit for
line-wrapping purposes whenever practical.

Examples:

- acceptable: `LinkedIn: linkedin.com/in/example`
- acceptable after line wrap: next line begins with `LinkedIn: linkedin.com/in/example`
- not acceptable: `LinkedIn:` followed by a line break before the visible URL

This applies to all `personal.links` rendered in the header.

### 2. Preserve visible labeled URL form
The header must continue to expose links in a visible labeled form such as:

```text
LinkedIn: linkedin.com/in/example
GitHub: github.com/example
Portfolio: example.dev
```

Do not replace the visible destination with generic text like `Profile`, `Open`,
or icon-only affordances.

### 3. Prefer line breaks between items, not within items
When multiple header links compete for width, the layout should prefer:

- keeping each link item intact;
- wrapping before the next link item;
- producing multiple controlled header lines if needed.

It should not prioritize keeping all links on one physical line at the cost of
splitting `Label:` from `visible-url`.

### 4. Contact block stability
The fix must preserve readable interaction between:

- email
- phone
- location
- header links

If the implementation requires the contact block to become a more explicitly
multi-line structure, that is acceptable as long as:

- ATS-safe extraction remains intact;
- reading order remains sensible;
- visible URLs remain present;
- the layout remains compact and professional.

### 5. URL display consistency
The visible URL formatting should remain aligned with current project behavior,
including cleaned display text such as removing `https://` where already done by
`_clean_url()`.

This task is about wrapping behavior, not changing URL normalization rules.

## Recommended Implementation Direction
The exact implementation is up to the implementing agent, but the fix should be
based on a layout mechanism that treats each header link item as a unit.

Acceptable approaches may include:

- wrapping each `Label: \href{...}{visible-url}` item in a non-breaking box;
- using a controlled tabular/parbox/minipage-style header link container;
- replacing `\hfill`-based free inline distribution with a more explicit
  multi-line item layout;
- introducing a header-specific helper macro that preserves unit integrity.

The preferred outcome is robust behavior, not minimal diff size.

Implementation should avoid brittle spacing hacks that only work for one sample
candidate.

## ATS-Safety Requirements
The wrapping fix must preserve the project’s ATS-safety constraints:

- visible URLs remain recoverable in extracted text;
- labels remain visible and associated with their URLs;
- no hidden-link-only behavior;
- no Type 3 fonts;
- no icon-garbage regressions in extracted contact lines;
- sensible reading order in `pdftotext` output.

The task is not complete if the PDF looks better visually but extracted text
loses labels, URLs, or ordering clarity.

## Verification
Minimum verification should include both visual and extracted-text checks.

### Source-mode generation

```bash
./curriculum-gen-dev pdf generate data/candidate.json --output /tmp/header-wrap-standard.pdf --density compact --locale en
./curriculum-gen-dev pdf check /tmp/header-wrap-standard.pdf
pdftotext /tmp/header-wrap-standard.pdf -
pdftoppm -png /tmp/header-wrap-standard.pdf /tmp/header-wrap-standard
```

### Stress fixture verification
The implementing agent should also verify with a candidate fixture that makes
header wrapping likely, for example:

- 3 or more header links;
- long labels;
- long visible URLs;
- localized labels if relevant.

Suggested verification flow:

```bash
./curriculum-gen-dev pdf generate <stress-candidate.json> --output /tmp/header-wrap-stress.pdf --density compact --locale en
./curriculum-gen-dev pdf check /tmp/header-wrap-stress.pdf
pdftotext /tmp/header-wrap-stress.pdf -
pdftoppm -png /tmp/header-wrap-stress.pdf /tmp/header-wrap-stress
```

### Packaged verification

```bash
.venv/bin/python build.py
./curriculum-gen pdf generate data/candidate.json --output /tmp/header-wrap-standard-packaged.pdf --density compact --locale en
./curriculum-gen pdf check /tmp/header-wrap-standard-packaged.pdf
```

## Expected Verification Outcomes
The implementing agent should confirm:

1. no header link appears visually as `Label:` on one line and URL on the next;
2. line breaks occur between whole link items when wrapping is necessary;
3. extracted text still contains visible labeled URLs;
4. PDF ATS checks still pass;
5. packaged binary preserves the same behavior.

## Acceptance Criteria
1. Header links in the `standard` layout no longer break as `Label:` followed by
   URL on the next line.
2. If a header link must wrap, the full `Label: visible-url` item moves to the
   next line as a unit whenever practical.
3. Visible labeled URLs remain present in the rendered PDF and extracted text.
4. The fix does not regress ATS safety.
5. The fix is verified in source mode and packaged mode.
6. A history entry records the implementation, tradeoffs, and verification.

## Notes For The Implementing Agent
- Read the current header/link rendering path in `src/curriculum_gen/generator.py`
  before changing template behavior.
- Treat this as a header composition problem, not a data-model problem.
- Prefer predictable multi-line layout over aggressive one-line compression.
- Verify with a deliberately crowded header, not only with the default sample.
