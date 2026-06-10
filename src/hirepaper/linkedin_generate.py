from __future__ import annotations

import contextlib
import io
import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._resources import prompts_dir, schemas_dir
from .content_lint import lint_candidate
from .loader import load_candidate
from .llm.client import LLMClientError, _complete, _extract_text, _extract_usage
from .llm.config import LLMConfig
from .log_archive import LogArchiveError, StagedLogArchive
from .models import Candidate

_LINKEDIN_SCHEMA_NAME = "linkedin-report.schema.json"


class LinkedInGenerateError(Exception):
    pass


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_linkedin_schema() -> dict:
    path = schemas_dir() / _LINKEDIN_SCHEMA_NAME
    if not path.exists():
        raise LinkedInGenerateError(f"linkedin report schema not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise LinkedInGenerateError(f"linkedin report schema read error: {path} — {e}")
    except json.JSONDecodeError as e:
        raise LinkedInGenerateError(f"invalid linkedin report schema JSON: {path} — {e}")
    return raw


def load_default_linkedin_prompt() -> str:
    path = prompts_dir() / "linkedin-generate-default.txt"
    if not path.exists():
        raise LinkedInGenerateError(f"default linkedin prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def load_prompt(prompt_path: str | None) -> str:
    if prompt_path is not None:
        path = Path(prompt_path)
        if not path.exists():
            raise LinkedInGenerateError(f"prompt file not found: {prompt_path}")
        try:
            return path.read_text(encoding="utf-8")
        except OSError as e:
            raise LinkedInGenerateError(f"prompt file read error: {prompt_path} — {e}")
    return load_default_linkedin_prompt()


def _build_candidate_payload(candidate: Candidate) -> dict:
    payload: dict[str, Any] = {}

    p = candidate.personal
    personal: dict[str, Any] = {
        "name": p.name,
        "headline": p.headline or "",
        "email": p.email,
        "phone": {"value": p.phone.value, "hyperlink": p.phone.hyperlink},
        "location": p.location,
    }
    if p.links:
        personal["links"] = [
            {"label": lnk.label, "url": lnk.url}
            for lnk in p.links
        ]
    if p.extra_links:
        personal["extra_links"] = [
            {"label": lnk.label, "url": lnk.url}
            for lnk in p.extra_links
        ]
    payload["personal"] = personal

    payload["summary"] = candidate.summary
    payload["target_role"] = candidate.target_role or ""

    payload["experience"] = [
        {
            "company": e.company,
            "position": e.position,
            "location": e.location,
            "start_date": e.start_date,
            "end_date": e.end_date,
            "current": e.current,
            "technologies": e.technologies,
            "role_summary": e.role_summary or "",
            "scope": e.scope or "",
            "employment_type": e.employment_type or "",
            "highlights": e.highlights,
            "achievements": [
                {
                    "situation": a.situation or "",
                    "task": a.task or "",
                    "action": a.action or "",
                    "result": a.result or "",
                    "metrics": a.metrics or "",
                    "summary": a.summary or "",
                    "context": (
                        {
                            "action": a.context.action or "",
                            "result": a.context.result or "",
                            "metrics": a.context.metrics or "",
                        }
                        if a.context
                        else None
                    ),
                }
                for a in e.achievements
            ],
        }
        for e in candidate.experience
    ]

    payload["education"] = [
        {
            "institution": e.institution,
            "degree": e.degree,
            "location": e.location,
            "start_date": e.start_date,
            "end_date": e.end_date,
            "gpa": e.gpa or "",
            "honors": e.honors or "",
        }
        for e in candidate.education
    ]

    if candidate.skills and candidate.skills.categories:
        payload["skills"] = {
            "categories": [
                {
                    "name": cat.name,
                    "items": [item for item in cat.items],
                }
                for cat in candidate.skills.categories
            ]
        }
    else:
        payload["skills"] = {"categories": []}

    payload["projects"] = [
        {
            "name": p.name,
            "description": p.description,
            "role": p.role or "",
            "start_date": p.start_date or "",
            "end_date": p.end_date or "",
            "technologies": p.technologies,
            "url": p.url or "",
            "highlights": p.highlights,
        }
        for p in candidate.projects
    ]

    payload["certifications"] = [
        {
            "name": c.name,
            "issuer": c.issuer,
            "date": c.date,
        }
        for c in candidate.certifications
    ]

    payload["awards"] = [
        {
            "name": a.name,
            "issuer": a.issuer,
            "date": a.date,
            "description": a.description or "",
        }
        for a in candidate.awards
    ]

    payload["volunteer"] = [
        {
            "organization": v.organization,
            "position": v.position,
            "location": v.location,
            "start_date": v.start_date,
            "end_date": v.end_date,
            "current": v.current,
            "highlights": v.highlights,
        }
        for v in candidate.volunteer
    ]

    payload["languages"] = [
        {"language": lang.language, "proficiency": lang.proficiency}
        for lang in candidate.languages
    ]

    return payload


def _resolve_schema_ref(root_schema: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        raise LinkedInGenerateError(f"unsupported schema ref: {ref}")
    node: object = root_schema
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            raise LinkedInGenerateError(f"invalid schema ref: {ref}")
        node = node[part]
    if not isinstance(node, dict):
        raise LinkedInGenerateError(f"invalid schema ref target: {ref}")
    return node


def _schema_error(path: list[str], message: str) -> LinkedInGenerateError:
    location = ".".join(path)
    if location:
        return LinkedInGenerateError(f"report does not match schema at '{location}': {message}")
    return LinkedInGenerateError(f"report does not match schema: {message}")


def _matches_schema_type(value: object, schema_type: str) -> bool:
    if schema_type == "object":
        return isinstance(value, dict)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "null":
        return value is None
    return True


def _validate_against_schema(
    value: object,
    schema: dict,
    root_schema: dict,
    path: list[str],
) -> None:
    if "$ref" in schema:
        _validate_against_schema(value, _resolve_schema_ref(root_schema, schema["$ref"]), root_schema, path)
        return

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        if not any(_matches_schema_type(value, item_type) for item_type in schema_type):
            raise _schema_error(path, f"expected one of {schema_type}, got {type(value).__name__}")
        schema_type = next((item_type for item_type in schema_type if _matches_schema_type(value, item_type)), None)

    schema_const = schema.get("const")
    if schema_const is not None and value != schema_const:
        raise _schema_error(path, f"value {value!r} does not match const {schema_const!r}")

    if schema_type == "object":
        if not isinstance(value, dict):
            raise _schema_error(path, f"expected object, got {type(value).__name__}")

        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise _schema_error(path + [key], "missing required property")

        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra_keys = sorted(set(value.keys()) - set(properties.keys()))
            if extra_keys:
                raise _schema_error(path + [extra_keys[0]], "additional properties are not allowed")

        for key, item_value in value.items():
            if key in properties:
                _validate_against_schema(item_value, properties[key], root_schema, path + [str(key)])
        return

    if schema_type == "array":
        if not isinstance(value, list):
            raise _schema_error(path, f"expected array, got {type(value).__name__}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate_against_schema(item, item_schema, root_schema, path + [str(index)])
        return

    if schema_type == "string":
        if not isinstance(value, str):
            raise _schema_error(path, f"expected string, got {type(value).__name__}")
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            raise _schema_error(path, f"string is shorter than minLength {min_length}")
        enum = schema.get("enum")
        if isinstance(enum, list) and value not in enum:
            raise _schema_error(path, f"value {value!r} is not one of {', '.join(map(str, enum))}")
        return

    if schema_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise _schema_error(path, f"expected number, got {type(value).__name__}")
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, (int, float)) and value < minimum:
            raise _schema_error(path, f"value {value} is smaller than minimum {minimum}")
        if isinstance(maximum, (int, float)) and value > maximum:
            raise _schema_error(path, f"value {value} is greater than maximum {maximum}")
        return

    if schema_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise _schema_error(path, f"expected integer, got {type(value).__name__}")
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, int) and value < minimum:
            raise _schema_error(path, f"value {value} is smaller than minimum {minimum}")
        if isinstance(maximum, int) and value > maximum:
            raise _schema_error(path, f"value {value} is greater than maximum {maximum}")
        return

    if schema_type == "boolean":
        if not isinstance(value, bool):
            raise _schema_error(path, f"expected boolean, got {type(value).__name__}")
        return

    if schema_type == "null":
        if value is not None:
            raise _schema_error(path, f"expected null, got {type(value).__name__}")
        return

    enum = schema.get("enum")
    if isinstance(enum, list) and value not in enum:
        raise _schema_error(path, f"value {value!r} is not one of {', '.join(map(str, enum))}")


def validate_report(report: dict, schema: dict) -> None:
    _validate_against_schema(report, schema, schema, [])


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    start = text.find("```json")
    if start == -1:
        start = text.find("```")
    if start != -1:
        text = text[start:]
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    end = text.rfind("```")
    if end != -1:
        text = text[:end]
    return text.strip()


def _strip_known_schema_metadata(parsed: dict) -> dict:
    cleaned = dict(parsed)
    for key in ("$schema", "$id", "title"):
        cleaned.pop(key, None)
    return cleaned


def parse_and_validate_response(raw_text: str, schema: dict) -> dict:
    stripped = _strip_json_fence(raw_text)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise LinkedInGenerateError(
            f"LLM response is not valid JSON: {e}\n\nRaw response:\n{raw_text}"
        )
    if not isinstance(parsed, dict):
        raise LinkedInGenerateError(
            f"LLM response is not a JSON object (got {type(parsed).__name__})"
        )
    parsed = _strip_known_schema_metadata(parsed)
    validate_report(parsed, schema)
    return parsed


def _build_llm_output_schema(public_schema: dict) -> dict:
    llm_schema = json.loads(json.dumps(public_schema))
    for key in ("$schema", "$id", "title"):
        llm_schema.pop(key, None)
    return llm_schema


def _build_linkedin_messages(
    candidate_payload: dict,
    prompt: str,
    locale: str,
    llm_schema: dict,
    extra_contexts: list[str] | None = None,
) -> list[dict]:
    system_msg = prompt.format(
        locale=locale,
    )

    candidate_json = json.dumps(candidate_payload, indent=2, ensure_ascii=False)
    schema_json = json.dumps(llm_schema, indent=2, ensure_ascii=False)

    locale_instruction = (
        f"Write all natural-language fields in {locale}.\n"
        if locale != "en"
        else ""
    )

    user_content = (
        f"{locale_instruction}"
        f"Output schema (use this exact JSON contract):\n"
        f"```json\n{schema_json}\n```\n\n"
        f"Candidate payload:\n"
        f"```json\n{candidate_json}\n```"
    )

    if extra_contexts:
        for i, ctx in enumerate(extra_contexts):
            user_content += f"\n\nExtra context {i + 1}:\n```\n{ctx}\n```"

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_content},
    ]


def _build_effective_config(
    config: LLMConfig,
    timeout_seconds: int | None,
    max_tokens: int | None,
) -> LLMConfig:
    effective_timeout = timeout_seconds if timeout_seconds is not None else config.timeout_seconds
    effective_max_tokens = max_tokens if max_tokens is not None else config.max_tokens

    if effective_timeout <= 0:
        raise LinkedInGenerateError("--timeout-seconds must be greater than zero")
    if effective_max_tokens <= 0:
        raise LinkedInGenerateError("--max-tokens must be greater than zero")

    return LLMConfig(
        {
            "base_url": config.base_url,
            "api_key": config.api_key,
            "model": config.model,
            "temperature": config.temperature,
            "timeout_seconds": effective_timeout,
            "max_tokens": effective_max_tokens,
        }
    )


def _parse_lint_output(output: str) -> dict:
    status = "pass"
    ok_count = 0
    warn_count = 0
    fail_count = 0
    warning_summaries: list[str] = []
    failure_summaries: list[str] = []

    for line in output.splitlines():
        if line.startswith("[OK]"):
            ok_count += 1
        elif line.startswith("[WARN]"):
            warn_count += 1
            summary = line[6:].strip()
            if summary:
                warning_summaries.append(summary)
        elif line.startswith("[FAIL]"):
            fail_count += 1
            summary = line[6:].strip()
            if summary:
                failure_summaries.append(summary)

    if fail_count > 0:
        status = "fail"
    elif warn_count > 0:
        status = "warning"

    return {
        "status": status,
        "ok": ok_count,
        "warn": warn_count,
        "fail": fail_count,
        "warning_summaries": warning_summaries,
        "failure_summaries": failure_summaries,
    }


def render_text_report(report: dict) -> str:
    lines: list[str] = []

    sep = "=" * 70
    lines.append(sep)
    lines.append("           LINKEDIN PROFILE REPORT")
    lines.append(sep)
    lines.append("")

    lines.append("DISCLAIMER")
    lines.append("-" * 70)
    lines.append(report.get("disclaimer", ""))
    lines.append("")

    lines.append("PROFILE STRATEGY")
    lines.append("-" * 70)
    lines.append(report.get("profile_focus", ""))
    lines.append("")

    headline = report.get("headline", {})
    if headline:
        lines.append("HEADLINE")
        lines.append("-" * 70)
        lines.append(f"  Recommended: {headline.get('recommended', '')}")
        for r in headline.get("rationale", []):
            lines.append(f"  - {r}")
        lines.append("")

    about = report.get("about", {})
    if about:
        lines.append("ABOUT / SUMMARY")
        lines.append("-" * 70)
        lines.append(about.get("recommended", ""))
        lines.append("")
        for r in about.get("rationale", []):
            lines.append(f"  - {r}")
        lines.append("")

    top_skills = report.get("top_skills", [])
    if top_skills:
        lines.append("TOP SKILLS TO EMPHASIZE")
        lines.append("-" * 70)
        for skill in top_skills:
            lines.append(f"  * {skill.get('name', '')}")
            lines.append(f"    {skill.get('reason', '')}")
        lines.append("")

    exp_highlights = report.get("experience_highlights", [])
    if exp_highlights:
        lines.append("EXPERIENCE EMPHASIS GUIDANCE")
        lines.append("-" * 70)
        for entry in exp_highlights:
            ref = entry.get("experience_ref", "")
            lines.append(f"  * {ref}")
            for emphasis in entry.get("recommended_emphasis", []):
                lines.append(f"    - {emphasis}")
            rewrite = entry.get("optional_rewrite", "")
            if rewrite:
                lines.append(f"    Optional rewrite: {rewrite}")
        lines.append("")

    proj_highlights = report.get("project_highlights", [])
    if proj_highlights:
        lines.append("PROJECT EMPHASIS GUIDANCE")
        lines.append("-" * 70)
        for entry in proj_highlights:
            ref = entry.get("project_ref", "")
            lines.append(f"  * {ref}")
            for emphasis in entry.get("recommended_emphasis", []):
                lines.append(f"    - {emphasis}")
            rewrite = entry.get("optional_rewrite", "")
            if rewrite:
                lines.append(f"    Optional rewrite: {rewrite}")
        lines.append("")

    keywords = report.get("keywords", {})
    if keywords:
        lines.append("KEYWORDS")
        lines.append("-" * 70)
        prioritize = keywords.get("prioritize", [])
        if prioritize:
            lines.append("  Prioritize:")
            for kw in prioritize:
                lines.append(f"    + {kw}")
        avoid = keywords.get("avoid", [])
        if avoid:
            lines.append("  Avoid:")
            for kw in avoid:
                lines.append(f"    - {kw}")
        lines.append("")

    cautions = report.get("cautions", [])
    if cautions:
        lines.append("CAUTIONS / UNSUPPORTED CLAIMS TO AVOID")
        lines.append("-" * 70)
        for c in cautions:
            lines.append(f"  ! {c}")
        lines.append("")

    grounding_notes = report.get("grounding_notes", [])
    if grounding_notes:
        lines.append("GROUNDING NOTES")
        lines.append("-" * 70)
        for note in grounding_notes:
            lines.append(f"  * {note}")
        lines.append("")

    return "\n".join(lines)


def render_markdown_report(report: dict) -> str:
    lines: list[str] = []

    lines.append("# LinkedIn Profile Report")
    lines.append("")

    lines.append("## Disclaimer")
    lines.append("")
    lines.append(report.get("disclaimer", ""))
    lines.append("")

    lines.append("## Profile Strategy")
    lines.append("")
    lines.append(report.get("profile_focus", ""))
    lines.append("")

    headline = report.get("headline", {})
    if headline:
        lines.append("## Headline")
        lines.append("")
        lines.append(f"**Recommended:** {headline.get('recommended', '')}")
        lines.append("")
        for r in headline.get("rationale", []):
            lines.append(f"- {r}")
        lines.append("")

    about = report.get("about", {})
    if about:
        lines.append("## About / Summary")
        lines.append("")
        lines.append(about.get("recommended", ""))
        lines.append("")
        for r in about.get("rationale", []):
            lines.append(f"- {r}")
        lines.append("")

    top_skills = report.get("top_skills", [])
    if top_skills:
        lines.append("## Top Skills to Emphasize")
        lines.append("")
        for skill in top_skills:
            lines.append(f"- **{skill.get('name', '')}**")
            lines.append(f"  - {skill.get('reason', '')}")
        lines.append("")

    exp_highlights = report.get("experience_highlights", [])
    if exp_highlights:
        lines.append("## Experience Emphasis Guidance")
        lines.append("")
        for entry in exp_highlights:
            ref = entry.get("experience_ref", "")
            lines.append(f"- **{ref}**")
            for emphasis in entry.get("recommended_emphasis", []):
                lines.append(f"  - {emphasis}")
            rewrite = entry.get("optional_rewrite", "")
            if rewrite:
                lines.append(f"  - Optional rewrite: {rewrite}")
        lines.append("")

    proj_highlights = report.get("project_highlights", [])
    if proj_highlights:
        lines.append("## Project Emphasis Guidance")
        lines.append("")
        for entry in proj_highlights:
            ref = entry.get("project_ref", "")
            lines.append(f"- **{ref}**")
            for emphasis in entry.get("recommended_emphasis", []):
                lines.append(f"  - {emphasis}")
            rewrite = entry.get("optional_rewrite", "")
            if rewrite:
                lines.append(f"  - Optional rewrite: {rewrite}")
        lines.append("")

    keywords = report.get("keywords", {})
    if keywords:
        lines.append("## Keywords")
        lines.append("")
        prioritize = keywords.get("prioritize", [])
        if prioritize:
            lines.append("**Prioritize:**")
            for kw in prioritize:
                lines.append(f"- {kw}")
        avoid = keywords.get("avoid", [])
        if avoid:
            lines.append("**Avoid:**")
            for kw in avoid:
                lines.append(f"- {kw}")
        lines.append("")

    cautions = report.get("cautions", [])
    if cautions:
        lines.append("## Cautions / Unsupported Claims to Avoid")
        lines.append("")
        for c in cautions:
            lines.append(f"- {c}")
        lines.append("")

    grounding_notes = report.get("grounding_notes", [])
    if grounding_notes:
        lines.append("## Grounding Notes")
        lines.append("")
        for note in grounding_notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)


def render_json_output(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False)


def _build_command_string(
    candidate_path: str,
    config_path: str | None,
    locale: str,
    format: str,
    output_path: str,
    log_path: str | None,
    prompt_path: str | None,
    extra_context_paths: list[str] | None,
    timeout_seconds: int | None,
    max_tokens: int | None,
) -> str:
    parts = [
        "hirepaper linkedin generate",
        candidate_path,
    ]
    if config_path:
        parts.extend(["--config", config_path])
    if locale != "en":
        parts.extend(["--locale", locale])
    if format != "txt":
        parts.extend(["--format", format])
    parts.extend(["--output", output_path])
    if log_path:
        parts.extend(["--log", log_path])
    if prompt_path:
        parts.extend(["--prompt", prompt_path])
    if extra_context_paths:
        for ctx in extra_context_paths:
            parts.extend(["--extra-context", ctx])
    if timeout_seconds is not None:
        parts.extend(["--timeout-seconds", str(timeout_seconds)])
    if max_tokens is not None:
        parts.extend(["--max-tokens", str(max_tokens)])
    return " ".join(parts)


def save_log_zip(
    log_path: str,
    meta: dict,
    candidate_input_payload: dict,
    extra_contexts: list[str] | None,
    linkedin_schema: dict,
    prompt_text: str,
    raw_response: str,
    validated_report: dict | None,
    report_text: str | None,
) -> None:
    try:
        with StagedLogArchive(log_path, prefix="hirepaper-linkedin-log-") as archive:
            archive.write_json("meta.json", meta)
            archive.write_json("candidate-input-payload.json", candidate_input_payload)
            if extra_contexts:
                for i, ctx in enumerate(extra_contexts):
                    archive.write_text(f"extra-context-{i + 1}.txt", ctx)
            archive.write_json("linkedin-report-schema.json", linkedin_schema)
            archive.write_text("prompt.txt", prompt_text)
            archive.write_json("raw-llm-response.json", {"raw_text": raw_response})
            if validated_report is not None:
                archive.write_json("validated-linkedin-report.json", validated_report)
            if report_text is not None:
                archive.write_text("final-report.txt", report_text)
            archive.finalize()
    except LogArchiveError as e:
        raise LinkedInGenerateError(str(e))


def run_generate(
    candidate_path: str,
    config: LLMConfig,
    locale: str,
    format: str,
    output_path: str,
    log_path: str | None,
    prompt_text: str,
    extra_context_paths: list[str] | None,
    timeout_seconds: int | None,
    max_tokens: int | None,
    verbose: int,
) -> tuple[str, dict, dict]:
    if format not in ("txt", "md", "json"):
        raise LinkedInGenerateError(f"unsupported --format '{format}' (supported: txt, md, json)")

    candidate_file = Path(candidate_path)
    if not candidate_file.exists():
        raise LinkedInGenerateError(f"candidate file not found: {candidate_path}")
    try:
        candidate = load_candidate(candidate_file)
    except (ValueError, KeyError) as e:
        raise LinkedInGenerateError(f"invalid candidate data: {e}")

    _stdout_redirect = io.StringIO()
    with contextlib.redirect_stdout(_stdout_redirect):
        lint_code = lint_candidate(candidate)
    lint_output = _stdout_redirect.getvalue()
    lint_summary = _parse_lint_output(lint_output)

    if lint_code != 0:
        sys.stderr.write(lint_output)
        raise LinkedInGenerateError(
            "Content lint FAILED — LinkedIn generation aborted. "
            "Fix candidate data quality issues before generating a LinkedIn report."
        )

    if verbose > 0:
        sys.stderr.write(lint_output)

    extra_contexts: list[str] = []
    if extra_context_paths:
        for ctx_path in extra_context_paths:
            ctx_file = Path(ctx_path)
            if not ctx_file.exists():
                raise LinkedInGenerateError(f"extra-context file not found: {ctx_path}")
            try:
                ctx_text = ctx_file.read_text(encoding="utf-8")
            except OSError as e:
                raise LinkedInGenerateError(f"cannot read extra-context file: {ctx_path} — {e}")
            if not ctx_text.strip():
                raise LinkedInGenerateError(f"extra-context file is empty: {ctx_path}")
            extra_contexts.append(ctx_text)

    candidate_payload = _build_candidate_payload(candidate)
    linkedin_schema = load_linkedin_schema()
    llm_output_schema = _build_llm_output_schema(linkedin_schema)

    effective_config = _build_effective_config(config, timeout_seconds, max_tokens)

    linkedin_messages = _build_linkedin_messages(
        candidate_payload=candidate_payload,
        prompt=prompt_text,
        locale=locale,
        llm_schema=llm_output_schema,
        extra_contexts=extra_contexts if extra_contexts else None,
    )

    spinner_stop = threading.Event()

    def _spin():
        chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        i = 0
        while not spinner_stop.is_set():
            sys.stderr.write(f"\r{chars[i]} Generating LinkedIn report... ")
            sys.stderr.flush()
            i = (i + 1) % len(chars)
            time.sleep(0.1)
        sys.stderr.write("\r\033[K")
        sys.stderr.flush()

    spinner = threading.Thread(target=_spin, daemon=True)
    spinner.start()

    raw_response_text: str = ""
    usage: dict | None = None

    try:
        response = _complete(effective_config, linkedin_messages)
    except LLMClientError as e:
        spinner_stop.set()
        spinner.join()
        raise LinkedInGenerateError(f"LLM request failed: {e}")
    finally:
        spinner_stop.set()
        spinner.join()

    finish_reason = None
    try:
        finish_reason = response.choices[0].finish_reason
    except (AttributeError, IndexError, TypeError):
        pass

    try:
        raw_response_text = _extract_text(response)
    except LLMClientError:
        if finish_reason != "length":
            raise LinkedInGenerateError("LLM response has no usable text")

    if finish_reason == "length":
        snippet = raw_response_text[-200:] if len(raw_response_text) > 200 else raw_response_text
        raise LinkedInGenerateError(
            f"LLM response was truncated (finish_reason=length). "
            f"The model hit the token limit before completing the report JSON. "
            f"Raw response tail: ...{repr(snippet)}"
        )

    try:
        usage = _extract_usage(response)
    except LLMClientError:
        usage = None

    validated_report = parse_and_validate_response(raw_response_text, linkedin_schema)

    if format == "json":
        report_str = render_json_output(validated_report)
    elif format == "md":
        report_str = render_markdown_report(validated_report)
    else:
        report_str = render_text_report(validated_report)

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        out_path.write_text(report_str, encoding="utf-8")
    except OSError as e:
        raise LinkedInGenerateError(f"cannot write output: {output_path} — {e}")

    log_report_ext = "md" if format == "md" else "txt"

    meta = {
        "command": _build_command_string(
            candidate_path, config.config_path,
            locale, format, output_path, log_path,
            None, extra_context_paths,
            timeout_seconds, max_tokens,
        ),
        "timestamp_utc": _utcnow_iso(),
        "candidate_path": candidate_path,
        "output_path": output_path,
        "log_path": log_path or "",
        "format": format,
        "locale": locale,
        "model": config.model,
        "base_url": config.base_url,
        "timeout_seconds": effective_config.timeout_seconds,
        "max_tokens": effective_config.max_tokens,
        "lint_status": lint_summary.get("status", "unknown"),
        "generation_status": "success",
    }

    if log_path:
        save_log_zip(
            log_path=log_path,
            meta=meta,
            candidate_input_payload=candidate_payload,
            extra_contexts=extra_contexts if extra_contexts else None,
            linkedin_schema=linkedin_schema,
            prompt_text=prompt_text,
            raw_response=raw_response_text,
            validated_report=validated_report,
            report_text=report_str if format in ("txt", "md") else None,
        )

    return report_str, validated_report, meta
