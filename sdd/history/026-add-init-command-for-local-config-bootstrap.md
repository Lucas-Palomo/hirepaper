# 026 - Add `init` command for local `config.toml` bootstrap

**Date:** 2026-06-05
**Agent:** opencode (deepseek-v4-flash)

---

## Context

The project had a `config_example.toml` at repo root that users had to
discover and copy manually. A dedicated `init` command makes the bootstrap
workflow explicit and self-documenting.

## Changes

### New: `assets/examples/config.example.toml`

The canonical config template now lives under `assets/examples/` instead of
repo root, so it is automatically bundled by PyInstaller (the existing
`build.py` already includes the entire `assets/` tree).

### Modified: `src/curriculum_gen/_resources.py`

Added `config_template_path()` helper that returns the path to the bundled
template, resolving correctly under both source and PyInstaller execution.

### Modified: `src/curriculum_gen/cli.py`

Added top-level `init` command:

- `--output <path>` — destination path (default: `./config.toml`)
- `--force` — overwrite existing file (default: false)

Behavior:
- Writes the bundled template to the destination
- Fails clearly if the destination exists without `--force`
- Creates parent directories as needed (matching other CLI commands)
- Prints a success message explaining env vars are still supported

### Modified: `project.md` and `agents.md`

- Added `curriculum-gen init` to CLI structure and source-layout docs
- Updated `config_example.toml` reference to point to
  `assets/examples/config.example.toml`
- Replaced copy-paste guidance with `init` command recommendation

## Verification

```bash
# Help
./curriculum-gen-dev init --help

# Create new
./curriculum-gen-dev init --output /tmp/cg-init-test.toml
# => Created: /tmp/cg-init-test.toml

# Fail on existing
./curriculum-gen-dev init --output /tmp/cg-init-test.toml
# => Error: config file already exists

# Force overwrite
./curriculum-gen-dev init --output /tmp/cg-init-test.toml --force
# => Created: /tmp/cg-init-test.toml

# Content matches original template
diff assets/config/config.toml.example /tmp/cg-init-test.toml

# Packaged binary
.venv/bin/python build.py
./curriculum-gen init --output /tmp/cg-init-packaged.toml
diff assets/config/config.toml.example /tmp/cg-init-packaged.toml
```

## Decisions and Tradeoffs

- **Template kept in `assets/config/`**: The existing `build.py` already
  bundles `assets/` wholesale, so no packaging changes were needed.
- **No interactive prompts**: The backlog explicitly forbids them; the
  command is entirely argument-driven.

## Residual Risks

- The template content is now centralized under `assets/config/`, so any future
  changes must preserve both source execution and packaged-binary lookup.
