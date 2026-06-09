# 020 - Add initial LiteLLM Proxy config

## Status
Completed

## Context
The project already has a clear CLI structure for:
- environment diagnostics;
- candidate-content linting;
- PDF generation;
- PDF validation.

The next product direction is to introduce LLM-backed content workflows for vacancy-specific operations:
- `content match`;
- `content tailor`.

However, this task is intentionally not the full implementation of vacancy matching or resume tailoring.

Before the project can implement real job-description analysis, it needs a small, disciplined integration layer that proves the CLI can:
- load LLM settings from a project-controlled config file;
- refuse execution when no config file is provided;
- talk to a LiteLLM Proxy endpoint;
- send a basic test prompt;
- receive and print the response;
- do this through the future public commands `content match` and `content tailor`.

The goal of this task is to establish the operational contract for LLM-backed commands without prematurely implementing real business logic.

## Goal
Introduce the first LLM integration path for the CLI using a LiteLLM Proxy-compatible endpoint configured exclusively through a JSON config file passed via `--config`.

This task must implement a minimal end-to-end hello-world flow for both:
- `curriculum-gen content match`
- `curriculum-gen content tailor`

In this first phase, both commands are transport/integration smoke tests only.

They must:
- require `--config=<file>`;
- fail clearly if the config file is missing, unreadable, or invalid;
- use the LLM configuration from that file only;
- send a deterministic test prompt to the configured LiteLLM Proxy endpoint;
- print the returned model response;
- exit non-zero on configuration or request failures.

## Non-Goal
This task is not about implementing real matching or tailoring semantics.

It must not:
- analyze the candidate JSON against a vacancy description semantically;
- compute real compatibility scores;
- rewrite summaries, bullets, or skills;
- introduce prompt engineering for production-quality vacancy handling;
- support multiple provider-specific environment variables;
- introduce provider-specific direct integrations in the CLI;
- make the commands depend on ambient `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or similar variables;
- silently fall back to environment-based configuration when `--config` is omitted.

If the implementing agent starts writing real matching/tailoring logic in this task, the scope has drifted.

## Product Decision
For now, LLM access is configured by a JSON file supplied explicitly by the user.

The CLI must not rely on implicit environment discovery for these commands.

The configuration source of truth for this task is:
- `--config=<path to json>`

This decision is deliberate because it:
- keeps the first integration explicit;
- avoids hidden configuration state;
- makes local testing reproducible;
- keeps the command contract simple while the LLM layer is still being validated.

## Required Command Contract
This task must implement or update the following commands:

```bash
curriculum-gen content match ... --config <config.json>
curriculum-gen content tailor ... --config <config.json>
```

Important behavioral rule:
- `--config` is mandatory for both commands.

If the user does not pass `--config`, the command must fail immediately with a clear error message and non-zero exit code.

This is a hard requirement.

## Scope Boundary For CLI Inputs
The long-term product direction still expects these commands to operate on candidate data plus a vacancy description.

But in this task, the implementation focus is the LLM transport path, not the real command semantics.

The implementing agent may choose one of the following CLI shapes for this first phase:

### Preferred shape
Keep the future-oriented command shape now, even if the internal logic is still a hello-world test.

Examples:

```bash
curriculum-gen content match data/candidate.json job.txt --config config.json
curriculum-gen content tailor data/candidate.json job.txt --config config.json
```

Under this preferred shape:
- the commands may accept candidate/job inputs now;
- the first implementation may ignore those inputs for model reasoning purposes;
- but the commands should preserve the intended public interface direction.

### Acceptable fallback shape
If preserving future arguments now creates unnecessary confusion, the commands may temporarily accept only `--config` in this task, provided the help text clearly states that the command is an initial connectivity smoke test.

Examples:

```bash
curriculum-gen content match --config config.json
curriculum-gen content tailor --config config.json
```

Preferred decision:
- keep the future-oriented command surface if practical;
- but do not fake real vacancy processing.

Whichever approach is chosen, it must be documented clearly in help text and in the implementation notes.

## Required Configuration Format
This task must define and implement a JSON configuration file format.

The configuration should stay intentionally small and explicit.

Minimum required fields:

```json
{
  "base_url": "http://localhost:4000/v1",
  "api_key": "your-key-here",
  "model": "openai/gpt-4.1-mini"
}
```

Recommended optional fields:

```json
{
  "temperature": 0.2,
  "timeout_seconds": 60,
  "max_tokens": 256
}
```

### Required semantics
- `base_url`: LiteLLM Proxy-compatible base URL.
- `api_key`: key used for the proxy call.
- `model`: model identifier passed through the OpenAI-compatible request.
- `temperature`: optional; use a conservative default if omitted.
- `timeout_seconds`: optional; use a safe default if omitted.
- `max_tokens`: optional; use a small default if omitted.

### Required validation
The command must fail clearly if:
- the config file does not exist;
- the path is not readable;
- the file is not valid JSON;
- required fields are missing;
- required fields are empty strings;
- numeric values are invalid where provided.

The validation error should identify the bad config path and explain which field or parse step failed.

## Required Configuration Policy
The implementing agent must follow this policy exactly for `content match` and `content tailor`:

1. Configuration must come from `--config`.
2. No config file means command failure.
3. The command must not silently inspect provider-specific environment variables.
4. The command must not silently substitute default credentials.
5. The command must not silently switch to another provider path.

A minimal explicit fallback such as using a default temperature when omitted from the JSON is acceptable.

A fallback to hidden credential sources is not acceptable.

## Integration Requirement
Use LiteLLM as the client abstraction for this first phase.

The task should introduce a small internal module boundary for LLM access so that the CLI commands do not embed raw request logic directly.

Recommended shape:
- config loader module;
- LLM client wrapper module;
- command wiring in `cli.py`.

Possible module placement:
- `src/curriculum_gen/llm/config.py`
- `src/curriculum_gen/llm/client.py`
- `src/curriculum_gen/llm/__init__.py`

The exact file names can vary, but the concerns should stay separated.

### Import and startup behavior
The implementing agent must keep LiteLLM import side effects isolated from unrelated CLI paths.

Required behavior:
- top-level CLI help must not trigger LiteLLM network initialization noise;
- `curriculum-gen content --help` and `curriculum-gen content match --help` must remain usable in offline environments without emitting provider-initialization warnings before help text;
- non-LLM commands such as `doctor`, `content lint`, `pdf generate`, and `pdf check` must not depend on importing LiteLLM at module import time.

Recommended implementation direction:
- defer LiteLLM imports until the command execution path actually needs them;
- avoid importing `litellm` at `cli.py` module load time;
- keep the LLM integration lazy so that only real `content match` / `content tailor` execution touches the LiteLLM runtime.

## Required Hello-World Behavior
This task must prove connectivity with a deterministic, low-risk prompt.

Both commands must send a basic test prompt to the configured model.

Example acceptable prompt intent:
- system: `You are a connectivity test assistant for curriculum-gen.`
- user: `Reply with a short confirmation that the LiteLLM proxy connection works.`

The prompt does not need to mention candidate data or vacancy text in this phase.

The command must then:
- receive the model response;
- print the response text to stdout in a readable way;
- exit `0` if the request succeeds.

The implementation must treat a normal LiteLLM success response as valid even if LiteLLM returns a structured response object rather than a plain Python `dict`.

Required behavior:
- do not assume the non-streaming response is always a raw `dict`;
- support LiteLLM's standard success response shape whether accessed through object attributes, dict-like indexing, or another documented response interface;
- only fail with `model returned no usable text response` when the response truly lacks assistant text content.

The task is not complete if a successful proxy response is incorrectly rejected because the code checked the wrong runtime type.

This is a smoke test, not a product-quality workflow.

## Required Command Messaging
The CLI output should make it obvious that the current behavior is an initial test integration.

Recommended output shape:

```text
LLM connectivity test: content match
Model: openai/gpt-4.1-mini
Endpoint: http://localhost:4000/v1

Response:
LiteLLM proxy connection works.
```

Equivalent wording is acceptable as long as it is explicit and not misleading.

The command must not imply that a real job-match or tailoring analysis was performed.

## Error Handling Requirements
The implementing agent must provide clear errors for these cases:

### 1. Missing config flag
Example intent:

```text
Error: --config is required for 'content match'
```

### 2. Config path not found
Example intent:

```text
Error: config file not found: /path/to/config.json
```

### 3. Invalid JSON
Example intent:

```text
Error: invalid config JSON: /path/to/config.json
```

### 4. Missing required field
Example intent:

```text
Error: invalid config — missing required field 'model'
```

### 5. Request failure
Example intent:

```text
Error: LLM request failed: <provider/proxy error>
```

### 6. Empty or malformed response
Example intent:

```text
Error: model returned no usable text response
```

Errors must be explicit enough for a developer or operator to diagnose configuration problems quickly.

## Dependency Expectations
This task is expected to add LiteLLM as a runtime dependency.

The implementing agent should update the appropriate packaging metadata so the dependency is installed in normal project usage.

At minimum, that likely includes:
- `pyproject.toml`
- and any other project dependency manifest that must stay in sync.

The implementing agent should keep the dependency surface minimal.

This task does not require additional orchestration frameworks.

## Documentation Expectations
This task should update the project documentation so the new behavior is discoverable and honest.

At minimum, update the relevant command descriptions in:
- `project.md`

The documentation should state clearly that:
- `content match` and `content tailor` exist;
- they currently require `--config`;
- they currently perform a hello-world LiteLLM Proxy connectivity test only;
- real vacancy analysis is deferred to a later task.

If a sample config file path or example block is added to documentation, it must match the implemented JSON schema.

## Acceptance Criteria
This task is complete only if all of the following are true:

1. `content match` exists as a public CLI command.
2. `content tailor` exists as a public CLI command.
3. Both commands require `--config=<json file>`.
4. Invoking either command without `--config` fails clearly and exits non-zero.
5. Invoking either command with a missing config path fails clearly and exits non-zero.
6. Invoking either command with invalid JSON config fails clearly and exits non-zero.
7. Invoking either command with missing required config fields fails clearly and exits non-zero.
8. With a valid config, each command sends a basic test prompt through LiteLLM.
9. With a successful model response, each command prints the returned text.
10. The output does not falsely claim that real matching or tailoring has been performed.
11. The implementation does not depend on provider-specific environment variables for these commands.
12. The command help and project docs reflect the temporary hello-world scope honestly.
13. A successful LiteLLM completion response is accepted even when LiteLLM returns its standard response object rather than a plain `dict`.
14. `--help` for top-level and content commands does not emit LiteLLM startup or network warnings before showing help text.

## Suggested Verification
The implementing agent should verify at least the following cases.

### Help surface
```bash
curriculum-gen content --help
curriculum-gen content match --help
curriculum-gen content tailor --help
```

Expected:
- help text renders successfully;
- no LiteLLM startup warning is printed before help output;
- no network-dependent initialization is triggered just to inspect help.

### Missing config
```bash
curriculum-gen content match
curriculum-gen content tailor
```

Expected:
- non-zero exit;
- explicit error that `--config` is required.

### Missing file
```bash
curriculum-gen content match --config missing.json
curriculum-gen content tailor --config missing.json
```

Expected:
- non-zero exit;
- explicit file-not-found error.

### Invalid JSON
```bash
printf '{bad json' > /tmp/bad-config.json
curriculum-gen content match --config /tmp/bad-config.json
```

Expected:
- non-zero exit;
- explicit invalid-JSON error.

### Valid config against working LiteLLM Proxy
Example config:

```json
{
  "base_url": "http://localhost:4000/v1",
  "api_key": "test-key",
  "model": "openai/gpt-4.1-mini",
  "temperature": 0.2,
  "timeout_seconds": 60,
  "max_tokens": 64
}
```

Example commands:

```bash
curriculum-gen content match --config config.json
curriculum-gen content tailor --config config.json
```

Expected:
- request reaches the proxy;
- model response is printed;
- exit code `0`.
- a normal LiteLLM success response object is accepted without being rejected for not being a plain `dict`.

If the implementing agent chooses to preserve candidate/job positional arguments in the first phase, verification should also include those shapes.

## Relationship With Future Tasks
This task is foundational.

It should unblock later tasks that implement real semantics for:
- vacancy compatibility analysis;
- resume tailoring;
- structured LLM outputs;
- config evolution beyond the initial JSON contract.

But this task must not absorb those later scopes.

## Notes For The Implementing Agent
- Keep the first LLM integration small and explicit.
- Do not overdesign a full provider abstraction layer in this task.
- Do not add hidden config discovery.
- Do not pretend the commands are more capable than they are.
- Prefer precise validation and clear failure modes over convenience magic.
- If you introduce internal abstractions, keep them thin and easy to replace when real match/tailor logic lands.
