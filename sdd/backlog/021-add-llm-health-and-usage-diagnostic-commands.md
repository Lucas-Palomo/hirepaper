# 021 - Add `llm health` and `llm usage` diagnostic commands

## Status
Completed

## Context
Task 020 introduced the first LiteLLM Proxy integration path for the CLI through:
- `content match`
- `content tailor`

In that phase, the commands are intentionally limited to a hello-world connectivity test driven by a required JSON config file.

That gave the project an initial LLM transport path, but it still leaves an operational gap.

Today, there is no dedicated CLI surface to answer basic diagnostic questions such as:
- Is the configured LiteLLM Proxy reachable right now?
- Is the configured LLM path healthy enough to accept requests?
- How many tokens did a diagnostic request consume?
- Can an operator inspect lightweight LLM usage without invoking a content-domain command?

Those are infrastructure and observability concerns, not resume-domain concerns.

They should not be hidden inside `content match` / `content tailor` because those commands represent user-facing content workflows, not infrastructure diagnostics.

The CLI should therefore gain a dedicated `llm` command group for operational checks.

## Goal
Introduce a top-level `llm` command group with two diagnostic subcommands:

```bash
curriculum-gen llm health --config <config.json>
curriculum-gen llm usage --config <config.json>
```

These commands are not resume-analysis features.

They exist only to inspect the operational state of the configured LLM integration.

## Product Decision
The `llm` command group is infrastructure-facing.

It must be used for:
- health diagnostics;
- token-usage diagnostics;
- future LLM operational tooling if needed.

It must not absorb domain workflows such as:
- `content match`
- `content tailor`

Those remain under `content` even though they depend on the LLM layer internally.

## Scope Boundary
This task is specifically about adding two diagnostic commands.

It must not:
- move `content match` into `llm`;
- move `content tailor` into `llm`;
- implement real vacancy matching;
- implement real resume tailoring;
- add provider-specific configuration discovery through environment variables;
- redesign the config schema beyond what is strictly needed for these diagnostic commands;
- implement a full metrics dashboard;
- implement historical usage persistence inside the CLI;
- introduce billing or budget management flows.

This task is about lightweight diagnostics only.

## Command Surface
This task must add a new top-level command group:

```bash
curriculum-gen llm
```

With the following subcommands:

```bash
curriculum-gen llm health --config <config.json>
curriculum-gen llm usage --config <config.json>
```

## Required Configuration Policy
Both commands must follow the same explicit configuration policy established in task 020.

Required policy:
1. `--config` is mandatory.
2. Configuration must be loaded only from the provided JSON file.
3. No provider-specific environment variable fallback is allowed.
4. No hidden credential lookup is allowed.
5. Missing config must fail clearly with non-zero exit status.

This keeps LLM diagnostics explicit and reproducible.

## Relationship With Task 020
Task 020 established:
- a JSON config contract;
- a LiteLLM-based client path;
- strict `--config` usage;
- a hello-world request path.

Task 021 should reuse that foundation rather than reinvent it.

Preferred implementation direction:
- reuse the task-020 config loader;
- reuse or extend the existing LLM client module;
- preserve lazy import behavior so help and unrelated commands stay clean in offline environments.

This task should not duplicate LLM config parsing in a second code path.

## `llm health` Goal
`llm health` is an operational reachability and readiness check.

It should answer:
- can the configured proxy endpoint be contacted?
- can the configured model path complete a minimal request?
- if not, what failed?

This command is intended to diagnose whether the configured LLM route is usable.

## `llm health` Required Behavior
The command must:
- require `--config`;
- load the config through the shared config loader;
- perform a lightweight health diagnostic against the configured LiteLLM path;
- report success or failure clearly;
- exit `0` on success and non-zero on failure.

### Acceptable implementation strategies
Because LiteLLM deployments differ, the implementing agent may choose either of these approaches:

#### Preferred approach
Use a direct proxy health/readiness endpoint if the configured LiteLLM deployment exposes one and the command can do so reliably.

Examples may include:
- proxy health endpoint;
- a lightweight readiness endpoint;
- another documented low-cost diagnostic path.

#### Acceptable fallback approach
If relying on a dedicated health endpoint is not sufficiently portable for the current setup, the command may perform a minimal diagnostic completion request using the configured model and treat a valid response as health success.

If the fallback approach is used, the output must state clearly that health was inferred from a successful minimal request, not from a dedicated proxy health endpoint.

Required wording principle:
- the command must not imply that a dedicated proxy health endpoint was checked if the implementation actually used only a minimal completion request;
- the output must clearly distinguish between `proxy health endpoint responded` and `health inferred from successful minimal completion request`;
- avoid diagnostic wording that overclaims what was measured.

### Output expectations
Example shape:

```text
LLM health check
Model: openai/gpt-4.1-mini
Endpoint: http://localhost:4000/v1

[OK] Proxy reachable
[OK] Minimal completion request succeeded
Result: HEALTHY
```

Or, if a dedicated health endpoint is used:

```text
LLM health check
Endpoint: http://localhost:4000/v1

[OK] Proxy health endpoint responded
Result: HEALTHY
```

Equivalent wording is acceptable as long as the command is explicit about what was actually checked.

## `llm usage` Goal
`llm usage` is a token-consumption diagnostic.

It should answer:
- how many prompt tokens were used in a small diagnostic request?
- how many completion tokens were used?
- what was the total token count?

This command is not intended to show historical account usage or billing totals unless the configured proxy exposes that data cleanly and the implementing agent can support it without broadening scope.

For this task, per-request token usage from a diagnostic request is sufficient and preferred.

## `llm usage` Required Behavior
The command must:
- require `--config`;
- load the config through the shared config loader;
- send a minimal diagnostic request through LiteLLM;
- read the returned usage block;
- print token counts clearly;
- exit `0` on success and non-zero on failure.

Minimum required token fields to report when available:
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`

If the provider/proxy returns a richer usage structure, the command may ignore extra fields in this first version.

## Required Usage Semantics
The command must be honest about what it is reporting.

It must not claim to show:
- cumulative account usage;
- monthly totals;
- team/project spend;
- historical dashboard metrics;

unless that is actually what was implemented.

The expected first version is:
- usage for one deterministic diagnostic request executed at command runtime.

Example output shape:

```text
LLM usage diagnostic
Model: openai/gpt-4.1-mini
Endpoint: http://localhost:4000/v1

Prompt tokens: 18
Completion tokens: 9
Total tokens: 27
```

Equivalent wording is acceptable.

## Prompt Policy For Diagnostic Commands
These commands should use deterministic, low-risk prompts.

Recommended principles:
- keep prompts short;
- avoid long completions;
- avoid prompts that materially increase token cost;
- keep outputs stable enough for diagnostics.

Example acceptable prompt intent:
- system: `You are a diagnostic assistant for curriculum-gen.`
- user: `Reply with a short confirmation.`

The agent may reuse the hello-world prompt from task 020 if that keeps behavior consistent.

## Error Handling Requirements
The implementing agent must provide clear errors for these cases:

### 1. Missing config flag
Example intent:

```text
Error: --config is required for 'llm health'
```

and

```text
Error: --config is required for 'llm usage'
```

### 2. Invalid or missing config file
These commands must preserve the same config-validation behavior established in task 020.

### 3. Request failure
Example intent:

```text
Error: LLM request failed: <proxy/provider error>
```

### 4. Health data unavailable
If a dedicated health endpoint is expected but cannot be interpreted:

```text
Error: unable to determine LLM health from proxy response
```

### 5. Usage data unavailable
If the request succeeds but the response has no usable token-usage block:

```text
Error: model returned no usable usage information
```

Errors must remain operationally useful.

## Import and Startup Behavior
This task must preserve the import-discipline requirement introduced by the updated task-020 spec.

Required behavior:
- `curriculum-gen --help` must not trigger LiteLLM startup warnings;
- `curriculum-gen llm --help` must not trigger LiteLLM startup warnings;
- `curriculum-gen llm health --help` and `curriculum-gen llm usage --help` must not trigger LiteLLM startup warnings;
- non-LLM commands must remain independent of LiteLLM import-time side effects.

The implementing agent should continue using lazy imports or another equivalent mechanism.

### Runtime output discipline
The command implementation should keep normal runtime output operationally clean.

Required behavior:
- normal command execution should not dump unrelated LiteLLM startup/help banners around the CLI's own diagnostic output;
- common request failures should be surfaced primarily through the CLI's own error messages;
- if LiteLLM emits noisy auxiliary stderr output by default, the implementing agent should suppress, redirect, or normalize it where practical without hiding the core failure reason.

The goal is not to hide meaningful diagnostic details. The goal is to ensure the CLI remains the authoritative presenter of operational results.

## Recommended Implementation Direction
The implementing agent should add a top-level Typer group such as:
- `llm_app`

Possible internal structure:
- `src/curriculum_gen/llm/config.py` — reused from task 020
- `src/curriculum_gen/llm/client.py` — extend with health/usage helpers
- `src/curriculum_gen/llm/diagnostics.py` — optional, if it keeps responsibilities clearer

Possible helper functions:
- `check_health(config)`
- `get_usage(config)`

The exact file layout can vary, but the implementation should avoid mixing raw request logic directly into CLI command functions.

## Required Response Handling Discipline
The implementation must not assume LiteLLM always returns a plain Python `dict`.

It must correctly handle LiteLLM's standard non-streaming response interface when extracting:
- assistant text for request-success diagnostics;
- usage data from the response.

This task is not complete if a successful LiteLLM response is rejected due to incorrect runtime-type assumptions.

## Documentation Expectations
This task should update `project.md` so the CLI structure reflects the new diagnostic group.

At minimum, documentation should include:
- `curriculum-gen llm health --config <json>`
- `curriculum-gen llm usage --config <json>`
- a short explanation that these are operational diagnostics for the configured LLM provider path.

The documentation must not imply that these commands expose historical billing dashboards if they only report per-request diagnostics.

## Acceptance Criteria
This task is complete only if all of the following are true:

1. A new top-level `llm` command group exists.
2. `curriculum-gen llm health --config <json>` exists.
3. `curriculum-gen llm usage --config <json>` exists.
4. Both commands require `--config` and fail clearly without it.
5. Both commands reuse the explicit JSON configuration policy from task 020.
6. `llm health` reports a clear healthy/unhealthy result based on a real diagnostic check.
7. `llm usage` reports token usage for a deterministic diagnostic request.
8. `llm usage` prints at least prompt, completion, and total token counts when available.
9. Both commands fail clearly when config loading fails.
10. Both commands fail clearly when the LLM/proxy request fails.
11. `llm usage` fails clearly if no usable usage information is returned.
12. The implementation does not assume LiteLLM responses are always raw `dict` objects.
13. Help output for top-level and `llm` commands does not emit LiteLLM startup/network warnings before help text.
14. When `llm health` uses a minimal completion request instead of a dedicated health endpoint, the output states explicitly that health was inferred from request success.
15. Normal runtime failures do not dump unrelated LiteLLM banners or help noise around the CLI's own diagnostic error output unless such output is unavoidable and explicitly documented.
16. `project.md` reflects the new `llm` diagnostic command group honestly.

## Suggested Verification
The implementing agent should verify at least the following cases.

### Help surface
```bash
curriculum-gen --help
curriculum-gen llm --help
curriculum-gen llm health --help
curriculum-gen llm usage --help
```

Expected:
- help renders successfully;
- no LiteLLM startup/network warning is printed before help text.

### Missing config
```bash
curriculum-gen llm health
curriculum-gen llm usage
```

Expected:
- non-zero exit;
- explicit error that `--config` is required.

### Missing config file
```bash
curriculum-gen llm health --config missing.json
curriculum-gen llm usage --config missing.json
```

Expected:
- non-zero exit;
- explicit file-not-found error.

### Invalid JSON
```bash
printf '{bad json' > /tmp/bad-config.json
curriculum-gen llm health --config /tmp/bad-config.json
curriculum-gen llm usage --config /tmp/bad-config.json
```

Expected:
- non-zero exit;
- explicit invalid-config error.

### Valid config against working LiteLLM path
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
curriculum-gen llm health --config config.json
curriculum-gen llm usage --config config.json
```

Expected for `llm health`:
- command prints what kind of health check was performed;
- if health was inferred from a minimal completion request, the output says so explicitly;
- success path exits `0`;
- failure path exits non-zero with explicit diagnostics.

Expected for `llm usage`:
- command prints prompt, completion, and total token counts when returned;
- success path exits `0`;
- missing-usage path exits non-zero with explicit diagnostics.

Expected runtime output discipline for both commands:
- the CLI's own diagnostic output remains readable and primary;
- failing runs do not print unrelated LiteLLM banners/help text around the command output unless that behavior cannot be suppressed and is documented as a known limitation.

## Relationship With Future Tasks
This task should make later LLM work easier by giving operators a clean way to validate the LLM path independently from content workflows.

It should support future work such as:
- real `content match` implementation;
- real `content tailor` implementation;
- richer usage reporting;
- optional proxy-health specialization;
- future LLM diagnostics.

But it must not absorb those scopes now.

## Notes For The Implementing Agent
- Keep these commands diagnostic and honest.
- Prefer explicit operational output over abstract phrasing.
- Do not present per-request usage as account-level usage.
- Preserve the domain/infrastructure separation in the CLI.
- Keep LiteLLM imports lazy and response parsing robust.
