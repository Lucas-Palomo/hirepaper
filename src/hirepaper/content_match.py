from __future__ import annotations

import contextlib
import io
import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from ._resources import prompts_dir, schemas_dir
from .content_lint import lint_candidate
from .log_archive import LogArchiveError, StagedLogArchive
from .llm.client import LLMClientError, _complete, _extract_text, _extract_usage
from .llm.config import LLMConfig
from .loader import load_candidate
from .models import Candidate

_MATCH_DEFAULT_INFERENCE = "medium"

_RATING_BANDS: list[tuple[int, int, str]] = [
    (90, 100, "strong"),
    (75, 89, "good"),
    (60, 74, "partial"),
    (40, 59, "weak"),
    (0, 39, "poor"),
]
_VALID_RATINGS = {r for (_, _, r) in _RATING_BANDS}
_VALID_INFERENCE = frozenset({"low", "medium", "high"})
_VALID_FORMATS = frozenset({"text", "md", "json"})
_VALID_PRIORITY = frozenset({"must_have", "should_have", "nice_to_have", "unknown"})
_VALID_ASSESSMENT = frozenset({"matched", "partially_matched", "not_matched", "unclear"})
_VALID_CONFIDENCE = frozenset({"low", "medium", "high"})
_VALID_SEVERITY = frozenset({"low", "medium", "high"})
_RESULT_SCHEMA_NAME = "content-match-result.schema.json"


class ContentMatchError(Exception):
    pass


class MatchPolicy:
    def __init__(self, strict: bool, inference: str, locale: str):
        self.strict = strict
        self.inference = inference
        self.locale = locale

    def validate(self) -> None:
        if self.inference not in _VALID_INFERENCE:
            raise ContentMatchError(
                f"unsupported --inference '{self.inference}' "
                "(supported: low, medium, high)"
            )
        if self.strict and self.inference != "low":
            raise ContentMatchError(
                "--strict requires --inference=low; "
                f"got --inference={self.inference}"
            )


def _build_candidate_payload(candidate: Candidate) -> dict:
    payload: dict = {}

    p = candidate.personal
    personal: dict[str, object] = {
        "name": p.name,
        "headline": p.headline or "",
        "email": p.email,
        "phone": p.phone.value,
        "location": p.location,
    }
    if p.links:
        personal["links"] = [{"label": lnk.label, "url": lnk.url} for lnk in p.links]
    if p.extra_links:
        personal["extra_links"] = [{"label": lnk.label, "url": lnk.url} for lnk in p.extra_links]
    payload["personal"] = personal

    payload["target_role"] = candidate.target_role or ""
    payload["summary"] = candidate.summary

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

    if candidate.skills:
        payload["skills"] = {
            "categories": [
                {"name": cat.name, "items": cat.items}
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
        {"name": c.name, "issuer": c.issuer, "date": c.date}
        for c in candidate.certifications
    ]

    payload["awards"] = [
        {"name": a.name, "issuer": a.issuer, "date": a.date, "description": a.description or ""}
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


def load_default_prompt() -> str:
    path = prompts_dir() / "content-match-default.txt"
    if not path.exists():
        raise ContentMatchError(f"default prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def load_prompt(prompt_path: str | None) -> str:
    if prompt_path is not None:
        path = Path(prompt_path)
        if not path.exists():
            raise ContentMatchError(f"prompt file not found: {prompt_path}")
        try:
            return path.read_text(encoding="utf-8")
        except OSError as e:
            raise ContentMatchError(f"prompt file read error: {prompt_path} — {e}")
    return load_default_prompt()


def load_result_schema() -> dict:
    path = schemas_dir() / _RESULT_SCHEMA_NAME
    if not path.exists():
        raise ContentMatchError(f"result schema not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise ContentMatchError(f"result schema read error: {path} — {e}")
    except json.JSONDecodeError as e:
        raise ContentMatchError(f"invalid result schema JSON: {path} — {e}")
    return raw


def build_llm_result_schema(public_schema: dict) -> dict:
    llm_schema = json.loads(json.dumps(public_schema))
    required = llm_schema.get("required", [])
    llm_schema["required"] = [field for field in required if field != "disclaimer"]
    properties = llm_schema.get("properties", {})
    if isinstance(properties, dict):
        properties.pop("disclaimer", None)
    return llm_schema


def localized_disclaimer(locale: str) -> str:
    normalized = locale.replace("_", "-").lower()
    if normalized.startswith("pt"):
        return (
            "Esta analise usa um LLM e pode conter julgamento subjetivo. "
            "Revise as evidencias antes de tomar decisoes."
        )
    return (
        "This analysis uses an LLM and may contain subjective judgment. "
        "Review the evidence before making decisions."
    )


def _build_public_result(llm_result: dict, locale: str) -> dict:
    public_result = dict(llm_result)
    public_result["disclaimer"] = localized_disclaimer(locale)
    return public_result


def _build_effective_config(
    config: LLMConfig,
    timeout_seconds: int | None,
    max_tokens: int | None,
) -> LLMConfig:
    effective_timeout = timeout_seconds if timeout_seconds is not None else config.timeout_seconds
    effective_max_tokens = max_tokens if max_tokens is not None else config.max_tokens

    if effective_timeout <= 0:
        raise ContentMatchError("--timeout-seconds must be greater than zero")
    if effective_max_tokens <= 0:
        raise ContentMatchError("--max-tokens must be greater than zero")

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


def build_messages(
    candidate_payload: dict,
    vacancy_text: str,
    prompt: str,
    policy: MatchPolicy,
    result_schema: dict,
) -> list[dict]:
    system_msg = prompt.format(
        locale=policy.locale,
        strict=str(policy.strict).lower(),
        inference=policy.inference,
    )

    candidate_json = json.dumps(candidate_payload, indent=2, ensure_ascii=False)
    locale_instruction = (
        f"Write all natural-language fields in {policy.locale}.\n"
        if policy.locale != "en"
        else ""
    )
    strict_instruction = (
        "STRICT MODE: Use only explicit evidence. "
        "Minimize inference. --inference=low is active.\n"
        if policy.strict
        else ""
    )
    inference_instruction = (
        f"Inference level: {policy.inference}.\n"
    )
    schema_json = json.dumps(result_schema, indent=2, ensure_ascii=False)

    user_content = (
        f"{locale_instruction}{strict_instruction}{inference_instruction}\n"
        f"Output schema (use this exact JSON contract):\n"
        f"```json\n{schema_json}\n```\n\n"
        f"Candidate payload:\n"
        f"```json\n{candidate_json}\n```\n\n"
        f"Vacancy text:\n"
        f"```\n{vacancy_text}\n```"
    )

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_content},
    ]


def _rating_for_score(score: int) -> str:
    for lo, hi, rating in _RATING_BANDS:
        if lo <= score <= hi:
            return rating
    return "poor"


def _schema_error(path: list[str], message: str) -> ContentMatchError:
    location = ".".join(path)
    if location:
        return ContentMatchError(f"LLM response does not match schema at '{location}': {message}")
    return ContentMatchError(f"LLM response does not match schema: {message}")


def _resolve_schema_ref(root_schema: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        raise ContentMatchError(f"unsupported schema ref: {ref}")
    node: object = root_schema
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            raise ContentMatchError(f"invalid schema ref: {ref}")
        node = node[part]
    if not isinstance(node, dict):
        raise ContentMatchError(f"invalid schema ref target: {ref}")
    return node


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

    enum = schema.get("enum")
    if isinstance(enum, list) and value not in enum:
        raise _schema_error(path, f"value {value!r} is not one of {', '.join(map(str, enum))}")


def _validate_result(result: dict, result_schema: dict) -> None:
    _validate_against_schema(result, result_schema, result_schema, [])

    score = result["score"]
    if not isinstance(score, (int, float)):
        raise ContentMatchError(f"LLM response: 'score' must be numeric, got {type(score).__name__}")
    score_int = int(score)
    if not (0 <= score_int <= 100):
        raise ContentMatchError(f"LLM response: 'score' {score_int} out of range [0, 100]")

    rating = result["rating"]
    if rating not in _VALID_RATINGS:
        raise ContentMatchError(
            f"LLM response: invalid 'rating' {rating!r}; "
            f"must be one of {', '.join(sorted(_VALID_RATINGS))}"
        )
    expected_rating = _rating_for_score(score_int)
    if rating != expected_rating:
        raise ContentMatchError(
            f"LLM response: 'rating' {rating!r} does not match score band "
            f"for score {score_int} (expected {expected_rating!r})"
        )

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


def parse_and_validate_response(raw_text: str, result_schema: dict) -> dict:
    stripped = _strip_json_fence(raw_text)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise ContentMatchError(
            f"LLM response is not valid JSON: {e}\n\nRaw response:\n{raw_text}"
        )
    if not isinstance(parsed, dict):
        raise ContentMatchError(
            f"LLM response is not a JSON object (got {type(parsed).__name__})"
        )
    _validate_result(parsed, result_schema)
    return parsed


def render_text_report(result: dict) -> str:
    lines: list[str] = []

    sep = "=" * 70
    lines.append(sep)
    lines.append("           LLM-BASED ATS COMPATIBILITY ANALYSIS")
    lines.append(sep)
    lines.append("")

    lines.append("DISCLAIMER")
    lines.append("-" * 70)
    lines.append(result["disclaimer"])
    lines.append("")

    lines.append(f"SCORE:      {result['score']}/100")
    lines.append(f"RATING:     {result['rating'].upper()}")
    lines.append(f"VERDICT:    {result['verdict']}")
    lines.append("")

    lines.append("EXECUTIVE SUMMARY")
    lines.append("-" * 70)
    lines.append(result["summary"])
    lines.append("")

    strengths = result.get("strengths", [])
    if strengths:
        lines.append("STRENGTHS")
        lines.append("-" * 70)
        for i, s in enumerate(strengths, 1):
            lines.append(f"  {i}. {s['title']}")
            for ev in s.get("evidence", []):
                lines.append(f"     - {ev}")
        lines.append("")

    gaps = result.get("gaps", [])
    if gaps:
        lines.append("GAPS")
        lines.append("-" * 70)
        for i, g in enumerate(gaps, 1):
            severity = g.get("severity", "unknown").upper()
            lines.append(f"  {i}. {g['title']}  [{severity}]")
            for ev in g.get("evidence", []):
                lines.append(f"     - {ev}")
        lines.append("")

    matched = result.get("matched_requirements", [])
    if matched:
        lines.append("MATCHED REQUIREMENTS")
        lines.append("-" * 70)
        for i, m in enumerate(matched, 1):
            priority = m.get("priority", "unknown")
            confidence = m.get("confidence", "unknown")
            lines.append(f"  {i}. {m['requirement']} ({priority}) -> matched [{confidence}]")
            for ev in m.get("evidence", []):
                lines.append(f"     - {ev}")
        lines.append("")

    unmatched = result.get("unmatched_requirements", [])
    if unmatched:
        lines.append("UNMATCHED REQUIREMENTS")
        lines.append("-" * 70)
        for i, u in enumerate(unmatched, 1):
            priority = u.get("priority", "unknown")
            assessment = u.get("assessment", "unknown")
            confidence = u.get("confidence", "unknown")
            lines.append(f"  {i}. {u['requirement']} ({priority}) -> {assessment} [{confidence}]")
            for ev in u.get("evidence", []):
                lines.append(f"     - {ev}")
        lines.append("")

    inferences = result.get("inferences", [])
    if inferences:
        lines.append("INFERENCES")
        lines.append("-" * 70)
        for i, inf in enumerate(inferences, 1):
            lines.append(f"  {i}. {inf['claim']}")
            lines.append(f"     Basis: {inf['basis']}")
            lines.append(f"     Confidence: {inf.get('confidence', 'unknown')}")
        lines.append("")

    return "\n".join(lines)


def render_markdown_report(result: dict) -> str:
    lines: list[str] = []

    lines.append("# ATS Compatibility Analysis")
    lines.append("")

    lines.append("## Disclaimer")
    lines.append("")
    lines.append(result["disclaimer"])
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(result["summary"])
    lines.append("")

    lines.append("## Score")
    lines.append("")
    lines.append(f"- **Score:** {result['score']}/100")
    lines.append(f"- **Rating:** {result['rating'].upper()}")
    lines.append(f"- **Verdict:** {result['verdict']}")
    lines.append("")

    strengths = result.get("strengths", [])
    if strengths:
        lines.append("## Strengths")
        lines.append("")
        for s in strengths:
            lines.append(f"- **{s['title']}**")
            for ev in s.get("evidence", []):
                lines.append(f"  - {ev}")
        lines.append("")

    gaps = result.get("gaps", [])
    if gaps:
        lines.append("## Gaps")
        lines.append("")
        for g in gaps:
            severity = g.get("severity", "unknown").upper()
            lines.append(f"- **{g['title']}** [{severity}]")
            for ev in g.get("evidence", []):
                lines.append(f"  - {ev}")
        lines.append("")

    matched = result.get("matched_requirements", [])
    if matched:
        lines.append("## Matched Requirements")
        lines.append("")
        for m in matched:
            priority = m.get("priority", "unknown")
            confidence = m.get("confidence", "unknown")
            lines.append(f"- **{m['requirement']}** ({priority}) &rarr; matched [{confidence}]")
            for ev in m.get("evidence", []):
                lines.append(f"  - {ev}")
        lines.append("")

    unmatched = result.get("unmatched_requirements", [])
    if unmatched:
        lines.append("## Unmatched Requirements")
        lines.append("")
        for u in unmatched:
            priority = u.get("priority", "unknown")
            assessment = u.get("assessment", "unknown")
            confidence = u.get("confidence", "unknown")
            lines.append(f"- **{u['requirement']}** ({priority}) &rarr; {assessment} [{confidence}]")
            for ev in u.get("evidence", []):
                lines.append(f"  - {ev}")
        lines.append("")

    inferences = result.get("inferences", [])
    if inferences:
        lines.append("## Inferences")
        lines.append("")
        for inf in inferences:
            lines.append(f"- **{inf['claim']}**")
            lines.append(f"  - Basis: {inf['basis']}")
            lines.append(f"  - Confidence: {inf.get('confidence', 'unknown')}")
        lines.append("")

    return "\n".join(lines)


def render_json_output(result: dict) -> str:
    return json.dumps(result, indent=2, ensure_ascii=False)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def save_log_zip(
    log_path: str,
    meta: dict,
    result_schema: dict,
    prompt_text: str,
    candidate_payload: dict,
    vacancy_text: str,
    raw_response: str,
    validated_result: dict | None,
    usage: dict | None,
) -> None:
    try:
        with StagedLogArchive(log_path, prefix="hirepaper-content-match-log-") as archive:
            archive.write_json("meta.json", meta)
            archive.write_json("result-schema.json", result_schema)
            archive.write_text("prompt.txt", prompt_text)
            archive.write_json("candidate-payload.json", candidate_payload)
            archive.write_text("vacancy.txt", vacancy_text)
            archive.write_json("raw-response.json", {"raw_text": raw_response})
            if validated_result is not None:
                archive.write_json("validated-result.json", validated_result)
            if usage is not None:
                archive.write_json("usage.json", usage)
            archive.finalize()
    except LogArchiveError as e:
        raise ContentMatchError(str(e))


def run_match(
    candidate_path: str,
    vacancy_path: str,
    config: LLMConfig,
    policy: MatchPolicy,
    prompt_source: str,
    prompt_text: str,
    format: str = "text",
    output_path: str | None = None,
    log_path: str | None = None,
    timeout_seconds: int | None = None,
    max_tokens: int | None = None,
    verbose: int = 0,
) -> tuple[str, dict | None, dict | None]:
    policy.validate()

    candidate_file = Path(candidate_path)
    if not candidate_file.exists():
        raise ContentMatchError(f"candidate file not found: {candidate_path}")

    try:
        candidate = load_candidate(candidate_file)
    except (ValueError, KeyError) as e:
        raise ContentMatchError(f"invalid candidate data: {e}")

    _stdout_redirect = io.StringIO()
    with contextlib.redirect_stdout(_stdout_redirect):
        lint_code = lint_candidate(candidate)
    lint_output = _stdout_redirect.getvalue()

    if lint_code != 0:
        sys.stderr.write(lint_output)
        raise ContentMatchError(
            "Content lint FAILED — matching aborted. "
            "Fix candidate data quality issues before matching."
        )

    if verbose > 0:
        sys.stderr.write(lint_output)

    vacancy_file = Path(vacancy_path)
    if not vacancy_file.exists():
        raise ContentMatchError(f"vacancy file not found: {vacancy_path}")
    try:
        vacancy_text = vacancy_file.read_text(encoding="utf-8")
    except OSError as e:
        raise ContentMatchError(f"cannot read vacancy file: {vacancy_path} — {e}")
    if not vacancy_text.strip():
        raise ContentMatchError(f"vacancy file is empty: {vacancy_path}")

    candidate_payload = _build_candidate_payload(candidate)
    public_result_schema = load_result_schema()
    llm_result_schema = build_llm_result_schema(public_result_schema)
    effective_config = _build_effective_config(config, timeout_seconds, max_tokens)

    messages = build_messages(candidate_payload, vacancy_text, prompt_text, policy, llm_result_schema)
    raw_response_text: str = ""
    usage: dict | None = None
    llm_validated: dict | None = None
    validated: dict | None = None
    llm_call_status = "success"

    spinner_stop = threading.Event()

    def _spin():
        chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        i = 0
        while not spinner_stop.is_set():
            sys.stderr.write(f"\r{chars[i]} Analyzing candidate against vacancy... ")
            sys.stderr.flush()
            i = (i + 1) % len(chars)
            time.sleep(0.1)
        sys.stderr.write("\r\033[K")
        sys.stderr.flush()

    spinner = threading.Thread(target=_spin, daemon=True)
    spinner.start()

    try:
        response = _complete(effective_config, messages)
    except LLMClientError as e:
        spinner_stop.set()
        spinner.join()
        llm_call_status = "failed"
        raise ContentMatchError(f"LLM request failed: {e}")
    finally:
        spinner_stop.set()
        spinner.join()

    raw_response_text = _extract_text(response)

    finish_reason = None
    try:
        finish_reason = response.choices[0].finish_reason
    except (AttributeError, IndexError, TypeError):
        pass

    if finish_reason == "length":
        snippet = raw_response_text[-200:] if len(raw_response_text) > 200 else raw_response_text
        raise ContentMatchError(
            f"LLM response was truncated (finish_reason=length). "
            f"The model hit the token limit before completing the JSON output. "
            f"Raw response tail: ...{repr(snippet)}"
        )

    try:
        usage = _extract_usage(response)
    except LLMClientError:
        usage = None

    try:
        llm_validated = parse_and_validate_response(raw_response_text, llm_result_schema)
        validated = _build_public_result(llm_validated, policy.locale)
        _validate_result(validated, public_result_schema)
    except ContentMatchError:
        llm_call_status = "failed"
        raise

    if "Result: PASS with warnings" in lint_output:
        lint_status = "warning"
    else:
        lint_status = "pass"

    meta = {
        "command": _build_command_string(
            candidate_path,
            vacancy_path,
            config.config_path,
            policy,
            format,
            output_path,
            log_path,
            timeout_seconds,
            max_tokens,
        ),
        "timestamp_utc": _utcnow_iso(),
        "locale": policy.locale,
        "format": format,
        "strict": policy.strict,
        "inference": policy.inference,
        "model": config.model,
        "base_url": config.base_url,
        "timeout_seconds": effective_config.timeout_seconds,
        "max_tokens": effective_config.max_tokens,
        "candidate_path": candidate_path,
        "vacancy_path": vacancy_path,
        "prompt_source": prompt_source,
        "output_path": output_path or "",
        "log_path": log_path or "",
        "result_schema": public_result_schema.get("$id", _RESULT_SCHEMA_NAME),
        "lint_status": lint_status,
        "llm_call_status": llm_call_status,
    }

    if format == "json":
        output = render_json_output(validated)
    elif format == "md":
        output = render_markdown_report(validated)
    else:
        output = render_text_report(validated)

    if output_path:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            out_path.write_text(output, encoding="utf-8")
        except OSError as e:
            raise ContentMatchError(f"cannot write output: {output_path} — {e}")

    if log_path:
        save_log_zip(
            log_path=log_path,
            meta=meta,
            result_schema=public_result_schema,
            prompt_text=prompt_text,
            candidate_payload=candidate_payload,
            vacancy_text=vacancy_text,
            raw_response=raw_response_text,
            validated_result=validated,
            usage=usage,
        )
        meta_stored = log_path
    else:
        meta_stored = None

    return output, validated, meta


def _build_command_string(
    candidate_path: str,
    vacancy_path: str,
    config_path: str | None,
    policy: MatchPolicy,
    format: str,
    output_path: str | None,
    log_path: str | None,
    timeout_seconds: int | None,
    max_tokens: int | None,
) -> str:
    parts = [
        "hirepaper content match",
        candidate_path,
        vacancy_path,
    ]
    if config_path:
        parts.extend(["--config", config_path])
    if policy.locale != "en":
        parts.extend(["--locale", policy.locale])
    if format != "text":
        parts.extend(["--format", format])
    if policy.strict:
        parts.append("--strict")
    if policy.inference != _MATCH_DEFAULT_INFERENCE:
        parts.extend(["--inference", policy.inference])
    if output_path:
        parts.extend(["--output", output_path])
    if log_path:
        parts.extend(["--log", log_path])
    if timeout_seconds is not None:
        parts.extend(["--timeout-seconds", str(timeout_seconds)])
    if max_tokens is not None:
        parts.extend(["--max-tokens", str(max_tokens)])
    return " ".join(parts)
