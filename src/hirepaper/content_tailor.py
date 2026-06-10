from __future__ import annotations

import contextlib
import copy
import io
import json
import re
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

_VALID_MODES = frozenset({"conservative", "rewrite"})
_VALID_INFERENCE = frozenset({"low", "medium", "high"})
_VALID_REPORT_FORMATS = frozenset({"text", "md", "json"})
_CANDIDATE_SCHEMA_NAME = "candidate.schema.json"
_TAILOR_PLAN_SCHEMA_NAME = "content-tailor-plan.schema.json"
_TAILOR_REPORT_SCHEMA_NAME = "content-tailor-report.schema.json"
_REWRITE_RESPONSE_SCHEMA_NAME = "content-tailor-rewrite-response.schema.json"


class ContentTailorError(Exception):
    pass


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def localized_disclaimer(locale: str) -> str:
    normalized = locale.replace("_", "-").lower()
    if normalized.startswith("pt"):
        return (
            "Esta adaptacao usa um LLM e pode conter julgamento subjetivo. "
            "Revise o resultado antes de tomar decisoes."
        )
    return (
        "This tailoring uses an LLM and may contain subjective judgment. "
        "Review the result before making decisions."
    )


def load_candidate_schema() -> dict:
    path = schemas_dir() / _CANDIDATE_SCHEMA_NAME
    if not path.exists():
        raise ContentTailorError(f"candidate schema not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise ContentTailorError(f"candidate schema read error: {path} — {e}")
    except json.JSONDecodeError as e:
        raise ContentTailorError(f"invalid candidate schema JSON: {path} — {e}")
    return raw


def load_tailor_plan_schema() -> dict:
    path = schemas_dir() / _TAILOR_PLAN_SCHEMA_NAME
    if not path.exists():
        raise ContentTailorError(f"tailor plan schema not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise ContentTailorError(f"tailor plan schema read error: {path} — {e}")
    except json.JSONDecodeError as e:
        raise ContentTailorError(f"invalid tailor plan schema JSON: {path} — {e}")
    return raw


def load_tailor_report_schema() -> dict:
    path = schemas_dir() / _TAILOR_REPORT_SCHEMA_NAME
    if not path.exists():
        raise ContentTailorError(f"tailor report schema not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise ContentTailorError(f"tailor report schema read error: {path} — {e}")
    except json.JSONDecodeError as e:
        raise ContentTailorError(f"invalid tailor report schema JSON: {path} — {e}")
    return raw


def load_rewrite_response_schema() -> dict:
    path = schemas_dir() / _REWRITE_RESPONSE_SCHEMA_NAME
    if not path.exists():
        raise ContentTailorError(f"rewrite response schema not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise ContentTailorError(f"rewrite response schema read error: {path} — {e}")
    except json.JSONDecodeError as e:
        raise ContentTailorError(f"invalid rewrite response schema JSON: {path} — {e}")
    return raw


def load_default_tailor_prompt() -> str:
    path = prompts_dir() / "content-tailor-default.txt"
    if not path.exists():
        raise ContentTailorError(f"default tailor prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def load_prompt(prompt_path: str | None) -> str:
    if prompt_path is not None:
        path = Path(prompt_path)
        if not path.exists():
            raise ContentTailorError(f"prompt file not found: {prompt_path}")
        try:
            return path.read_text(encoding="utf-8")
        except OSError as e:
            raise ContentTailorError(f"prompt file read error: {prompt_path} — {e}")
    return load_default_tailor_prompt()


def _build_llm_output_schema(public_schema: dict) -> dict:
    llm_schema = json.loads(json.dumps(public_schema))
    for key in ("$schema", "$id", "title"):
        llm_schema.pop(key, None)
    return llm_schema


def _build_candidate_payload_with_ids(candidate: Candidate) -> dict:
    payload: dict[str, Any] = {}

    p = candidate.personal
    personal: dict[str, Any] = {
        "id": "personal",
        "name": p.name,
        "headline": p.headline or "",
        "email": p.email,
        "phone": {"value": p.phone.value, "hyperlink": p.phone.hyperlink},
        "location": p.location,
    }
    if p.links:
        personal["links"] = [
            {"id": f"link_{i}", "label": lnk.label, "url": lnk.url}
            for i, lnk in enumerate(p.links)
        ]
    if p.extra_links:
        personal["extra_links"] = [
            {"id": f"extra_link_{i}", "label": lnk.label, "url": lnk.url}
            for i, lnk in enumerate(p.extra_links)
        ]
    payload["personal"] = personal

    payload["summary"] = {"id": "summary", "text": candidate.summary}
    payload["target_role"] = {"id": "target_role", "text": candidate.target_role or ""}

    payload["experience"] = [
        {
            "id": f"exp_{i}",
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
            "highlights": [
                {"id": f"exp_{i}_hl_{j}", "text": h}
                for j, h in enumerate(e.highlights)
            ],
            "achievements": [
                {
                    "id": f"exp_{i}_ach_{j}",
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
                for j, a in enumerate(e.achievements)
            ],
        }
        for i, e in enumerate(candidate.experience)
    ]

    payload["education"] = [
        {
            "id": f"edu_{i}",
            "institution": e.institution,
            "degree": e.degree,
            "location": e.location,
            "start_date": e.start_date,
            "end_date": e.end_date,
            "gpa": e.gpa or "",
            "honors": e.honors or "",
        }
        for i, e in enumerate(candidate.education)
    ]

    if candidate.skills and candidate.skills.categories:
        payload["skills"] = {
            "categories": [
                {
                    "id": f"skill_cat_{i}",
                    "name": cat.name,
                    "items": [
                        {"id": f"skill_cat_{i}_item_{j}", "name": item}
                        for j, item in enumerate(cat.items)
                    ],
                }
                for i, cat in enumerate(candidate.skills.categories)
            ]
        }
    else:
        payload["skills"] = {"categories": []}

    payload["projects"] = [
        {
            "id": f"proj_{i}",
            "name": p.name,
            "description": p.description,
            "role": p.role or "",
            "start_date": p.start_date or "",
            "end_date": p.end_date or "",
            "technologies": p.technologies,
            "url": p.url or "",
            "highlights": [
                {"id": f"proj_{i}_hl_{j}", "text": h}
                for j, h in enumerate(p.highlights)
            ],
        }
        for i, p in enumerate(candidate.projects)
    ]

    payload["certifications"] = [
        {
            "id": f"cert_{i}",
            "name": c.name,
            "issuer": c.issuer,
            "date": c.date,
        }
        for i, c in enumerate(candidate.certifications)
    ]

    payload["awards"] = [
        {
            "id": f"award_{i}",
            "name": a.name,
            "issuer": a.issuer,
            "date": a.date,
            "description": a.description or "",
        }
        for i, a in enumerate(candidate.awards)
    ]

    payload["volunteer"] = [
        {
            "id": f"vol_{i}",
            "organization": v.organization,
            "position": v.position,
            "location": v.location,
            "start_date": v.start_date,
            "end_date": v.end_date,
            "current": v.current,
            "highlights": [
                {"id": f"vol_{i}_hl_{j}", "text": h}
                for j, h in enumerate(v.highlights)
            ],
        }
        for i, v in enumerate(candidate.volunteer)
    ]

    payload["languages"] = [
        {"id": f"lang_{i}", "language": lang.language, "proficiency": lang.proficiency}
        for i, lang in enumerate(candidate.languages)
    ]

    return payload


def _resolve_schema_ref(root_schema: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        raise ContentTailorError(f"unsupported schema ref: {ref}")
    node: object = root_schema
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            raise ContentTailorError(f"invalid schema ref: {ref}")
        node = node[part]
    if not isinstance(node, dict):
        raise ContentTailorError(f"invalid schema ref target: {ref}")
    return node


def _schema_error(path: list[str], message: str) -> ContentTailorError:
    location = ".".join(path)
    if location:
        return ContentTailorError(f"plan does not match schema at '{location}': {message}")
    return ContentTailorError(f"plan does not match schema: {message}")


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


def _validate_plan(plan: dict, plan_schema: dict) -> None:
    _validate_against_schema(plan, plan_schema, plan_schema, [])

    mode = plan.get("mode")
    inference = plan.get("inference")
    if mode not in _VALID_MODES:
        raise ContentTailorError(f"plan has invalid mode: {mode}")
    if inference not in _VALID_INFERENCE:
        raise ContentTailorError(f"plan has invalid inference: {inference}")


def _validate_report(report: dict, report_schema: dict) -> None:
    _validate_against_schema(report, report_schema, report_schema, [])


def _validate_candidate_json(candidate_json: dict, candidate_schema: dict) -> None:
    _validate_against_schema(candidate_json, candidate_schema, candidate_schema, [])


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
        raise ContentTailorError(
            f"LLM response is not valid JSON: {e}\n\nRaw response:\n{raw_text}"
        )
    if not isinstance(parsed, dict):
        raise ContentTailorError(
            f"LLM response is not a JSON object (got {type(parsed).__name__})"
        )
    parsed = _strip_known_schema_metadata(parsed)
    _validate_plan(parsed, schema)
    return parsed


def _validate_rewrite_response(
    parsed: dict,
    rewrite_schema: dict,
    rewrite_request: dict,
) -> dict:
    _validate_against_schema(parsed, rewrite_schema, rewrite_schema, [])

    expected_refs = [str(ref).strip() for ref in rewrite_request.get("target_refs", []) if str(ref).strip()]
    parsed_target_refs = parsed.get("target_refs", [])
    if not isinstance(parsed_target_refs, list):
        raise ContentTailorError(
            f"rewrite response: 'target_refs' must be a list "
            f"(expected {expected_refs!r})"
        )
    normalized_target_refs = [str(ref).strip() for ref in parsed_target_refs if str(ref).strip()]
    if sorted(normalized_target_refs) != sorted(expected_refs):
        raise ContentTailorError(
            f"rewrite response: 'target_refs' mismatch — "
            f"expected {expected_refs!r}, got {normalized_target_refs!r}"
        )
    expected_operation = str(rewrite_request.get("allowed_operation", "")).replace("rewrite_", "")
    if parsed.get("operation") != expected_operation:
        raise ContentTailorError(
            "rewrite response: 'operation' does not match the active rewrite request"
        )

    rewrites = parsed.get("rewrites", {})
    if not isinstance(rewrites, dict):
        raise ContentTailorError("rewrite response: 'rewrites' must be an object")
    request_refs = parsed.get("request_refs", [])
    if not isinstance(request_refs, list) or not request_refs:
        raise ContentTailorError("rewrite response: 'request_refs' must be a non-empty list")

    rewrite_keys = [str(ref).strip() for ref in rewrites.keys() if str(ref).strip()]
    if parsed.get("operation") == "1_to_1":
        if sorted(rewrite_keys) != sorted(expected_refs):
            raise ContentTailorError(
                "rewrite response: 1_to_1 rewrites must provide exactly one rewritten text for each target ref"
            )
    elif parsed.get("operation") == "n_to_1":
        if len(rewrite_keys) != 1:
            raise ContentTailorError(
                "rewrite response: n_to_1 rewrites must provide exactly one rewritten text entry"
            )
        if rewrite_keys[0] not in expected_refs:
            raise ContentTailorError(
                "rewrite response: n_to_1 rewrite key must be one of the active target refs"
            )

    for ref, new_text in rewrites.items():
        if not isinstance(ref, str) or not ref.strip():
            raise ContentTailorError(f"rewrite response: invalid ref {ref!r}")
        if not isinstance(new_text, str) or not new_text.strip():
            raise ContentTailorError(f"rewrite response: empty text for ref {ref!r}")

    return parsed


def parse_and_validate_rewrite_response(
    raw_text: str,
    rewrite_schema: dict,
    rewrite_request: dict,
) -> dict:
    stripped = _strip_json_fence(raw_text)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise ContentTailorError(
            f"rewrite response is not valid JSON: {e}\n\nRaw response:\n{raw_text}"
        )
    if not isinstance(parsed, dict):
        raise ContentTailorError(
            f"rewrite response is not a JSON object (got {type(parsed).__name__})"
        )
    parsed = _strip_known_schema_metadata(parsed)
    return _validate_rewrite_response(parsed, rewrite_schema, rewrite_request)


def build_plan_messages(
    candidate_payload: dict,
    vacancy_text: str,
    prompt: str,
    mode: str,
    inference: str,
    locale: str,
    candidate_schema: dict,
    plan_schema: dict,
    extra_contexts: list[str] | None = None,
) -> list[dict]:
    system_msg = prompt.format(
        locale=locale,
        mode=mode,
        inference=inference,
    )

    candidate_json = json.dumps(candidate_payload, indent=2, ensure_ascii=False)
    plan_schema_json = json.dumps(plan_schema, indent=2, ensure_ascii=False)
    candidate_schema_json = json.dumps(candidate_schema, indent=2, ensure_ascii=False)

    locale_instruction = (
        f"Write all natural-language fields in {locale}.\n"
        if locale != "en"
        else ""
    )

    user_content = (
        f"{locale_instruction}"
        f"Mode: {mode}\n"
        f"Inference: {inference}\n\n"
        f"Output schema (use this exact JSON contract):\n"
        f"```json\n{plan_schema_json}\n```\n\n"
        f"Candidate JSON Schema (for reference):\n"
        f"```json\n{candidate_schema_json}\n```\n\n"
        f"Candidate payload with stable IDs:\n"
        f"```json\n{candidate_json}\n```\n\n"
        f"Vacancy text:\n"
        f"```\n{vacancy_text}\n```"
    )

    if extra_contexts:
        for i, ctx in enumerate(extra_contexts):
            user_content += f"\n\nExtra context {i + 1}:\n```\n{ctx}\n```"

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_content},
    ]


def _build_rewrite_messages(
    rewrite_request: dict,
    candidate_payload: dict,
    locale: str,
    mode: str,
    inference: str,
    rewrite_response_schema: dict | None = None,
) -> list[dict]:
    target_kind = rewrite_request["target_kind"]
    target_refs = rewrite_request["target_refs"]
    instruction = rewrite_request["instruction"]
    allowed_operation = rewrite_request["allowed_operation"]

    original_texts: list[str] = []
    for ref in target_refs:
        text = _resolve_ref_text(ref, candidate_payload)
        if text:
            original_texts.append(f"[{ref}]: {text}")

    schema_json = ""
    if rewrite_response_schema:
        schema_json = (
            "\n\nOutput schema (use this exact JSON contract):\n"
            f"```json\n{json.dumps(rewrite_response_schema, indent=2, ensure_ascii=False)}\n```"
        )

    system_msg = (
        "You are a rewrite assistant for hirepaper. "
        "Rewrite the requested items according to the instructions provided. "
        f"Use {locale} for all natural-language output. "
        f"Mode: {mode}. Inference: {inference}. "
        f"Operation: {allowed_operation}. "
        "Return only valid JSON. "
        "Do not add markdown fences or commentary."
    )

    expected_refs_json = json.dumps(target_refs)

    user_content = (
        f"Instruction: {instruction}\n\n"
        f"Target refs to rewrite: {expected_refs_json}\n"
        f"Expected operation: {allowed_operation.replace('rewrite_', '')}\n\n"
        "Response contract notes:\n"
        "- request_refs: list the refs you used as the basis for the rewrite.\n"
        "- target_refs: MUST be exactly the target refs listed above, in the same order.\n"
        "- operation: MUST match the expected operation above.\n"
        "- rewrites: for 1_to_1, return one rewritten text for each target ref. For n_to_1, return exactly one rewritten text keyed by one of the target refs.\n\n"
        f"Original texts to rewrite:\n"
        + "\n".join(original_texts)
        + schema_json
    )

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_content},
    ]


def _resolve_ref_text(ref: str, payload: dict) -> str | None:
    for section_key in ("personal", "summary", "target_role", "experience",
                        "education", "projects", "certifications", "awards",
                        "volunteer", "languages"):
        section = payload.get(section_key)
        if section_key == "personal":
            if ref == "personal":
                return json.dumps(section, indent=2)
            if ref == "headline":
                return section.get("headline", "")
            if ref == "summary":
                if isinstance(payload.get("summary"), dict):
                    return payload["summary"].get("text", "")
                return str(payload.get("summary", ""))
            if ref == "target_role":
                if isinstance(payload.get("target_role"), dict):
                    return payload["target_role"].get("text", "")
                return str(payload.get("target_role", ""))
            if ref.startswith("link_"):
                for link in section.get("links", []):
                    if link.get("id") == ref:
                        return f"{link.get('label', '')}: {link.get('url', '')}"
            if ref.startswith("extra_link_"):
                for link in section.get("extra_links", []):
                    if link.get("id") == ref:
                        return f"{link.get('label', '')}: {link.get('url', '')}"
        elif isinstance(section, list):
            for item in section:
                if isinstance(item, dict) and item.get("id") == ref:
                    return json.dumps(item, indent=2)
                if isinstance(item, dict):
                    for sub_key in ("highlights", "achievements"):
                        subs = item.get(sub_key, [])
                        if isinstance(subs, list):
                            for sub in subs:
                                if isinstance(sub, dict) and sub.get("id") == ref:
                                    return sub.get("text") or sub.get("summary") or json.dumps(sub)
        elif isinstance(section, dict):
            cats = section.get("categories", [])
            if isinstance(cats, list):
                for cat in cats:
                    if isinstance(cat, dict) and cat.get("id") == ref:
                        return json.dumps(cat, indent=2)
                    items = cat.get("items", [])
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict) and item.get("id") == ref:
                                return item.get("name", "")
    return None


def _build_effective_config(
    config: LLMConfig,
    timeout_seconds: int | None,
    max_tokens: int | None,
) -> LLMConfig:
    effective_timeout = timeout_seconds if timeout_seconds is not None else config.timeout_seconds
    effective_max_tokens = max_tokens if max_tokens is not None else config.max_tokens

    if effective_timeout <= 0:
        raise ContentTailorError("--timeout-seconds must be greater than zero")
    if effective_max_tokens <= 0:
        raise ContentTailorError("--max-tokens must be greater than zero")

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


def _find_item_by_id(container: list, target_id: str) -> dict | None:
    for item in container:
        if isinstance(item, dict) and item.get("id") == target_id:
            return item
    return None


def _find_sub_items(container: list, target_ids: list[str]) -> list[dict]:
    found: list[dict] = []
    for item in container:
        if isinstance(item, dict) and item.get("id") in target_ids:
            found.append(item)
    return found


def _apply_structural_actions(
    plan: dict,
    candidate_raw: dict,
) -> tuple[dict, list[str]]:
    result = copy.deepcopy(candidate_raw)
    changes: list[str] = []
    actions = plan.get("structural_actions", [])

    kill_ids: set[str] = set()

    for action in actions:
        action_type = action["action_type"]
        target_kind = action["target_kind"]
        target_refs = action.get("target_refs", [])
        reason = action.get("reason", "")

        if action_type == "remove":
            for ref in target_refs:
                kill_ids.add(ref)
            changes.append(f"Removed {target_kind}: {', '.join(target_refs)} — {reason}")

        elif action_type == "keep":
            changes.append(f"Kept {target_kind}: {', '.join(target_refs)} — {reason}")

    for section_key, id_key in [
        ("experience", "exp_"),
        ("projects", "proj_"),
        ("certifications", "cert_"),
        ("awards", "award_"),
        ("volunteer", "vol_"),
        ("languages", "lang_"),
    ]:
        items = result.get(section_key, [])
        surviving = [
            item for item in items
            if isinstance(item, dict) and item.get("id") not in kill_ids
        ]
        result[section_key] = surviving

    for section_key in ("experience", "projects", "volunteer"):
        items = result.get(section_key, [])
        for item in items:
            if isinstance(item, dict):
                for sub_key in ("highlights", "achievements"):
                    subs = item.get(sub_key, [])
                    if isinstance(subs, list):
                        surviving_subs = [
                            s for s in subs
                            if isinstance(s, dict) and s.get("id") not in kill_ids
                        ]
                        item[sub_key] = surviving_subs

    for section_key, highlight_key in [
        ("experience", "highlights"),
        ("projects", "highlights"),
        ("volunteer", "highlights"),
    ]:
        items = result.get(section_key, [])
        for item in items:
            if isinstance(item, dict):
                subs = item.get(highlight_key, [])
                if isinstance(subs, list):
                    surviving_subs = [
                        s for s in subs
                        if isinstance(s, dict) and s.get("id") not in kill_ids
                    ]
                    item[highlight_key] = surviving_subs

    skills = result.get("skills")
    if isinstance(skills, dict):
        cats = skills.get("categories", [])
        if isinstance(cats, list):
            surviving_cats = [
                c for c in cats
                if isinstance(c, dict) and c.get("id") not in kill_ids
            ]
            for cat in surviving_cats:
                if isinstance(cat, dict):
                    items = cat.get("items", [])
                    if isinstance(items, list):
                        cat["items"] = [
                            i for i in items
                            if isinstance(i, dict) and i.get("id") not in kill_ids
                        ]
            skills["categories"] = surviving_cats

    personal = result.get("personal", {})
    if isinstance(personal, dict):
        for link_key in ("links", "extra_links"):
            links = personal.get(link_key, [])
            if isinstance(links, list):
                personal[link_key] = [
                    l for l in links
                    if isinstance(l, dict) and l.get("id") not in kill_ids
                ]

    for action in actions:
        action_type = action["action_type"]
        target_kind = action["target_kind"]
        target_refs = action.get("target_refs", [])
        reason = action.get("reason", "")
        replacement_refs = action.get("replacement_refs", [])

        if action_type == "reorder":
            if target_kind in ("experience_entry", "project_entry",
                               "certification", "award", "volunteer_entry",
                               "language"):
                section_map = {
                    "experience_entry": "experience",
                    "project_entry": "projects",
                    "certification": "certifications",
                    "award": "awards",
                    "volunteer_entry": "volunteer",
                    "language": "languages",
                }
                section_key = section_map.get(target_kind)
                if section_key and section_key in result:
                    items = result[section_key]
                    id_order = list(target_refs)
                    id_set = set(id_order)
                    remaining = [item for item in items if isinstance(item, dict) and item.get("id") not in id_set]
                    ordered = []
                    for rid in id_order:
                        item = _find_item_by_id(items, rid)
                        if item:
                            ordered.append(item)
                    ordered.extend(remaining)
                    result[section_key] = ordered
                    changes.append(f"Reordered {target_kind} to: {', '.join(target_refs)} — {reason}")

        elif action_type == "prioritize":
            if target_kind in ("experience_entry", "project_entry",
                               "certification", "volunteer_entry"):
                section_map = {
                    "experience_entry": "experience",
                    "project_entry": "projects",
                    "certification": "certifications",
                    "volunteer_entry": "volunteer",
                }
                section_key = section_map.get(target_kind)
                if section_key and section_key in result:
                    items = result[section_key]
                    id_set = set(target_refs)
                    prioritized = [item for item in items if isinstance(item, dict) and item.get("id") in id_set]
                    rest = [item for item in items if isinstance(item, dict) and item.get("id") not in id_set]
                    result[section_key] = prioritized + rest
                    changes.append(f"Prioritized {target_kind}: {', '.join(target_refs)} — {reason}")

        elif action_type == "deprioritize":
            if target_kind in ("experience_entry", "project_entry",
                               "certification", "volunteer_entry"):
                section_map = {
                    "experience_entry": "experience",
                    "project_entry": "projects",
                    "certification": "certifications",
                    "volunteer_entry": "volunteer",
                }
                section_key = section_map.get(target_kind)
                if section_key and section_key in result:
                    items = result[section_key]
                    id_set = set(target_refs)
                    deprioritized = [item for item in items if isinstance(item, dict) and item.get("id") in id_set]
                    rest = [item for item in items if isinstance(item, dict) and item.get("id") not in id_set]
                    result[section_key] = rest + deprioritized
                    changes.append(f"Deprioritized {target_kind}: {', '.join(target_refs)} — {reason}")

        elif action_type == "replace_items":
            if target_kind in ("skill_category", "skill_item"):
                skills_sec = result.get("skills", {})
                if isinstance(skills_sec, dict):
                    cats = skills_sec.get("categories", [])
                    if isinstance(cats, list) and replacement_refs:
                        if target_kind == "skill_category":
                            surviving_cats = [
                                c for c in cats
                                if isinstance(c, dict) and c.get("id") not in target_refs
                            ]
                            for ref in replacement_refs:
                                item = _find_item_by_id(cats, ref)
                                if item:
                                    surviving_cats.append(item)
                            skills_sec["categories"] = surviving_cats
                            changes.append(f"Replaced skill categories: replaced {', '.join(target_refs)} with {', '.join(replacement_refs)} — {reason}")
                        elif target_kind == "skill_item":
                            for cat in cats:
                                if isinstance(cat, dict):
                                    items = cat.get("items", [])
                                    if isinstance(items, list):
                                        surviving_items = [
                                            i for i in items
                                            if isinstance(i, dict) and i.get("id") not in target_refs
                                        ]
                                        for ref in replacement_refs:
                                            item = _find_item_by_id(items, ref)
                                            if item and item not in surviving_items:
                                                surviving_items.append(item)
                                        cat["items"] = surviving_items
                            changes.append(f"Replaced skill items: replaced {', '.join(target_refs)} with {', '.join(replacement_refs)} — {reason}")

    changed_sections = []
    for decision in plan.get("section_decisions", []):
        section_name = decision["section_name"]
        decision_type = decision["decision"]
        reason = decision.get("reason", "")
        if decision_type == "remove" and section_name not in ("personal", "summary", "experience", "skills"):
            section_key = _section_name_to_key(section_name)
            if section_key in result:
                if isinstance(result.get(section_key), list):
                    result[section_key] = []
                elif isinstance(result.get(section_key), str):
                    result[section_key] = ""
                changed_sections.append(section_name)
                changes.append(f"Removed section: {section_name} — {reason}")
        elif decision_type == "deprioritize":
            changed_sections.append(section_name)
            changes.append(f"Deprioritized section: {section_name} — {reason}")

    return result, changes


def _section_name_to_key(name: str) -> str:
    mapping = {
        "summary": "summary",
        "target_role": "target_role",
        "experience": "experience",
        "education": "education",
        "skills": "skills",
        "projects": "projects",
        "certifications": "certifications",
        "awards": "awards",
        "volunteer": "volunteer",
        "languages": "languages",
        "links": "personal",
        "extra_links": "personal",
    }
    return mapping.get(name, name)


def _apply_rewrite_to_payload(
    target_kind: str,
    rewrites: dict[str, str],
    candidate_raw: dict,
) -> None:
    if target_kind == "headline":
        first_value = next(iter(rewrites.values()), None)
        if first_value is not None and isinstance(candidate_raw.get("personal"), dict):
            candidate_raw["personal"]["headline"] = first_value
        return
    if target_kind == "summary":
        first_value = next(iter(rewrites.values()), None)
        if first_value is not None:
            candidate_raw["summary"] = first_value
        return
    if target_kind == "target_role":
        first_value = next(iter(rewrites.values()), None)
        if first_value is not None:
            candidate_raw["target_role"] = first_value
        return

    for ref, new_text in rewrites.items():
        if ref == "headline":
            if isinstance(candidate_raw.get("personal"), dict):
                candidate_raw["personal"]["headline"] = new_text
        elif ref == "summary":
            candidate_raw["summary"] = new_text
        elif ref == "target_role":
            candidate_raw["target_role"] = new_text
        elif ref.startswith("exp_"):
            _apply_experience_rewrite(ref, new_text, candidate_raw)
        elif ref.startswith("proj_"):
            _apply_project_rewrite(ref, new_text, candidate_raw)


def _apply_experience_rewrite(ref: str, new_text: str, candidate_raw: dict) -> None:
    experiences = candidate_raw.get("experience", [])
    for exp in experiences:
        if isinstance(exp, dict):
            if exp.get("id") == ref:
                exp["role_summary"] = new_text
                return
            for sub_key in ("highlights", "achievements"):
                subs = exp.get(sub_key, [])
                if isinstance(subs, list):
                    for sub in subs:
                        if isinstance(sub, dict) and sub.get("id") == ref:
                            if sub_key == "achievements":
                                sub["summary"] = new_text
                            else:
                                sub["text"] = new_text
                            return


def _apply_project_rewrite(ref: str, new_text: str, candidate_raw: dict) -> None:
    projects = candidate_raw.get("projects", [])
    for proj in projects:
        if isinstance(proj, dict):
            if proj.get("id") == ref:
                proj["description"] = new_text
                return
            highlights = proj.get("highlights", [])
            if isinstance(highlights, list):
                for hl in highlights:
                    if isinstance(hl, dict) and hl.get("id") == ref:
                        hl["text"] = new_text
                        return


def _convert_phone(raw: object) -> dict[str, str]:
    if isinstance(raw, dict):
        return {"value": raw.get("value", ""), "hyperlink": raw.get("hyperlink", "")}
    val = str(raw) if raw is not None else ""
    return {"value": val, "hyperlink": f"tel:{val.replace(' ', '')}"}


def _convert_payload_to_candidate_json(payload_with_ids: dict) -> dict:
    result: dict[str, Any] = {}

    personal = payload_with_ids.get("personal", {})
    if isinstance(personal, dict):
        personal_out: dict[str, Any] = {
            "name": personal.get("name", ""),
            "email": personal.get("email", ""),
            "phone": _convert_phone(personal.get("phone", "")),
            "location": personal.get("location", ""),
        }
        if personal.get("headline"):
            personal_out["headline"] = personal["headline"]
        if personal.get("links"):
            links_out = []
            for link in personal["links"]:
                if isinstance(link, dict):
                    links_out.append({
                        "label": link.get("label", ""),
                        "url": link.get("url", ""),
                    })
            if links_out:
                personal_out["links"] = links_out
        if personal.get("extra_links"):
            extra_links_out = []
            for link in personal["extra_links"]:
                if isinstance(link, dict):
                    extra_links_out.append({
                        "label": link.get("label", ""),
                        "url": link.get("url", ""),
                    })
            if extra_links_out:
                personal_out["extra_links"] = extra_links_out
        result["personal"] = personal_out

    summary_val = payload_with_ids.get("summary")
    if isinstance(summary_val, dict):
        result["summary"] = summary_val.get("text", "")
    elif isinstance(summary_val, str):
        result["summary"] = summary_val
    else:
        result["summary"] = ""

    target_role = payload_with_ids.get("target_role")
    if isinstance(target_role, dict):
        if target_role.get("text"):
            result["target_role"] = target_role["text"]
    elif isinstance(target_role, str) and target_role:
        result["target_role"] = target_role

    result["experience"] = _convert_experience_list(payload_with_ids.get("experience", []))
    result["education"] = _convert_education_list(payload_with_ids.get("education", []))
    result["skills"] = _convert_skills(payload_with_ids.get("skills"))
    result["projects"] = _convert_project_list(payload_with_ids.get("projects", []))
    result["certifications"] = _convert_certification_list(payload_with_ids.get("certifications", []))
    result["awards"] = _convert_award_list(payload_with_ids.get("awards", []))
    result["volunteer"] = _convert_volunteer_list(payload_with_ids.get("volunteer", []))
    result["languages"] = _convert_language_list(payload_with_ids.get("languages", []))

    for key in list(result.keys()):
        if isinstance(result[key], list) and not result[key]:
            del result[key]
        if isinstance(result[key], dict) and not result[key]:
            del result[key]

    return result


def _convert_experience_list(items: list) -> list[dict]:
    result: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        exp: dict[str, Any] = {
            "company": item.get("company", ""),
            "position": item.get("position", ""),
            "location": item.get("location", ""),
            "start_date": item.get("start_date", ""),
            "end_date": item.get("end_date"),
            "current": item.get("current", False),
        }
        if item.get("technologies"):
            exp["technologies"] = list(item["technologies"])
        if item.get("role_summary"):
            exp["role_summary"] = item["role_summary"]
        if item.get("scope"):
            exp["scope"] = item["scope"]
        if item.get("employment_type"):
            exp["employment_type"] = item["employment_type"]
        highlights = item.get("highlights", [])
        if isinstance(highlights, list) and highlights:
            exp["highlights"] = [h.get("text", "") if isinstance(h, dict) else h for h in highlights]
        achievements = item.get("achievements", [])
        if isinstance(achievements, list) and achievements:
            exp["achievements"] = [
                {k: v for k, v in a.items() if k != "id" and v}
                for a in achievements if isinstance(a, dict)
            ]
        result.append(exp)
    return result


def _convert_education_list(items: list) -> list[dict]:
    result: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        edu: dict[str, Any] = {
            "institution": item.get("institution", ""),
            "degree": item.get("degree", ""),
            "location": item.get("location", ""),
            "start_date": item.get("start_date", ""),
            "end_date": item.get("end_date", ""),
        }
        if item.get("gpa"):
            edu["gpa"] = item["gpa"]
        if item.get("honors"):
            edu["honors"] = item["honors"]
        result.append(edu)
    return result


def _convert_skills(skills_val: Any) -> dict | None:
    if not isinstance(skills_val, dict):
        return None
    cats = skills_val.get("categories", [])
    if not isinstance(cats, list) or not cats:
        return None
    categories_out: list[dict] = []
    for cat in cats:
        if not isinstance(cat, dict):
            continue
        items = cat.get("items", [])
        if isinstance(items, list):
            categories_out.append({
                "name": cat.get("name", ""),
                "items": [i.get("name", "") if isinstance(i, dict) else i for i in items],
            })
    if not categories_out:
        return None
    return {"categories": categories_out}


def _convert_project_list(items: list) -> list[dict]:
    result: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        proj: dict[str, Any] = {
            "name": item.get("name", ""),
            "description": item.get("description", ""),
        }
        if item.get("role"):
            proj["role"] = item["role"]
        if item.get("start_date"):
            proj["start_date"] = item["start_date"]
        if item.get("end_date"):
            proj["end_date"] = item["end_date"]
        if item.get("technologies"):
            proj["technologies"] = list(item["technologies"])
        if item.get("url"):
            proj["url"] = item["url"]
        highlights = item.get("highlights", [])
        if isinstance(highlights, list) and highlights:
            proj["highlights"] = [h.get("text", "") if isinstance(h, dict) else h for h in highlights]
        result.append(proj)
    return result


def _convert_certification_list(items: list) -> list[dict]:
    result: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        result.append({
            "name": item.get("name", ""),
            "issuer": item.get("issuer", ""),
            "date": item.get("date", ""),
        })
    return result


def _convert_award_list(items: list) -> list[dict]:
    result: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        award: dict[str, Any] = {
            "name": item.get("name", ""),
            "issuer": item.get("issuer", ""),
            "date": item.get("date", ""),
        }
        if item.get("description"):
            award["description"] = item["description"]
        result.append(award)
    return result


def _convert_volunteer_list(items: list) -> list[dict]:
    result: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        vol: dict[str, Any] = {
            "organization": item.get("organization", ""),
            "position": item.get("position", ""),
            "location": item.get("location", ""),
            "start_date": item.get("start_date", ""),
            "end_date": item.get("end_date"),
            "current": item.get("current", False),
        }
        highlights = item.get("highlights", [])
        if isinstance(highlights, list) and highlights:
            vol["highlights"] = [h.get("text", "") if isinstance(h, dict) else h for h in highlights]
        result.append(vol)
    return result


def _convert_language_list(items: list) -> list[dict]:
    result: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        result.append({
            "language": item.get("language", ""),
            "proficiency": item.get("proficiency", ""),
        })
    return result


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
    lines.append("           LLM-BASED CANDIDATE TAILORING REPORT")
    lines.append(sep)
    lines.append("")

    lines.append("DISCLAIMER")
    lines.append("-" * 70)
    lines.append(report.get("disclaimer", ""))
    lines.append("")

    lines.append(f"MODE:       {report.get('mode', 'unknown').upper()}")
    lines.append(f"INFERENCE:  {report.get('inference', 'unknown').upper()}")
    lines.append("")

    lines.append("EXECUTIVE SUMMARY")
    lines.append("-" * 70)
    lines.append(report.get("summary", ""))
    lines.append("")

    target_role = report.get("target_role", "")
    if target_role:
        lines.append("TARGET ROLE")
        lines.append("-" * 70)
        lines.append(target_role)
        lines.append("")

    key_changes = report.get("key_changes", [])
    if key_changes:
        lines.append("KEY CHANGES")
        lines.append("-" * 70)
        for change in key_changes:
            lines.append(f"  * {change.get('title', '')}")
            for detail in change.get("details", []):
                lines.append(f"    - {detail}")
        lines.append("")

    rewrites = report.get("rewrites", [])
    if rewrites:
        lines.append("REWRITES")
        lines.append("-" * 70)
        for rw in rewrites:
            kind = rw.get("target_kind", "unknown").replace("_", " ").title()
            refs = ", ".join(rw.get("target_refs", []))
            summary = rw.get("summary", "")
            lines.append(f"  * {kind} [{refs}]")
            lines.append(f"    {summary}")
        lines.append("")

    removed = report.get("removed_or_deprioritized_sections", [])
    if removed:
        lines.append("REMOVED / DEPRIORITIZED SECTIONS")
        lines.append("-" * 70)
        for sec in removed:
            decision = sec.get("decision", "unknown").upper()
            lines.append(f"  * {sec.get('section_name', '')} [{decision}]")
            lines.append(f"    {sec.get('reason', '')}")
        lines.append("")

    lint_before = report.get("lint_status_before", {})
    lint_after = report.get("lint_status_after", {})
    if lint_before or lint_after:
        lines.append("LINT STATUS")
        lines.append("-" * 70)
        before_status = lint_before.get("status", "unknown") if lint_before else "N/A"
        after_status = lint_after.get("status", "unknown") if lint_after else "N/A"
        lines.append(f"  Before: {before_status.upper()}")
        lines.append(f"  After:  {after_status.upper()}")
        for summary in lint_after.get("warning_summaries", []):
            lines.append(f"    WARN: {summary}")
        for summary in lint_after.get("failure_summaries", []):
            lines.append(f"    FAIL: {summary}")
        lines.append("")

    warnings = report.get("warnings", [])
    if warnings:
        lines.append("WARNINGS")
        lines.append("-" * 70)
        for w in warnings:
            lines.append(f"  ! {w}")
        lines.append("")

    return "\n".join(lines)


def render_markdown_report(report: dict) -> str:
    lines: list[str] = []

    lines.append("# LLM-Based Candidate Tailoring Report")
    lines.append("")

    lines.append("## Disclaimer")
    lines.append("")
    lines.append(report.get("disclaimer", ""))
    lines.append("")

    lines.append(f"- **Mode:** {report.get('mode', 'unknown').upper()}")
    lines.append(f"- **Inference:** {report.get('inference', 'unknown').upper()}")
    lines.append("")

    lines.append("## Executive Summary")
    lines.append("")
    lines.append(report.get("summary", ""))
    lines.append("")

    target_role = report.get("target_role", "")
    if target_role:
        lines.append("## Target Role")
        lines.append("")
        lines.append(target_role)
        lines.append("")

    key_changes = report.get("key_changes", [])
    if key_changes:
        lines.append("## Key Changes")
        lines.append("")
        for change in key_changes:
            lines.append(f"- **{change.get('title', '')}**")
            for detail in change.get("details", []):
                lines.append(f"  - {detail}")
        lines.append("")

    rewrites = report.get("rewrites", [])
    if rewrites:
        lines.append("## Rewrites")
        lines.append("")
        for rw in rewrites:
            kind = rw.get("target_kind", "unknown").replace("_", " ").title()
            refs = ", ".join(rw.get("target_refs", []))
            summary = rw.get("summary", "")
            lines.append(f"- **{kind}** [{refs}]")
            lines.append(f"  - {summary}")
        lines.append("")

    removed = report.get("removed_or_deprioritized_sections", [])
    if removed:
        lines.append("## Removed / Deprioritized Sections")
        lines.append("")
        for sec in removed:
            decision = sec.get("decision", "unknown").upper()
            lines.append(f"- **{sec.get('section_name', '')}** [{decision}]")
            lines.append(f"  - {sec.get('reason', '')}")
        lines.append("")

    lint_before = report.get("lint_status_before", {})
    lint_after = report.get("lint_status_after", {})
    if lint_before or lint_after:
        lines.append("## Lint Status")
        lines.append("")
        before_status = lint_before.get("status", "unknown") if lint_before else "N/A"
        after_status = lint_after.get("status", "unknown") if lint_after else "N/A"
        lines.append(f"- **Before:** {before_status.upper()}")
        lines.append(f"- **After:** {after_status.upper()}")
        for summary in lint_after.get("warning_summaries", []):
            lines.append(f"  - WARN: {summary}")
        for summary in lint_after.get("failure_summaries", []):
            lines.append(f"  - FAIL: {summary}")
        lines.append("")

    warnings = report.get("warnings", [])
    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def render_json_report(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False)


def _build_report_data(
    plan: dict,
    changes: list[str],
    rewrites: list[dict],
    lint_before: dict,
    lint_after: dict,
    locale: str,
    final_target_role: str,
) -> dict:
    key_changes: list[dict] = []

    if changes:
        key_changes.append({
            "title": "Structural changes",
            "details": changes,
        })

    rewrite_items: list[dict] = []
    for rw in plan.get("rewrite_requests", []):
        refs = rw.get("target_refs", [])
        actual_rewrite = None
        for rr in rewrites:
            if rr.get("target_refs") == refs:
                actual_rewrite = rr
                break
        rewrite_items.append({
            "target_kind": rw.get("target_kind", ""),
            "target_refs": refs,
            "summary": rw.get("instruction", ""),
            "grounding": [g.get("source_ref", "") for g in rw.get("grounding", [])],
        })

    removed_sections: list[dict] = []
    for decision in plan.get("section_decisions", []):
        if decision.get("decision") in ("remove", "deprioritize"):
            removed_sections.append({
                "section_name": decision.get("section_name", ""),
                "decision": decision.get("decision", ""),
                "reason": decision.get("reason", ""),
            })

    grounding_notes: list[dict] = []
    for note in plan.get("grounding_notes", []):
        grounding_notes.append({
            "claim": note.get("claim", ""),
            "source_summary": [g.get("source_ref", "") for g in note.get("grounding", [])],
        })

    return {
        "disclaimer": localized_disclaimer(locale),
        "mode": plan.get("mode", "conservative"),
        "inference": plan.get("inference", "medium"),
        "summary": plan.get("strategy_summary", ""),
        "target_role": final_target_role,
        "key_changes": key_changes,
        "rewrites": rewrite_items,
        "removed_or_deprioritized_sections": removed_sections,
        "grounding_notes": grounding_notes,
        "lint_status_before": lint_before,
        "lint_status_after": lint_after,
        "warnings": plan.get("warnings", []),
    }


def save_tailor_log_zip(
    log_path: str,
    meta: dict,
    candidate_input_payload: dict,
    vacancy_text: str,
    extra_contexts: list[str] | None,
    candidate_schema: dict,
    plan_schema: dict,
    report_schema: dict,
    rewrite_response_schema: dict,
    prompt_text: str,
    plan_raw_response: str,
    validated_plan: dict | None,
    rewrite_request_responses: list[dict] | None,
    final_candidate_json: dict | None,
    report_data: dict | None,
    lint_before_summary: dict,
    lint_after_summary: dict,
) -> None:
    try:
        with StagedLogArchive(log_path, prefix="hirepaper-content-tailor-log-") as archive:
            archive.write_json("meta.json", meta)
            archive.write_json("candidate-input-payload.json", candidate_input_payload)
            archive.write_text("vacancy.txt", vacancy_text)
            if extra_contexts:
                for i, ctx in enumerate(extra_contexts):
                    archive.write_text(f"extra-context-{i + 1}.txt", ctx)
            archive.write_json("candidate-schema.json", candidate_schema)
            archive.write_json("tailor-plan-schema.json", plan_schema)
            archive.write_json("tailor-report-schema.json", report_schema)
            archive.write_json("rewrite-response-schema.json", rewrite_response_schema)
            archive.write_text("prompt.txt", prompt_text)
            archive.write_json("plan-raw-response.json", {"raw_text": plan_raw_response})
            if validated_plan is not None:
                archive.write_json("validated-plan.json", validated_plan)
            if rewrite_request_responses:
                archive.write_json("rewrite-responses.json", rewrite_request_responses)
            if final_candidate_json is not None:
                archive.write_json("final-tailored-candidate.json", final_candidate_json)
            if report_data is not None:
                archive.write_json("tailor-report.json", report_data)
            archive.write_json("lint-before.json", lint_before_summary)
            archive.write_json("lint-after.json", lint_after_summary)
            archive.finalize()
    except LogArchiveError as e:
        raise ContentTailorError(str(e))


def run_tailor(
    candidate_path: str,
    vacancy_path: str,
    config: LLMConfig,
    mode: str,
    inference: str,
    locale: str,
    report_format: str,
    output_path: str,
    report_output_path: str | None,
    log_path: str | None,
    prompt_text: str,
    extra_context_paths: list[str] | None,
    timeout_seconds: int | None,
    max_tokens: int | None,
    verbose: int,
) -> tuple[str, dict | None, dict | None]:
    if mode not in _VALID_MODES:
        raise ContentTailorError(f"unsupported --mode '{mode}' (supported: conservative, rewrite)")
    if inference not in _VALID_INFERENCE:
        raise ContentTailorError(f"unsupported --inference '{inference}' (supported: low, medium, high)")
    if report_format not in _VALID_REPORT_FORMATS:
        raise ContentTailorError(f"unsupported --report-format '{report_format}' (supported: text, json)")

    candidate_file = Path(candidate_path)
    if not candidate_file.exists():
        raise ContentTailorError(f"candidate file not found: {candidate_path}")
    try:
        candidate = load_candidate(candidate_file)
    except (ValueError, KeyError) as e:
        raise ContentTailorError(f"invalid candidate data: {e}")

    _stdout_redirect = io.StringIO()
    with contextlib.redirect_stdout(_stdout_redirect):
        lint_code_before = lint_candidate(candidate)
    lint_output_before = _stdout_redirect.getvalue()
    lint_before_summary = _parse_lint_output(lint_output_before)

    if lint_code_before != 0:
        sys.stderr.write(lint_output_before)
        raise ContentTailorError(
            "Content lint FAILED — tailoring aborted. "
            "Fix candidate data quality issues before tailoring."
        )

    if verbose > 0:
        sys.stderr.write(lint_output_before)

    vacancy_file = Path(vacancy_path)
    if not vacancy_file.exists():
        raise ContentTailorError(f"vacancy file not found: {vacancy_path}")
    try:
        vacancy_text = vacancy_file.read_text(encoding="utf-8")
    except OSError as e:
        raise ContentTailorError(f"cannot read vacancy file: {vacancy_path} — {e}")
    if not vacancy_text.strip():
        raise ContentTailorError(f"vacancy file is empty: {vacancy_path}")

    extra_contexts: list[str] = []
    if extra_context_paths:
        for ctx_path in extra_context_paths:
            ctx_file = Path(ctx_path)
            if not ctx_file.exists():
                raise ContentTailorError(f"extra-context file not found: {ctx_path}")
            try:
                ctx_text = ctx_file.read_text(encoding="utf-8")
            except OSError as e:
                raise ContentTailorError(f"cannot read extra-context file: {ctx_path} — {e}")
            if not ctx_text.strip():
                raise ContentTailorError(f"extra-context file is empty: {ctx_path}")
            extra_contexts.append(ctx_text)

    candidate_payload = _build_candidate_payload_with_ids(candidate)
    candidate_schema = load_candidate_schema()
    plan_schema = load_tailor_plan_schema()
    report_schema = load_tailor_report_schema()
    rewrite_response_schema = load_rewrite_response_schema()
    llm_plan_schema = _build_llm_output_schema(plan_schema)
    llm_rewrite_response_schema = _build_llm_output_schema(rewrite_response_schema)

    effective_config = _build_effective_config(config, timeout_seconds, max_tokens)

    plan_max_tokens = max(effective_config.max_tokens, 32768)
    plan_timeout = max(effective_config.timeout_seconds, 120)
    plan_effective_config = _build_effective_config(
        config, timeout_seconds=plan_timeout, max_tokens=plan_max_tokens,
    )

    plan_messages = build_plan_messages(
        candidate_payload=candidate_payload,
        vacancy_text=vacancy_text,
        prompt=prompt_text,
        mode=mode,
        inference=inference,
        locale=locale,
        candidate_schema=candidate_schema,
        plan_schema=llm_plan_schema,
        extra_contexts=extra_contexts if extra_contexts else None,
    )

    plan_response_text: str = ""
    plan_usage: dict | None = None
    validated_plan: dict | None = None
    plan_status = "success"

    spinner_stop = threading.Event()

    def _spin():
        chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        i = 0
        while not spinner_stop.is_set():
            sys.stderr.write(f"\r{chars[i]} Generating tailoring plan... ")
            sys.stderr.flush()
            i = (i + 1) % len(chars)
            time.sleep(0.1)
        sys.stderr.write("\r\033[K")
        sys.stderr.flush()

    spinner = threading.Thread(target=_spin, daemon=True)
    spinner.start()

    try:
        response = _complete(plan_effective_config, plan_messages)
    except LLMClientError as e:
        spinner_stop.set()
        spinner.join()
        plan_status = "failed"
        raise ContentTailorError(f"LLM plan request failed: {e}")
    finally:
        spinner_stop.set()
        spinner.join()

    finish_reason = None
    try:
        finish_reason = response.choices[0].finish_reason
    except (AttributeError, IndexError, TypeError):
        pass

    plan_response_text = ""
    try:
        plan_response_text = _extract_text(response)
    except LLMClientError:
        if finish_reason != "length":
            raise ContentTailorError("LLM plan response has no usable text")

    if finish_reason == "length":
        snippet = plan_response_text[-200:] if len(plan_response_text) > 200 else plan_response_text
        raise ContentTailorError(
            f"LLM plan response was truncated (finish_reason=length). "
            f"The model hit the token limit before completing the plan JSON. "
            f"Raw response tail: ...{repr(snippet)}"
        )

    try:
        plan_usage = _extract_usage(response)
    except LLMClientError:
        plan_usage = None

    try:
        validated_plan = parse_and_validate_response(plan_response_text, plan_schema)
    except ContentTailorError:
        plan_status = "failed"
        raise

    candidate_raw = copy.deepcopy(candidate_payload)
    candidate_raw, structural_changes = _apply_structural_actions(validated_plan, candidate_raw)

    rewrite_results: list[dict] = []
    rewrite_stage_used = False

    all_rewrite_requests = validated_plan.get("rewrite_requests", [])
    _ALWAYS_REWRITE_KINDS = frozenset({"headline", "summary", "target_role"})
    always_rewrites = [
        rw for rw in all_rewrite_requests
        if rw.get("target_kind") in _ALWAYS_REWRITE_KINDS
    ]
    mode_rewrites = [
        rw for rw in all_rewrite_requests
        if rw.get("target_kind") not in _ALWAYS_REWRITE_KINDS
    ]

    process_rewrites = list(always_rewrites)
    if mode == "rewrite":
        process_rewrites.extend(mode_rewrites)

    if process_rewrites:
        rewrite_stage_used = True
        rewrite_spinner_stop = threading.Event()

        def _rewrite_spin():
            chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            i = 0
            while not rewrite_spinner_stop.is_set():
                sys.stderr.write(f"\r{chars[i]} Applying rewrites... ")
                sys.stderr.flush()
                i = (i + 1) % len(chars)
                time.sleep(0.1)
            sys.stderr.write("\r\033[K")
            sys.stderr.flush()

        for rw_request in process_rewrites:
            rw_messages = _build_rewrite_messages(
                rewrite_request=rw_request,
                candidate_payload=candidate_raw,
                locale=locale,
                mode=mode,
                inference=inference,
                rewrite_response_schema=llm_rewrite_response_schema,
            )

            rw_spinner = threading.Thread(target=_rewrite_spin, daemon=True)
            rw_spinner.start()
            try:
                rw_response = _complete(effective_config, rw_messages)
            except LLMClientError as e:
                rewrite_spinner_stop.set()
                raise ContentTailorError(f"LLM rewrite request failed: {e}")
            finally:
                rewrite_spinner_stop.set()
                rw_spinner.join()

            rw_finish_reason = None
            try:
                rw_finish_reason = rw_response.choices[0].finish_reason
            except (AttributeError, IndexError, TypeError):
                pass

            rw_text = ""
            try:
                rw_text = _extract_text(rw_response)
            except LLMClientError:
                if rw_finish_reason != "length":
                    raise ContentTailorError(
                        f"LLM rewrite response has no usable text for request "
                        f"'{rw_request.get('target_kind', '?')}' targeting "
                        f"{rw_request.get('target_refs', [])!r}"
                    )

            if rw_finish_reason == "length":
                raise ContentTailorError(
                    "LLM rewrite response was truncated (finish_reason=length). "
                    "The model hit the token limit before completing the rewrite JSON."
                )

            validated_rw = parse_and_validate_rewrite_response(
                rw_text,
                rewrite_response_schema,
                rw_request,
            )
            rewrites_dict = validated_rw.get("rewrites", {})
            _apply_rewrite_to_payload(
                rw_request.get("target_kind", ""),
                rewrites_dict,
                candidate_raw,
            )

            rewrite_results.append({
                "target_kind": rw_request.get("target_kind", ""),
                "target_refs": rw_request.get("target_refs", []),
                "request": rw_request.get("instruction", ""),
                "response": validated_rw,
            })

    final_target_role = validated_plan.get("target_role", {}).get("proposed_value", "")

    final_candidate_json = _convert_payload_to_candidate_json(candidate_raw)

    if final_target_role:
        final_candidate_json["target_role"] = final_target_role

    try:
        _validate_candidate_json(final_candidate_json, candidate_schema)
        temp_path = Path(candidate_path + ".tailor-tmp.json")
        temp_path.write_text(json.dumps(final_candidate_json, indent=2, ensure_ascii=False), encoding="utf-8")
        load_candidate(temp_path)
        temp_path.unlink()
    except (ValueError, KeyError, OSError, ContentTailorError) as e:
        raise ContentTailorError(f"Final tailored JSON validation failed: {e}")

    lint_after_summary: dict = {
        "status": "not_run",
        "ok": 0,
        "warn": 0,
        "fail": 0,
        "warning_summaries": [],
        "failure_summaries": [],
    }
    try:
        temp_lint_path = Path(candidate_path + ".tailor-lint-tmp.json")
        temp_lint_path.write_text(json.dumps(final_candidate_json, indent=2, ensure_ascii=False), encoding="utf-8")
        temp_candidate = load_candidate(temp_lint_path)
        _stdout_redirect2 = io.StringIO()
        with contextlib.redirect_stdout(_stdout_redirect2):
            lint_code_after = lint_candidate(temp_candidate)
        lint_output_after = _stdout_redirect2.getvalue()
        lint_after_summary = _parse_lint_output(lint_output_after)
        temp_lint_path.unlink()
        if verbose > 0:
            sys.stderr.write(lint_output_after)
    except (ValueError, KeyError, OSError) as e:
        raise ContentTailorError(f"Final lint validation failed: {e}")

    if lint_code_after != 0:
        raise ContentTailorError(
            "Final tailored candidate FAILED content lint. "
            "Review the tailored JSON and ensure it is complete and valid."
        )

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        out_path.write_text(
            json.dumps(final_candidate_json, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as e:
        raise ContentTailorError(f"cannot write output: {output_path} — {e}")

    report_data = _build_report_data(
        plan=validated_plan,
        changes=structural_changes,
        rewrites=rewrite_results,
        lint_before=lint_before_summary,
        lint_after=lint_after_summary,
        locale=locale,
        final_target_role=final_target_role,
    )
    _validate_report(report_data, report_schema)

    if report_format == "json":
        report_str = render_json_report(report_data)
    elif report_format == "md":
        report_str = render_markdown_report(report_data)
    else:
        report_str = render_text_report(report_data)

    if report_output_path:
        report_path = Path(report_output_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            report_path.write_text(report_str, encoding="utf-8")
        except OSError as e:
            raise ContentTailorError(f"cannot write report output: {report_output_path} — {e}")

    meta = {
        "command": _build_command_string(
            candidate_path, vacancy_path, config.config_path,
            mode, inference, locale, report_format,
            output_path, report_output_path, log_path,
            extra_context_paths, timeout_seconds, max_tokens,
        ),
        "timestamp_utc": _utcnow_iso(),
        "candidate_path": candidate_path,
        "vacancy_path": vacancy_path,
        "extra_context_paths": extra_context_paths or [],
        "output_path": output_path,
        "report_output_path": report_output_path or "",
        "report_format": report_format,
        "log_path": log_path or "",
        "mode": mode,
        "inference": inference,
        "locale": locale,
        "model": config.model,
        "base_url": config.base_url,
        "timeout_seconds": effective_config.timeout_seconds,
        "max_tokens": effective_config.max_tokens,
        "lint_status_before": lint_before_summary.get("status", "unknown"),
        "lint_status_after": lint_after_summary.get("status", "unknown"),
        "tailoring_status": "success",
        "rewrite_stage_used": rewrite_stage_used,
        "plan_llm_call_status": plan_status,
    }

    if log_path:
        save_tailor_log_zip(
            log_path=log_path,
            meta=meta,
            candidate_input_payload=candidate_payload,
            vacancy_text=vacancy_text,
            extra_contexts=extra_contexts if extra_contexts else None,
            candidate_schema=candidate_schema,
            plan_schema=plan_schema,
            report_schema=report_schema,
            rewrite_response_schema=rewrite_response_schema,
            prompt_text=prompt_text,
            plan_raw_response=plan_response_text,
            validated_plan=validated_plan,
            rewrite_request_responses=rewrite_results if rewrite_results else None,
            final_candidate_json=final_candidate_json,
            report_data=report_data,
            lint_before_summary=lint_before_summary,
            lint_after_summary=lint_after_summary,
        )

    return report_str, report_data, meta


def _build_command_string(
    candidate_path: str,
    vacancy_path: str,
    config_path: str | None,
    mode: str,
    inference: str,
    locale: str,
    report_format: str,
    output_path: str,
    report_output_path: str | None,
    log_path: str | None,
    extra_context_paths: list[str] | None,
    timeout_seconds: int | None,
    max_tokens: int | None,
) -> str:
    parts = [
        "hirepaper content tailor",
        candidate_path,
        vacancy_path,
    ]
    if config_path:
        parts.extend(["--config", config_path])
    if locale != "en":
        parts.extend(["--locale", locale])
    if mode != "conservative":
        parts.extend(["--mode", mode])
    if inference != "medium":
        parts.extend(["--inference", inference])
    if report_format != "text":
        parts.extend(["--report-format", report_format])
    parts.extend(["--output", output_path])
    if report_output_path:
        parts.extend(["--report-output", report_output_path])
    if log_path:
        parts.extend(["--log", log_path])
    if extra_context_paths:
        for ctx in extra_context_paths:
            parts.extend(["--extra-context", ctx])
    if timeout_seconds is not None:
        parts.extend(["--timeout-seconds", str(timeout_seconds)])
    if max_tokens is not None:
        parts.extend(["--max-tokens", str(max_tokens)])
    return " ".join(parts)
