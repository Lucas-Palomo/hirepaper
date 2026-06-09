# 003 - Add PDF language localization for English and PT-BR

## Status
Completed

## Context
The current pipeline already generates a working PDF resume, but parts of the output still use hardcoded English labels in files such as `generator.py` and `resume.tex`.

The generated PDF must also support Brazilian Portuguese (`pt-BR`).

At this stage, the project only needs to support:
- English (`en`)
- Brazilian Portuguese (`pt-BR`)

Future expansion to additional languages is possible, so the implementation should avoid hardcoding language-specific labels directly in the generator or LaTeX template.

## Goal
Introduce a small localization system for PDF-facing labels and fixed text used during LaTeX generation.

## Scope
Refactor the generation flow so the resume can be rendered in:
- English
- Brazilian Portuguese

The language selection should affect fixed labels in the generated PDF, especially section names and other static UI text emitted by the pipeline.

## Requirements
### 1. Supported languages
The implementation must support exactly these languages for now:
- `en`
- `pt-BR`

Any internal design should keep future language additions possible without forcing a redesign.

### 2. Localization mechanism
Adopt a localization structure that follows Python conventions.

The implementation should prefer established Python i18n patterns over Java-inspired resource handling.

Expected characteristics:
- translation keys are stable and explicit;
- the translation layer is easy to read and maintain;
- the generator resolves labels by locale instead of embedding raw strings directly;
- fallback behavior is defined for missing locale or missing key cases.

Preferred direction:
- use Python-native i18n conventions, such as `gettext`-style organization, if that remains proportionate to the project's size;
- keep the translation mechanism simple enough for the current two-language scope;
- isolate translation lookup from the LaTeX rendering logic.

### 3. Affected content
Localization should cover at least:
- section titles in the PDF;
- fixed labels emitted by `generator.py`;
- fixed labels present in `resume.tex` or the LaTeX class/template layer.

Dynamic candidate content from JSON must not be translated automatically.

### 4. Locale selection
The task should define where the locale comes from.

Acceptable approaches include:
- a field in the input JSON;
- a CLI argument;
- a generator configuration value.

The choice should be documented and kept simple.

## Constraints
- Prefer the Python standard library when it provides a clean solution.
- Do not introduce a large i18n framework for this phase.
- Preserve the current architecture as much as possible.
- Limit official support to `en` and `pt-BR` for now.

## Recommended Direction
Use an approach aligned with normal Python internationalization practices, for example:
- locale-aware message lookup separated from business logic;
- one translation resource set per supported locale;
- a default fallback locale;
- clear normalization between locale identifiers such as `pt-BR` and Python-friendly internal naming where needed.

## Expected Outcome
- the resume PDF can be generated in English and Brazilian Portuguese;
- hardcoded fixed labels are removed from the main generation path;
- localization is organized according to Python conventions so adding another locale later is straightforward.

## Notes
This task is about localizing fixed output text, not translating user-provided resume content.
