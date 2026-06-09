# 017 - Add content lint for candidate data

**Date:** 2026-05-30 
**Agent:** opencode (deepseek-v4-flash)

## Context
The project had no way to evaluate resume data quality and density before rendering. Input validation in `loader.py` was minimal — it only ensured required fields existed. The backlog item called for a separate content-lint layer focused on structural completeness, density, section balance, and placeholder leakage.

## Changes Made

### New module: `src/curriculum_gen/content_lint.py`
- `LintResult` class — follows the same `[OK]`/`[WARN]`/`[FAIL]` output convention as `ats_check.py`.
- `lint_candidate(candidate: Candidate) -> int` — entry point that runs all checks and returns exit code.
- **Structural completeness** — validates summary, experience/projects, skills, and education presence.
- **Summary density** — word-count check with thresholds (<25 WARN, 25-80 OK, >80 WARN).
- **Experience density** — bullets per role (>5 WARN), word count per bullet (>32 WARN), total bullets (>20 WARN, >18 WARN near limit).
- **Skills density** — items per category (>8->10 WARN), total items (>30->35 WARN).
- **Projects density** — number of projects (>3 WARN), description length (>60->80 WARN), highlights per project (>3 WARN).
- **Education density** — verbose detail check on GPA/honors text.
- **Section balance** — projects vs experience bullet mass, skills-to-experience ratio, total narrative word count.
- **Placeholder leakage** — ~45 regex patterns matching `data/example.json` sample text (Your Name, Company Name, Tech1, etc.).
- **Exit codes** — `0` when no failures, `1` when one or more failures found (warnings alone don't fail).

### Updated: `src/curriculum_gen/cli.py`
- Added `lint_content` command:
  ```bash
  curriculum-gen lint-content <candidate_json>
  ```
- Loads candidate via existing `load_candidate` path.
- Delegates to `lint_candidate()` from the new module.
- Exits consistently with `ats-check` (non-zero on failures).

## Decisions & Tradeoffs
- **Separate module** — Kept lint rules out of `loader.py` as specified. `loader.py` remains focused on schema parsing and validation, not editorial judgment.
- **Counting bullets** — For experience, achievements are counted when present (each achievement = 1 bullet), otherwise highlights. This matches the rendering priority in `generator.py`.
- **Placeholder patterns** — Used `re.compile` patterns for stable matching across structured fields. Patterns cover all obvious sample text from `data/example.json`. Some patterns use `\b` word boundaries to avoid false positives on legitimate text.
- **WARN vs FAIL** — Followed the severity guidance: FAIL for missing structure and placeholder leakage; WARN for density, balance, and editorial concerns.

## Verification

### Dev entry point
```
$ ./curriculum-gen-dev lint-content data/candidate.json
→ PASS with warnings (1 warning(s), 9 ok)
```

```
$ ./curriculum-gen-dev lint-content data/example.json
→ Result: FAIL (1 failure(s), 1 warning(s), 7 ok)
```

### Packaged binary
```
$ ./curriculum-gen lint-content data/candidate.json
→ PASS with warnings (1 warning(s), 9 ok)

$ ./curriculum-gen lint-content data/example.json
→ Exit code: 1
```

## Residual Risks
- **Threshold tuning** — Current thresholds (25/80 words for summary, 5 bullets per role, 32 words per bullet, etc.) are sensible starting points but may need adjustment based on real-world usage.
- **Placeholder patterns** — Some patterns may catch edge-case legitimate text (e.g., "Stack" in a technologies list). Patterns can be refined as users report false positives.
- **Phase 1 only** — This implements the deterministic density checks (Phase 1 in the backlog). Phases 2-4 (editorial heuristics, correlation checks, strict mode) remain as future work.

## Follow-up Items
- Monitor for false-positive placeholder detections and refine patterns.
- Consider adding `--strict` mode and `--json-report` output (Phase 4).
- Consider adding repetition and metric-presence heuristics (Phase 2).
