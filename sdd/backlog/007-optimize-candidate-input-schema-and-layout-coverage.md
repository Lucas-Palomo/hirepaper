# 007 - Optimize candidate input schema and layout coverage

## Status
Completed

## Context
The current project already supports the basic resume pipeline and a usable candidate schema, but the input model is still narrow for real-world resume authoring.

Today, the schema supports:
- `personal`
- `target_role`
- `summary`
- `experience`
- `education`
- `skills`
- `projects`
- `certifications`
- `languages`

This is enough for a first resume, but several high-value candidate data points are still missing from both the JSON schema and the LaTeX layout.

The goal of this task is not to add fields blindly. It is to expand the input model where the added information improves resume quality, targeting, and completeness.

## Goal
Evolve the candidate input structure and resume layout so the generator can represent more realistic professional profiles without making the schema noisy or overly abstract.

## Current Observations
Based on the current implementation:
- `personal` is limited to `name`, `email`, `phone`, `location`, and labeled links;
- `experience` supports company, role, location, dates, and highlights, but no tech stack, employment type, promotions, or role summary;
- `education` is minimal and cannot represent honors, coursework, or status cleanly;
- `projects` lacks dates and role context;
- `certifications` lacks credential metadata such as ID or expiration;
- there is no support for awards, publications, volunteer work, or professional profile metadata;
- the layout can render sections and repeated entries cleanly, but currently exposes only the fields already modeled.

## Task Intent
This task should identify which fields are worth adding now, define a practical next-version schema, and update the layout/generator to support those additions coherently.

The task should prefer:
- fields with strong resume value;
- fields that are common across technical candidates;
- additions that are easy to validate and render clearly;
- schema evolution that stays explicit and maintainable.

## Recommended Schema Additions
The implementing agent should evaluate and prioritize the following field additions.

### 1. `personal` enhancements
Recommended additions:
- `headline`: short professional title below or near the candidate name;
- `website`: canonical personal website when it should be treated separately from generic links;
- `github`: optional dedicated field if the project wants first-class handling for common developer profiles;
- `linkedin`: optional dedicated field for the same reason;
- `citizenship` or `work_authorization`: useful for some job markets, but should remain optional;
- `remote_preference`: optional, only if the project intends to support job-targeting metadata in the resume output.

Notes:
- avoid adding too many one-off profile fields unless they clearly improve rendering or targeting;
- if dedicated fields such as `github` or `linkedin` are added, decide whether they replace or complement generic `links`.

### 2. `summary` / profile evolution
Recommended additions:
- `summary_highlights`: optional short bullets or keywords for compact top-of-resume emphasis;
- `years_of_experience`: optional structured value if the project wants deterministic summary building later.

Notes:
- avoid auto-generating summary claims unless they are grounded in data;
- keep summary support compatible with both manually written and structured profile data.

### 3. `experience` enhancements
Recommended additions:
- `employment_type`: e.g. full-time, contract, internship;
- `technologies`: explicit stack used in the role;
- `scope`: optional description of product, system, domain, or business area;
- `achievements`: optional structured bullets distinct from generic highlights if the model needs stronger semantic separation;
- `company_description`: short context line for lesser-known companies;
- `team_size`: optional;
- `promotion_track`: optional way to represent multiple roles at the same company;
- `role_summary`: short one-line context before highlights;
- `remote`: boolean or mode indicator when relevant;
- `company_url`: optional, if the layout should eventually link employers.

Notes:
- `technologies` is one of the highest-value additions because it improves both ATS relevance and human scanning;
- `promotion_track` should only be added if the project is ready to represent multi-role history cleanly.
- `achievements` should be treated as a strong candidate for structured resume content, especially when the input can follow a STAR-like model.

### 3.1 Structured achievement model for experience
The current `highlights` field is simple, but it limits how much the generator can improve phrasing, compression, and layout adaptation.

The task should evaluate introducing structured experience achievements using a STAR-like model.

Recommended structure:
- `achievements[].situation`
- `achievements[].task`
- `achievements[].action`
- `achievements[].result`
- `achievements[].metrics` (optional)
- `achievements[].summary` (optional fallback or hand-written version)

Purpose:
- preserve richer source detail from the candidate;
- allow the generator to produce concise bullets from structured input;
- support future variation between compact and fuller rendering styles without losing information fidelity.

Important:
- `highlights` should remain supported for backward compatibility;
- `achievements` should become the preferred richer structure where available;
- the generator should be able to render both models safely.

Layout constraint:
- the structured data must still adapt to the current layout;
- the current layout should continue rendering concise bullet points, not full multi-paragraph STAR blocks;
- the generator should compress STAR-like fields into compact ATS-friendly bullets appropriate to the existing template.

### 4. `education` enhancements
Recommended additions:
- `status`: completed, in-progress, paused, etc.;
- `honors`: dean's list, summa cum laude, distinction, etc.;
- `coursework`: optional selected coursework;
- `thesis`: optional;
- `activities`: optional student orgs or leadership;
- `graduation_date` if the project later wants a more explicit distinction from generic `end_date`.

Notes:
- `honors` is a strong low-risk addition;
- `coursework` should stay optional and should not bloat the layout.

### 5. `skills` enhancements
Recommended additions:
- `level` per skill or per category item, only if there is a clear rendering strategy;
- `group_order` or explicit ordering controls;
- `featured` skills for top-priority emphasis.

Notes:
- be careful with numeric skill ratings or progress bars; they often weaken resume credibility;
- prefer explicit grouping and ordering over gimmicky scoring.

### 6. `projects` enhancements
Recommended additions:
- `role`: what the candidate did in the project;
- `start_date`
- `end_date`
- `status`: active, completed, archived;
- `highlights`: project bullet points instead of a single description blob;
- `achievements`: optional structured accomplishments using the same STAR-like direction as experience when useful;
- `repository_url`: distinct from live URL;
- `impact`: measurable result if known.

Notes:
- `highlights` is a strong addition because it aligns project rendering with experience rendering;
- separate `repository_url` and `url` is useful for technical portfolios.
- project achievements should also remain compact enough to fit the current layout.

### 7. `certifications` enhancements
Recommended additions:
- `credential_id`
- `credential_url`
- `expires_at`
- `status`

Notes:
- expiration support is useful for certifications that lose validity;
- URLs can improve traceability if the layout chooses to expose them.

### 8. `languages` enhancements
Recommended additions:
- `level_code`: e.g. `C2`, `B1`;
- `notes`: optional clarifier such as business, conversational, native.

Notes:
- keep rendering concise; language sections should stay compact.

### 9. New optional sections worth supporting
High-value candidates for new top-level sections:
- `awards`
- `publications`
- `volunteer_experience`
- `open_source`
- `talks`
- `patents`

Priority recommendation:
1. `awards`
2. `volunteer_experience`
3. `publications` or `open_source`, depending on target audience

Notes:
- not all of these should be implemented at once;
- prefer sections that fit technical candidate profiles and are easy to render elegantly.

## Recommended Layout Changes
The schema evolution should be matched by layout improvements where the new data is worth showing.

### 1. Header improvements
Possible additions:
- optional professional headline under the name;
- clearer separation between core contact info and profile links;
- tighter control over line wrapping when many links exist.

### 2. Experience entry improvements
Possible additions:
- optional secondary line for role summary;
- optional inline technology stack line;
- support for multiple roles under one company if `promotion_track` is introduced.

Important:
- these additions must fit the current layout model based on compact entry blocks plus bullet lists;
- avoid turning each experience into a visually heavy card or multi-paragraph section;
- prefer one extra compact metadata line at most before the bullet list when needed.

### 3. Project rendering improvements
Possible additions:
- support for project dates;
- support for multiple URLs, especially live URL vs repository URL;
- optional project highlights list instead of only paragraph description.

Important:
- project rendering should remain visually lighter than experience unless a clear reason exists;
- if STAR-like project achievements are added, they should be rendered as compact bullets, not as verbose narrative sections.

### 4. Education rendering improvements
Possible additions:
- honors appended cleanly;
- optional coursework or thesis as subordinate lines;
- support for in-progress status.

### 5. New compact sections
The current class already supports compact single-line entries well.

That makes it suitable for adding compact sections such as:
- awards;
- certifications with richer metadata;
- talks;
- publications.

## Recommended Prioritization
The implementing agent should not try to expand every section at once.

Recommended order:
1. Add high-value fields to existing sections:
   - `personal.headline`
   - `experience.technologies`
   - `experience.role_summary`
   - `experience.scope`
   - `experience.achievements[]`
   - `projects.role`
   - `projects.start_date` / `projects.end_date`
   - `projects.highlights`
   - `projects.achievements[]`
   - `education.honors`
   - `certifications.credential_url`
2. Add one or two new top-level sections only if they clearly fit the sample candidate and layout:
   - `awards`
   - `volunteer_experience`
3. Revisit more specialized sections later:
   - `publications`
   - `talks`
   - `patents`

## Constraints
- Keep the schema explicit.
- Avoid over-engineering the model into a highly generic document system.
- Do not add decorative layout features that reduce ATS readability.
- Keep new fields optional unless there is a strong reason to require them.
- Prefer additions that improve technical resume quality materially.
- New structured fields must adapt to the current layout instead of assuming a brand-new layout system.
- Structured STAR-like content should be compressed into concise output appropriate for the current resume template.

## Acceptance Criteria
The task should be considered complete only if:

1. A revised schema proposal is defined clearly.
2. Each new field has a documented purpose.
3. The generator/model/loader are updated for the selected additions.
4. The LaTeX layout is updated only where the new fields are actually worth rendering.
5. Sample data is updated to demonstrate the new fields.
6. The added complexity remains proportional to the project's scope.

## Suggested Verification
The implementing agent should verify:
- sample JSON using the new fields parses correctly;
- omitted optional fields do not break generation;
- the generated PDF remains readable and ATS-friendly;
- new sections or sub-lines do not bloat the layout excessively.

## Notes For The Implementing Agent
- This task is about improving candidate expressiveness, not inventing profile data.
- Strong preference should be given to fields that help technical resumes communicate scope, stack, impact, and credibility.
- `experience.technologies`, `experience.achievements[]`, `projects.highlights`, and `personal.headline` are likely the highest-value additions for the next iteration.
- Do not assume that richer source data means more verbose PDF output. The current layout should remain compact, and the generator should do the work of condensing structured input into readable bullets.
