# 034 — Remove `credential_url` from certification contract

**Date:** 2026-06-08
**Agent:** opencode (deepseek-v4-flash)

---

## Context
Certification verification URLs created visual noise in the compact certifications section and degraded extraction clarity. The field was removed from the canonical candidate contract.

## Changes
- **`models.py`**: Removed `credential_url` from `Certification` dataclass.
- **`loader.py`**: Removed `credential_url=c.get("credential_url")`.
- **`generator.py`**: Simplified `_render_certifications` — no longer appends credential URL.
- **`candidate.schema.json`**: Removed `credential_url` from certification `$defs`.
- **`content_tailor.py`**: Removed `credential_url` from LLM payload and conversion path.
- **`assets/prompts/content-tailor-default.txt`**: Removed `credential_url` from fixed fields.
- **Fixtures**: Removed `credential_url` from `data/candidate.json`, `data/candidate-test.json`, `data/example.json`, `assets/examples/candidate.example.json`.

## Verification
```bash
./curriculum-gen-dev content lint data/candidate.json       # PASS
./curriculum-gen-dev pdf generate data/candidate.json --output /tmp/certifications-clean.pdf --density compact --locale en
./curriculum-gen-dev pdf check /tmp/certifications-clean.pdf  # PASS (15 checks)
```

Certifications extracted text no longer contains URLs:
```
AWS Solutions Architect – Associate
Amazon Web Services
Jun 2023
```

All changes verified in source and packaged mode.
