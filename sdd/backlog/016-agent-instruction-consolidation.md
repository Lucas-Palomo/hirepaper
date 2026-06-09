# 016 - Agent instruction consolidation

## Status
Completed

## Context
The project had two older support files, `sdd/agent.md` and
`sdd/agent-context.md`, created during the initial project phase. They still
described the agent as if it were defining the first schema, first layout, and
first implementation from scratch.

That context is now outdated. The project has an established Python CLI,
multiple layouts, density policies, ATS validation, and a packaged binary flow.
Future agents need one canonical instruction file for task execution, plus a
separate technical context file for project-specific details.

The project also now has two root-level entry points:
- `./curriculum-gen-dev`: source-based development and testing entry point;
- `./curriculum-gen`: packaged binary entry point that delegates to
  `dist/curriculum-gen`.

## Goal
Replace the stale agent instruction files with a clearer root-level instruction
structure for future agents.

The final project should:
- use `agents.md` as the canonical agent instruction file;
- use `project.md` for technical project context;
- remove stale instructions from `sdd/agent.md` and `sdd/agent-context.md`;
- document the required task workflow for future agents;
- document the two root-level entry points;
- require agents to rebuild the packaged binary and run focused smoke tests
  after task execution;
- require agents to document completed work and decisions in `sdd/history/`.

## Scope
This task may update:
- `agents.md`
- `project.md`
- `sdd/agent.md`
- `sdd/agent-context.md`
- `sdd/history/`

This task should not:
- change runtime CLI behavior;
- change resume generation behavior;
- change ATS validation behavior;
- change the packaging implementation itself.

## Required Behavior

### Agent instructions
`agents.md` must explain:
- the agent role and mission;
- the required per-task workflow;
- the two root-level entry points;
- build and smoke-test expectations;
- documentation requirements;
- core engineering and resume-content rules.

### Project context
`project.md` must explain:
- current pipeline;
- runtime commands;
- source layout;
- layout variants;
- density policy expectations;
- PDF generation requirements;
- ATS validation expectations;
- packaging behavior;
- backlog/history documentation flow.

### Entry point guidance
The documentation must clearly distinguish:
- `./curriculum-gen-dev` for source-based development testing;
- `./curriculum-gen` for packaged binary testing after build.

### Per-task execution rule
Future agents must be instructed that, after executing a task, they should:
- rebuild the packaged binary;
- run a small smoke test derived from the task scope;
- document development decisions and verification in `sdd/history/`.

## Acceptance Criteria
1. Root-level `agents.md` exists and is the canonical agent instruction file.
2. Root-level `project.md` exists and contains technical project context.
3. `sdd/agent.md` is removed.
4. `sdd/agent-context.md` is removed.
5. Documentation mentions both root entry points:
   - `./curriculum-gen-dev`
   - `./curriculum-gen`
6. Documentation requires a post-task binary build.
7. Documentation requires a post-task smoke test.
8. Documentation requires history documentation for completed work.
9. The packaged binary can be rebuilt after the documentation change.
10. A basic packaged entry point smoke test passes.

## Verification
```bash
./curriculum-gen-dev --help
.venv/bin/python build.py
./curriculum-gen --help
```

## Completion Record
Completed in `sdd/history/016-agent-instruction-consolidation.md`.
