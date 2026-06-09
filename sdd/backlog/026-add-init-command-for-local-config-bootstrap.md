# 026 - Add `init` command for local `config.toml` bootstrap

## Status
Completed

## Context

The project now uses an env-first LLM configuration model with optional TOML
overrides:

- environment variables are the base configuration
- `./config.toml` is an optional local override by convention
- `--config <path>` is an optional explicit TOML override
- the canonical bundled template now lives at `assets/config/config.toml.example`

That model is technically sound, but the onboarding UX is still manual. A user
must discover that a template exists and then copy it into place themselves.

A dedicated `init` command makes that workflow explicit, predictable, and
self-documenting.

## Goal

Add a top-level CLI command that bootstraps a local TOML config file for the
user from the canonical bundled template.

Target outcome:

- a user can run `curriculum-gen init`
- the command writes a local config file from the bundled template
- the command is safe by default and does not overwrite existing files unless
  explicitly requested
- the same command works in source mode and in the packaged binary

## Scope

This task may update:

- `src/curriculum_gen/cli.py`
- `src/curriculum_gen/_resources.py`
- `build.py` or packaging/resource inclusion if needed
- `project.md`
- `agents.md` only if execution guidance needs to mention the new command
- `sdd/history/`

This task may add:

- a config template asset under `assets/`
- helper functions for locating or copying the template
- minimal command-level tests or verification fixtures if the repo already uses
  that pattern

This task should not:

- redesign the LLM config resolution model
- change the semantics of environment-variable loading
- add interactive prompts
- silently overwrite existing files

## Command Surface

Target command:

```bash
curriculum-gen init
```

### Options

- `--output <path>`
  - optional output path
  - default: `./config.toml`
- `--force`
  - overwrite the destination file if it already exists
  - default: false

Optional alias support is not required.

## Template Source

The command must not hardcode the template inline in Python.

The canonical template should live in a bundled asset path, for example:

```text
assets/config/config.toml.example
```

The implementation should load the template from that asset path so the same
source is used by:

- development/source execution
- packaged binary execution
- future documentation references

Use `assets/config/config.toml.example` as the single canonical template source.
Avoid maintaining duplicate copies of the same template.

## Required Behavior

### 1. Default output path

When the user runs:

```bash
curriculum-gen init
```

The command should write:

```text
./config.toml
```

using the bundled template content.

### 2. Existing file protection

If the output file already exists and `--force` is not provided:

- the command must fail clearly
- exit non-zero
- explain that the file already exists
- suggest `--force` or `--output`

Example error style:

```text
Error: config file already exists: ./config.toml
Use --force to overwrite it or --output to choose another path.
```

### 3. Forced overwrite

If `--force` is provided:

- overwrite the output file
- exit zero on success

### 4. Alternate output path

If the user provides `--output`, write to that path instead of `./config.toml`.

The command should create parent directories when reasonable, similar to other
project commands that write files.

### 5. Success output

On success, print a short confirmation that includes:

- where the file was written
- that environment variables are still supported
- that the file acts as a local override

Example:

```text
Created: ./config.toml
This file is an optional TOML override; environment variables are still supported.
```

## Error Handling

The command must fail clearly for:

- template asset missing
- template asset unreadable
- output path unwritable
- output path already exists without `--force`

Do not emit Python tracebacks for expected user errors.

## Resource Handling

Because the command must work in the packaged binary, the template asset must be
included in bundled resources.

This task must verify that:

- the template can be found from source execution
- the template can be found from packaged execution

If `_resources.py` needs a helper such as `config_assets_dir()` or
`config_template_path()`, add it there.

## Documentation Updates

Update `project.md` to include:

- the new `curriculum-gen init` command in the CLI structure
- the purpose of the command
- the location/role of the config template asset if relevant

Update references to point to the canonical asset location or to the `init`
command as the recommended workflow.

## Verification

Minimum verification should include:

```bash
./curriculum-gen-dev init --output /tmp/curriculum-gen-init-test.toml
./curriculum-gen-dev init --output /tmp/curriculum-gen-init-test.toml
./curriculum-gen-dev init --output /tmp/curriculum-gen-init-test.toml --force

.venv/bin/python build.py

./curriculum-gen init --output /tmp/curriculum-gen-init-packaged.toml
```

Expected outcomes:

1. first command creates the file successfully
2. second command fails because the file already exists
3. third command succeeds because `--force` is provided
4. packaged binary also creates the file successfully

If the environment prevents writing to `/tmp`, use another writable path and
document that change in history.

## Acceptance Criteria

1. `curriculum-gen init` exists.
2. By default it writes `./config.toml`.
3. It uses a bundled template asset, not an inline hardcoded string.
4. It refuses to overwrite an existing file unless `--force` is used.
5. It supports `--output <path>`.
6. It works in both source execution and packaged binary execution.
7. Documentation is updated.
8. A history entry records what changed and how it was verified.

## Delivered Notes

The delivered implementation corresponds to this task and currently provides:

- top-level `curriculum-gen init`
- `--output <path>` with default `./config.toml`
- `--force` overwrite support
- clear failure when destination already exists
- parent directory creation before writing
- bundled template lookup through `config_template_path()`
- source and packaged binary support

Delivered implementation references:

- CLI command: `src/curriculum_gen/cli.py`
- resource helper: `src/curriculum_gen/_resources.py`
- canonical template: `assets/config/config.toml.example`
- history entry: `sdd/history/026-add-init-command-for-local-config-bootstrap.md`
