# 032 - Add hyperlinked email and structured phone links

**Date:** 2026-06-08
**Agent:** opencode (deepseek-v4-flash)

---

## Context

The project's PDF header rendered email and phone as plain visible text. The PDF exposed the values for human reading and ATS extraction, but did not provide actionable hyperlinks (e.g., `mailto:`, `tel:`, WhatsApp). Additionally, `personal.phone` was a plain string, which did not allow candidates to declare their preferred contact hyperlink — the layout code would have to guess between `tel:` or WhatsApp.

## Changes Made

### 1. Phone data model (`models.py`)

Added a `Phone` dataclass with `value: str` (visible text) and `hyperlink: str` (PDF click target). Changed `Personal.phone` from `str` to `Phone`.

### 2. Phone loader (`loader.py`)

Added `_parse_phone()` that handles both:
- **Canonical form**: `{"value": "+55 11 ...", "hyperlink": "tel:+55..."}` — full object with explicit hyperlink.
- **Legacy string fallback**: plain string `"+55 11 ..."` is accepted transitionally and generates a `tel:` hyperlink by stripping spaces. This is documented as a temporary migration aid.

Fails clearly on missing required `value`/`hyperlink` fields.

### 3. JSON Schema (`assets/schemas/candidate.schema.json`)

Changed `personal.phone` from `"type": "string"` to a `$ref` to a new `$defs/phone` object with required `value` and `hyperlink` (both non-empty strings, no additional properties).

### 4. PDF rendering (`generator.py`)

- **Email**: rendered as `\href{mailto:email}{visible-email}` — clickable with visible text preserved.
- **Phone**: rendered as `\href{phone.hyperlink}{phone.value}` — clickable with visible text preserved.
- **`_render_contact_table()`**: same `\href` wrapping for email and phone in the tabular contact layout.

### 5. LLM content commands (`content_match.py`, `content_tailor.py`)

Updated `p.phone` → `p.phone.value` to send the raw phone string in LLM payloads.

### 6. Fixtures

Updated `data/candidate.json`, `data/example.json`, and `assets/examples/candidate.example.json` to use the new phone object shape:
- `data/candidate.json`: uses `tel:+5511999999999` hyperlink.
- Example fixtures: use `https://wa.me/...` hyperlink.

### 7. Documentation (`project.md`)

Updated source layout section to document the `Phone` model and that generated PDFs embed clickable email and phone hyperlinks.

## Verification

### Loader / lint

```bash
./curriculum-gen-dev content lint data/candidate.json   # PASS with warnings (1 warn, 9 ok)
./curriculum-gen-dev content lint data/example.json     # PASS (placeholder warnings expected)
```

### PDF generation

```bash
./curriculum-gen-dev pdf generate data/candidate.json --output /tmp/contact-hyperlinks.pdf --density compact --locale en
./curriculum-gen-dev pdf check /tmp/contact-hyperlinks.pdf     # PASS (15 checks)
pdftotext /tmp/contact-hyperlinks.pdf -    # Email and phone visible text preserved
exiftool /tmp/contact-hyperlinks.pdf       # Metadata OK
```

### Generated LaTeX hyperlinks

```
\href{mailto:joao.silva@email.com}{joao.silva@email.com}
\href{tel:+5511999999999}{+55 11 99999-9999}
```

### Packaged verification

```bash
.venv/bin/python build.py
./curriculum-gen pdf generate data/candidate.json --output /tmp/contact-hyperlinks-packaged.pdf --density compact --locale en
./curriculum-gen pdf check /tmp/contact-hyperlinks-packaged.pdf   # PASS (15 checks)
```

### Key outcomes

1. Updated fixtures load successfully.
2. `content lint` succeeds on all canonical fixtures.
3. Generated PDFs pass ATS checks with visible email and phone text preserved.
4. Email is wrapped with `mailto:` hyperlink.
5. Phone is wrapped with the configured `tel:` hyperlink.
6. Packaged binary preserves the same behavior.

## Decisions & Tradeoffs

- **Phone as explicit object** rather than inferred behavior — the loader does not guess whether `tel:` or WhatsApp is the right action. The candidate declares it explicitly.
- **Legacy string fallback** in the loader — a plain string `"phone": "+55 11 ..."` is accepted transitionally, generating a `tel:` hyperlink by stripping spaces. This is a migration aid, not the canonical contract. Future consumers should always use the object form.
- **No `mailto:` schema change for email** — email remains a string in the model. The `mailto:` wrapping is a rendering concern handled entirely in `generator.py`.
- **ATS safety preserved** — visible text is unchanged; hyperlinks are added as PDF metadata on the same text, not replacing it.

## Residual Risks

- GUI verification of clickable hyperlinks in a PDF viewer was not performed due to environment limitations. The `\href` wrapping is confirmed in the generated LaTeX source.
- The legacy string fallback in the loader produces a `tel:` link by stripping spaces, which may not produce a valid number for all phone formats. Users are encouraged to migrate to the object form.
