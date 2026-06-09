# 003 — PDF language localization (en / pt-BR)

**Date:** 2026-05-27
**Agent:** opencode (deepseek-v4-flash)

---

## Context

The pipeline generated all fixed labels in English. The project needed to support
both English and Brazilian Portuguese for section titles, date labels, and other
static UI text emitted during LaTeX generation.

This task was refined to prefer Python-standard i18n practices (`gettext`) over
the initially considered Java `.properties` style.

## Implementation

### 1. Locale system (`src/locale.py`)

Uses Python's standard library `gettext` module with `.po` / `.mo` files:

- **`Locale`** class wraps `gettext.translation()` to load `.mo` files from
  `locale/{lang}/LC_MESSAGES/messages.mo`.
- `pt-BR` is normalized to `pt_BR` internally (gettext convention).
- Fallback chain: requested locale → `en` → `NullTranslations` → key name.
- `locale.get(key)` returns translation or the key itself as fallback.
- `locale.month_abbr(num)` shortcut for month lookups.

### 2. Translation files

```
locale/
├── en/LC_MESSAGES/messages.po   → messages.mo
└── pt_BR/LC_MESSAGES/messages.po → messages.mo
```

22 keys per locale: 7 section titles, 2 labels (`label.present`, `label.gpa`),
12 month abbreviations. Compiled via `msgfmt`.

### 3. Template (`templates/resume.tex`)

Hardcoded section titles replaced with placeholders:
`{SECTION_PROFILE}`, `{SECTION_EXPERIENCE}`, etc.

### 4. Generator (`src/generator.py`)

- `generate_latex()` accepts `locale: Locale | None` parameter.
- Section title placeholders resolved via `locale.get("section.{name}")`.
- `_format_date()` uses `locale.get("label.present")` and `locale.month_abbr()`.
- `_render_education()` uses `locale.get("label.gpa")`.

### 5. CLI (`generate.py`)

Added `--locale {en,pt-BR}` argument (default: `en`).

## Verified Behavior

```
$ python generate.py --locale en      # "Experience", "Present", "Mar"
$ python generate.py --locale pt-BR   # "Experiência", "Atualmente", "mar"
```

Both compile to valid PDF. Dynamic candidate content is not translated.
Adding a new locale requires: creating `.po` → compiling `.mo` → adding to
`--locale` choices.
