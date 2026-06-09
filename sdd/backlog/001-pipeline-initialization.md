# 001 - Pipeline Initialization (JSON → LaTeX → PDF)

## Status
Completed

## Context
The `curriculum-gen` project started with no predefined schema, template, or code.
Two instruction files (`sdd/agent.md` and `sdd/agent-context.md`) defined the scope,
constraints, and autonomy for the first iteration.

## Goal
Build the first working version of the JSON → LaTeX → PDF resume generation pipeline.

## Scope
Deliver a complete pipeline from scratch, including:
- a JSON data schema for candidate information;
- a LaTeX class and template for resume layout;
- Python code to parse JSON, validate required fields, and generate LaTeX;
- CLI entry point with PDF compilation support.

## Required Changes
### 1. Project structure
Create directories (`data/`, `templates/`, `src/`, `output/`) and entry point.

### 2. JSON schema
Define explicit top-level fields for personal info, experience, education,
skills, projects, certifications, and languages.

### 3. LaTeX class (`resume.cls`)
Implement a custom document class with ATS-friendly layout, sectioning commands,
and resume-specific macros (`\resumeEntry`, `\resumeSkillCategory`, etc.).

### 4. LaTeX template (`resume.tex`)
Define a template with placeholders (`{NAME}`, `{EXPERIENCE}`, etc.) for the
generator to fill.

### 5. Python data models (`src/models.py`)
Create dataclasses matching the JSON schema.

### 6. JSON loader (`src/loader.py`)
Load and validate JSON input, parse into dataclass instances.

### 7. LaTeX generator (`src/generator.py`)
Transform `Candidate` objects into LaTeX with proper escaping of special characters.

### 8. CLI entry point (`generate.py`)
Accept `--input`, `--output`, `--engine` arguments; copy `.cls` to output directory;
compile PDF via `pdflatex`.

## Constraints
- Use Python standard library only (no external dependencies).
- Output must be ATS-friendly.
- All resume content must be grounded in provided data — no fabrication.
- Layout must be clean, professional, and deterministic.

## Expected Outcome
- `python generate.py` produces valid `.tex` and `.pdf` from sample JSON data.
- Pipeline is reproducible: same input → same output.
- Structure is simple enough to evolve without breaking changes.

## Notes
Full architecture decisions and trade-offs are documented in
`sdd/history/001-pipeline-initialization.md`.
