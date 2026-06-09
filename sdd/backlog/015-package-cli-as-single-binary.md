# 015 - Package curriculum-gen as a single binary

## Status
Completed

## Context
The project currently runs as a Python CLI from source, with templates, locale
files, and icon assets loaded from the repository filesystem at runtime.

This is workable for development, but it is not yet convenient to distribute to
non-developer users or to run in environments where cloning the repository and
setting up Python is undesirable.

After task 014, the project has stronger build validation, ATS checks, and more
reliable runtime behavior. The next step is to make the CLI distributable as a
single executable artifact.

## Goal
Produce a single-binary distribution of `curriculum-gen` that preserves current
CLI behavior and can run outside the source tree.

The final result should:
- build a standalone executable for the current platform;
- preserve all current commands (`generate`, `doctor`, `ats-check`);
- bundle the templates, locale files, and icon assets required at runtime;
- resolve asset/template paths correctly when running from the packaged binary;
- clearly document which dependencies remain external to the binary.

## Scope
This task may update:
- `pyproject.toml`
- build scripts or packaging config files
- `src/curriculum_gen/cli.py`
- `src/curriculum_gen/generator.py`
- `src/curriculum_gen/locale.py`
- any runtime path-resolution helpers
- project documentation
- `.gitignore` if build artifacts need to be ignored

This task should not:
- change the CLI interface unless packaging requires a small compatibility fix;
- remove source-based execution;
- change LuaLaTeX as the supported PDF engine;
- bundle a full TeX distribution into the binary unless explicitly justified;
- weaken the validation behavior added in task 014.

## Primary Problems To Address

### 1. Runtime files are source-tree dependent
The CLI currently expects templates, locale files, and icon assets to exist in
known repository-relative paths.

Required behavior:
- packaged execution must still find:
  - `templates/*.tex`
  - `templates/*.cls`
  - `assets/icons/*.svg`
  - `locale/**`
- runtime path resolution must work both:
  - from source checkout;
  - from the packaged executable.

### 2. Packaging strategy must be explicit
The project needs a defined approach for generating a single binary.

Required behavior:
- choose one packaging tool and implement it cleanly;
- the choice should favor pragmatic distribution over novelty;
- the build process should be reproducible from documented commands.

Suggested direction:
- prefer `PyInstaller` unless another tool is clearly better justified for this
  project.

### 3. External dependencies still exist
Even with a single binary, the project still depends on external tools such as:
- `lualatex`
- `rsvg-convert`
- `pdftotext`
- `pdffonts`
- `exiftool`

Required behavior:
- the binary must keep working with task 014 validation rules;
- `doctor` must continue to check these external dependencies;
- documentation must clearly distinguish:
  - what is bundled into the executable;
  - what must still be installed on the host system.

### 4. Packaged execution must preserve CLI behavior
The executable should behave like the existing CLI from the user perspective.

Required behavior:
- `generate` must still render PDFs successfully;
- `doctor` must still validate the environment;
- `ats-check` must still validate generated PDFs;
- help output must still be available and correct.

### 5. Build and smoke-test flow must exist
Packaging is not complete unless the produced binary is actually exercised.

Required behavior:
- define a build command for the executable;
- define a smoke-test command sequence using the built artifact;
- verify that the built executable can:
  - print help;
  - run `doctor`;
  - generate a PDF from `data/candidate.json`;
  - run `ats-check` on that PDF.

## Required Behavior

### Packaging
- produce one standalone executable artifact for the current OS;
- keep the artifact outside tracked source files, e.g. under `dist/`;
- do not require the repo checkout at runtime.

### Runtime assets
- templates, locale files, and icons must be bundled or otherwise made available
  to the packaged executable;
- code must resolve resource paths in a packaging-safe way.

### CLI compatibility
- existing command names and options must continue to work;
- source execution and packaged execution must both remain supported.

### Documentation
- document how to build the binary;
- document where the binary artifact is produced;
- document required host dependencies that are not bundled.

## Acceptance Criteria
1. A documented command builds a single executable for the current platform.
2. The executable runs outside the source module import path.
3. The executable can print `--help`.
4. The executable can run `doctor`.
5. The executable can generate a PDF from `data/candidate.json`.
6. The executable can run `ats-check` on a generated PDF.
7. Templates, locale files, and icon assets are available to the packaged app.
8. Source execution of `./curriculum-gen` continues to work.
9. Documentation clearly lists external host dependencies that remain required.

## Suggested Verification
```bash
# build
<documented build command>

# smoke test packaged executable
./dist/curriculum-gen --help
./dist/curriculum-gen doctor
./dist/curriculum-gen generate data/candidate.json -o output/packaged-resume.pdf --density compact --layout standard-headline-inline --locale en
./dist/curriculum-gen ats-check output/packaged-resume.pdf

# source mode must still work
./curriculum-gen --help
./curriculum-gen doctor
```

The implementing agent should also verify that the packaged executable still
works after being invoked from a directory other than the repository root.

## Notes For The Implementing Agent
- Treat this as a packaging/distribution task, not an excuse to refactor the
  whole runtime layout.
- Keep the runtime resource-loading strategy simple and explicit.
- Prefer a small amount of targeted path-handling code over broad structural
  changes.
- If the chosen packaging tool needs hooks or data-file declarations, keep them
  checked into the repository and documented.
