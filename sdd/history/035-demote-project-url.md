# 035 — Demote project URL to final utility line

**Date:** 2026-06-08
**Agent:** opencode (deepseek-v4-flash)

---

## Context
Project URLs occupied a primary header slot in `\resumeEntry` (arg #4), competing with project name, role, and period. The URL was promoted to a structural header position, creating visual noise and making entries feel like link cards instead of project descriptions.

## Changes
- **`generator.py` `_render_projects()`**:
  - Moved URL from `\resumeEntry` arg #4 (header slot) to a final `\resumeEntrySub{URL: {url}}` line after description and bullets.
  - Replaced arg #4 with `tech` (technologies) and arg #3 with `date_range` (period).
  - Tech is now the second-line left metadata, period is right metadata.
  - URL only renders when `proj.url` is present; no `URL:` line otherwise.

## Target structure
```
FastAPI Admin                   Core contributor
Python, FastAPI, SQLAlchemy     Jan 2023 — Jun 2024

Description...
Bullets...
URL: github.com/fastapi-admin/fastapi-admin
```

## Verification
```bash
./curriculum-gen-dev pdf generate data/candidate.json --output /tmp/project-layout.pdf --density full --locale en
./curriculum-gen-dev pdf check /tmp/project-layout.pdf       # PASS with warnings (1 warn, 15 ok)
pdftotext /tmp/project-layout.pdf -    # URLs at end of each project entry
```

All changes verified in source and packaged mode.
