# 002 - Refactor compilation validation and TeX escaping

## Status
Completed

## Context
Task `001` established the first working `JSON -> LaTeX -> PDF` pipeline and verified manual generation.

Two implementation risks remain and should now be addressed as a focused refactor:
- compilation success detection is too permissive if it only checks whether a PDF exists;
- TeX escaping is incomplete for real-world resume input.

## Goal
Strengthen pipeline correctness without changing the project's overall architecture.

## Scope
Refactor the current implementation to:
- make PDF generation success detection reliable for the current execution;
- improve LaTeX text escaping coverage for common problematic characters.

## Required Changes
### 1. Compilation validation
The generation flow should not report success based only on the presence of a PDF file in the output directory.

The refactor should ensure that success reflects the current run, not a stale artifact from a previous run.

Acceptable directions include:
- removing or replacing previous output artifacts before compilation;
- validating modification time or other run-specific evidence;
- combining file existence checks with process result and log inspection.

### 2. TeX escaping
The text escaping function should be reviewed and expanded.

At minimum, the refactor should evaluate support for:
- `\\`
- `~`
- `^`

It should also confirm that already handled characters continue to compile correctly in realistic resume text.

## Constraints
- Keep the solution dependency-free unless a strong reason appears.
- Preserve the current project structure unless a small structural adjustment clearly improves maintainability.
- Avoid broad redesign unrelated to the two issues above.

## Expected Outcome
- the generator fails more honestly when compilation breaks;
- stale PDF artifacts no longer produce false success;
- common special characters in candidate data are handled more safely in LaTeX generation.

## Notes
This task is a refactor and stabilization step after the initial implementation, not a new architecture phase.
