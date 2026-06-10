"""
Public library API for hirepaper workflows.

Provides stable, importable entry points for PDF generation, content analysis,
and LinkedIn reporting without depending on the Typer CLI layer.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._resources import config_template_path, example_candidate_path, icons_dir, templates_dir
from .content_lint import lint_candidate as _lint_candidate
from .density import DENSITY_MAP
from .generator import generate_latex as _generate_latex
from .loader import load_candidate as _load_candidate
from .locale import Locale
from .log_archive import LogArchiveError, StagedLogArchive
from .models import Candidate

# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class PDFGenerateError(Exception):
    pass


# ---------------------------------------------------------------------------
# Request / Response types
# ---------------------------------------------------------------------------


@dataclass
class PDFGenerateResult:
    output_path: Path
    build_status: str
    artifact_validation_status: str
    validation_message: str = ""
    log_archive_members: list[str] = field(default_factory=list)


@dataclass
class LintResult:
    ok: int
    warn: int
    fail: int
    messages: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers (moved from cli.py)
# ---------------------------------------------------------------------------

_LAYOUT_MAP: dict[str, dict[str, str]] = {
    "standard": {"tex": "standard.tex", "cls": "standard.cls"},
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _latex_env(build_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    xdg_cache_home = build_dir / "xdg-cache"
    texmf_var = build_dir / "texmf-var"
    xdg_cache_home.mkdir(parents=True, exist_ok=True)
    texmf_var.mkdir(parents=True, exist_ok=True)
    env["XDG_CACHE_HOME"] = str(xdg_cache_home)
    env["TEXMFVAR"] = str(texmf_var)
    env["TEXMFCACHE"] = str(texmf_var)
    return env


def _convert_icons(build_dir: Path) -> None:
    for svg_path in sorted(icons_dir().glob("*.svg")):
        pdf_path = build_dir / f"{svg_path.stem}.pdf"
        subprocess.run(
            ["rsvg-convert", "-f", "pdf", "-o", str(pdf_path), str(svg_path)],
            capture_output=True, text=True,
        )


def _stage_pdf_build_logs(
    archive: StagedLogArchive | None,
    build_dir: Path,
    cls_stem: str,
    candidate_path: Path,
    engine_stdout: str,
    engine_stderr: str,
) -> list[str]:
    if archive is None:
        return []

    archive.copy_file(candidate_path, "candidate.json")
    archive.copy_file(build_dir / "resume.tex", "resume.tex")
    archive.copy_file(build_dir / f"{cls_stem}.cls", f"{cls_stem}.cls")

    for icon_pdf in sorted(build_dir.glob("*.pdf")):
        if icon_pdf.name == "resume.pdf":
            continue
        archive.copy_file(icon_pdf, Path("icons") / icon_pdf.name)

    for artifact in sorted(build_dir.glob("resume.*")):
        archive.copy_file(artifact, artifact.name)

    archive.write_text("engine-stdout.log", engine_stdout or "")
    archive.write_text("engine-stderr.log", engine_stderr or "")
    return archive.list_members()


def _validate_pdf_artifact(pdf_path: Path) -> tuple[bool, str]:
    r = subprocess.run(["pdftotext", str(pdf_path), "-"], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return False, "PDF has no extractable text (build may have failed; check luaotfload/fontspec)"
    r = subprocess.run(["pdffonts", str(pdf_path)], capture_output=True, text=True)
    if r.returncode != 0:
        return False, "Font inspection failed (pdffonts error)"
    lines = r.stdout.splitlines()
    if len(lines) < 3:
        return False, "No fonts listed in PDF (font loading may have failed)"
    has_type3 = False
    has_font = False
    for line in lines[2:]:
        if not line.strip():
            continue
        has_font = True
        if "Type 3" in line:
            has_type3 = True
    if not has_font:
        return False, "No embedded fonts found in PDF"
    if has_type3:
        return False, "PDF contains Type 3 fonts (ATS-unsafe)"
    return True, ""


def _build_pdf(
    tex_content: str,
    cls_content: str,
    cls_stem: str,
    candidate_path: Path,
    pdf_dst: Path,
    log_archive: StagedLogArchive | None = None,
    engine: str = "lualatex",
) -> tuple[int, str, str, str]:
    with tempfile.TemporaryDirectory(prefix="hirepaper-") as tmp:
        build = Path(tmp)
        tex_path = build / "resume.tex"
        cls_path = build / f"{cls_stem}.cls"
        latex_env = _latex_env(build)
        tex_path.write_text(tex_content, encoding="utf-8")
        cls_path.write_text(cls_content, encoding="utf-8")
        _convert_icons(build)

        result = subprocess.run(
            [engine, "-interaction=nonstopmode", tex_path.name],
            cwd=build,
            capture_output=True,
            text=True,
            errors="replace",
            env=latex_env,
        )

        _stage_pdf_build_logs(
            log_archive,
            build,
            cls_stem,
            candidate_path,
            result.stdout or "",
            result.stderr or "",
        )

        pdf_path = build / "resume.pdf"
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            pdf_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf_path, pdf_dst)

            valid, msg = _validate_pdf_artifact(pdf_dst)
            if not valid:
                return 2, "success", "failed", msg

            return 0, "success", "passed", ""

    return 1, "failed", "not_run", ""


# ---------------------------------------------------------------------------
# PDF Generation
# ---------------------------------------------------------------------------


def generate_pdf(
    candidate: Candidate,
    output_path: Path | str,
    locale: str = "en",
    density: str = "compact",
    layout: str = "standard",
    log: Path | str | None = None,
) -> PDFGenerateResult:
    if density not in DENSITY_MAP:
        raise PDFGenerateError(f"unknown density '{density}' (choose from: {', '.join(DENSITY_MAP)})")

    if layout not in _LAYOUT_MAP:
        raise PDFGenerateError(
            f"unknown layout '{layout}' "
            "(current supported value: standard)"
        )

    try:
        locale_obj = Locale(locale)
    except FileNotFoundError:
        raise PDFGenerateError(f"locale '{locale}' not found")

    layout_files = _LAYOUT_MAP[layout]
    cls_path = templates_dir() / layout_files["cls"]
    tex_path = templates_dir() / layout_files["tex"]
    if not cls_path.exists() or not tex_path.exists():
        raise PDFGenerateError(f"layout files not found for '{layout}'")

    latex = _generate_latex(candidate, locale=locale_obj, density=density, template_path=tex_path)
    cls_content = cls_path.read_text(encoding="utf-8")
    cls_stem = Path(layout_files["cls"]).stem

    pdf_dst = Path(output_path)

    if log:
        log_path = Path(log)
        try:
            with StagedLogArchive(log_path, prefix="hirepaper-pdf-log-") as archive:
                exit_code, build_status, validation_status, validation_msg = _build_pdf(
                    latex,
                    cls_content,
                    cls_stem,
                    Path("candidate.json"),
                    pdf_dst,
                    log_archive=archive,
                )
                meta = {
                    "command": (
                        f"generate_pdf(locale={locale}, density={density}, layout={layout})"
                    ),
                    "timestamp_utc": _utcnow_iso(),
                    "output_path": str(pdf_dst),
                    "log_path": str(log_path),
                    "candidate_name": candidate.personal.name,
                    "locale": locale,
                    "density": density,
                    "layout": layout,
                    "engine": "lualatex",
                    "build_status": build_status,
                    "artifact_validation_status": validation_status,
                    "validation_message": validation_msg,
                }
                archive.write_json("meta.json", meta)
                archive_members = archive.list_members()
                archive.write_json("meta.json", {**meta, "artifacts_included": archive_members})
                archive.finalize()
        except LogArchiveError as e:
            raise PDFGenerateError(str(e))
    else:
        exit_code, build_status, validation_status, validation_msg = _build_pdf(
            latex,
            cls_content,
            cls_stem,
            Path("candidate.json"),
            pdf_dst,
        )
        archive_members = []

    return PDFGenerateResult(
        output_path=pdf_dst,
        build_status=build_status,
        artifact_validation_status=validation_status,
        validation_message=validation_msg,
        log_archive_members=archive_members,
    )


def generate_pdf_file(
    candidate_path: Path | str,
    output_path: Path | str,
    locale: str = "en",
    density: str = "compact",
    layout: str = "standard",
    log: Path | str | None = None,
) -> PDFGenerateResult:
    path = Path(candidate_path)
    if not path.exists():
        raise PDFGenerateError(f"input file not found: {path}")
    try:
        candidate = _load_candidate(path)
    except (ValueError, KeyError) as e:
        raise PDFGenerateError(f"invalid input data — {e}")
    return generate_pdf(candidate, output_path, locale, density, layout, log)


def check_pdf_file(pdf_path: Path | str) -> int:
    path = Path(pdf_path)
    if not path.exists():
        raise PDFGenerateError(f"file not found: {pdf_path}")
    from .ats_check import check_pdf as _check_pdf
    return _check_pdf(path)


# ---------------------------------------------------------------------------
# Content Lint
# ---------------------------------------------------------------------------


def _build_lint_result(candidate: Candidate) -> LintResult:
    from .content_lint import LintResult as _LintResultInternal
    internal = _LintResultInternal()
    from .content_lint import (
        _check_structural,
        _check_summary,
        _check_experience,
        _check_skills,
        _check_projects,
        _check_education,
        _check_balance,
        _check_placeholders,
    )
    _check_structural(candidate, internal)
    _check_summary(candidate, internal)
    _check_experience(candidate, internal)
    _check_skills(candidate, internal)
    _check_projects(candidate, internal)
    _check_education(candidate, internal)
    _check_balance(candidate, internal)
    _check_placeholders(candidate, internal)
    return internal


def lint_candidate_data(candidate: Candidate) -> LintResult:
    result = _build_lint_result(candidate)
    messages: list[str] = []
    io = __import__("io")
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        _lint_candidate(candidate)
    messages = [line for line in buf.getvalue().splitlines() if line.strip()]
    return LintResult(ok=result.ok, warn=result.warn, fail=result.fail, messages=messages)


def lint_candidate_file(candidate_path: Path | str) -> LintResult:
    path = Path(candidate_path)
    if not path.exists():
        raise FileNotFoundError(f"candidate file not found: {path}")
    candidate = _load_candidate(path)
    return lint_candidate_data(candidate)


# ---------------------------------------------------------------------------
# Content Match
# ---------------------------------------------------------------------------


def match_candidate(
    candidate: Candidate,
    vacancy_text: str,
    config: Any,
    policy: Any | None = None,
    prompt_text: str | None = None,
    locale: str = "en",
    strict: bool = False,
    inference: str = "medium",
    timeout_seconds: int | None = None,
    max_tokens: int | None = None,
    verbose: int = 0,
) -> dict:
    from .content_match import (
        ContentMatchError,
        MatchPolicy,
        _build_candidate_payload,
        build_messages,
        load_default_prompt,
        load_result_schema,
        build_llm_result_schema,
        _build_effective_config,
        parse_and_validate_response,
        _build_public_result,
    )
    from .llm.client import _complete, _extract_text, _extract_usage

    match_policy = policy or MatchPolicy(strict=strict, inference=inference, locale=locale)
    match_policy.validate()

    prompt = prompt_text or load_default_prompt()
    candidate_payload = _build_candidate_payload(candidate)
    public_schema = load_result_schema()
    llm_schema = build_llm_result_schema(public_schema)
    effective_config = _build_effective_config(config, timeout_seconds, max_tokens)

    messages = build_messages(candidate_payload, vacancy_text, prompt, match_policy, llm_schema)
    response = _complete(effective_config, messages)
    raw_text = _extract_text(response)
    usage = _extract_usage(response)

    finish_reason = None
    try:
        finish_reason = response.choices[0].finish_reason
    except (AttributeError, IndexError, TypeError):
        pass

    if finish_reason == "length":
        snippet = raw_text[-200:] if len(raw_text) > 200 else raw_text
        raise ContentMatchError(
            f"LLM response was truncated (finish_reason=length). "
            f"Raw response tail: ...{repr(snippet)}"
        )

    llm_validated = parse_and_validate_response(raw_text, llm_schema)
    validated = _build_public_result(llm_validated, locale)
    return validated


def match_candidate_file(
    candidate_path: Path | str,
    vacancy_path: Path | str,
    config_path: str | None = None,
    locale: str = "en",
    format: str = "text",
    output: str | None = None,
    log: str | None = None,
    prompt: str | None = None,
    strict: bool = False,
    inference: str = "medium",
    timeout_seconds: int | None = None,
    max_tokens: int | None = None,
    verbose: int = 0,
) -> tuple[str, dict | None, dict | None]:
    from .content_match import run_match
    from .llm.config import load_config

    cfg = load_config(config_path, profile="content_match")
    from .content_match import MatchPolicy, load_prompt as _load_match_prompt

    policy = MatchPolicy(strict=strict, inference=inference, locale=locale)
    prompt_source = "custom" if prompt else "default"
    prompt_text = _load_match_prompt(prompt)

    return run_match(
        candidate_path=str(candidate_path),
        vacancy_path=str(vacancy_path),
        config=cfg,
        policy=policy,
        prompt_source=prompt_source,
        prompt_text=prompt_text,
        format=format,
        output_path=output,
        log_path=log,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
        verbose=verbose,
    )


# ---------------------------------------------------------------------------
# Content Tailor
# ---------------------------------------------------------------------------


def tailor_candidate(
    candidate: Candidate,
    vacancy_text: str,
    config: Any,
    mode: str = "conservative",
    inference: str = "medium",
    locale: str = "en",
    prompt_text: str | None = None,
    extra_contexts: list[str] | None = None,
    timeout_seconds: int | None = None,
    max_tokens: int | None = None,
    verbose: int = 0,
) -> dict:
    from .content_tailor import (
        ContentTailorError,
        _build_candidate_payload_with_ids,
        build_plan_messages,
        load_candidate_schema,
        load_tailor_plan_schema,
        load_tailor_report_schema,
        load_rewrite_response_schema,
        load_default_tailor_prompt,
        _build_llm_output_schema,
        _build_effective_config,
        parse_and_validate_response,
        _validate_candidate_json,
        _apply_structural_actions,
        _convert_payload_to_candidate_json,
        _build_report_data,
        _validate_report,
        _build_rewrite_messages,
        _apply_rewrite_to_payload,
        parse_and_validate_rewrite_response,
        _parse_lint_output,
    )
    from .llm.client import _complete, _extract_text, _extract_usage
    from .llm.config import LLMConfig

    if mode not in ("conservative", "rewrite"):
        raise ContentTailorError(f"unsupported mode '{mode}'")
    if inference not in ("low", "medium", "high"):
        raise ContentTailorError(f"unsupported inference '{inference}'")

    prompt = prompt_text or load_default_tailor_prompt()
    candidate_payload = _build_candidate_payload_with_ids(candidate)
    candidate_schema = load_candidate_schema()
    plan_schema = load_tailor_plan_schema()
    report_schema = load_tailor_report_schema()
    rewrite_response_schema = load_rewrite_response_schema()
    llm_plan_schema = _build_llm_output_schema(plan_schema)
    llm_rewrite_schema = _build_llm_output_schema(rewrite_response_schema)

    effective_config = _build_effective_config(config, timeout_seconds, max_tokens)
    plan_effective_config = _build_effective_config(
        config,
        timeout_seconds=max(effective_config.timeout_seconds, 120),
        max_tokens=max(effective_config.max_tokens, 32768),
    )

    plan_messages = build_plan_messages(
        candidate_payload=candidate_payload,
        vacancy_text=vacancy_text,
        prompt=prompt,
        mode=mode,
        inference=inference,
        locale=locale,
        candidate_schema=candidate_schema,
        plan_schema=llm_plan_schema,
        extra_contexts=extra_contexts,
    )

    response = _complete(plan_effective_config, plan_messages)
    plan_raw = _extract_text(response)

    finish_reason = None
    try:
        finish_reason = response.choices[0].finish_reason
    except (AttributeError, IndexError, TypeError):
        pass

    if finish_reason == "length":
        snippet = plan_raw[-200:] if len(plan_raw) > 200 else plan_raw
        raise ContentTailorError(
            f"LLM plan response was truncated (finish_reason=length). "
            f"Raw response tail: ...{repr(snippet)}"
        )

    validated_plan = parse_and_validate_response(plan_raw, plan_schema)

    candidate_raw = __import__("copy").deepcopy(candidate_payload)
    candidate_raw, structural_changes = _apply_structural_actions(validated_plan, candidate_raw)

    rewrite_results: list[dict] = []
    all_rewrite_requests = validated_plan.get("rewrite_requests", [])
    always_rewrite_kinds = frozenset({"headline", "summary", "target_role"})
    always_rewrites = [rw for rw in all_rewrite_requests if rw.get("target_kind") in always_rewrite_kinds]
    mode_rewrites = [rw for rw in all_rewrite_requests if rw.get("target_kind") not in always_rewrite_kinds]

    process_rewrites = list(always_rewrites)
    if mode == "rewrite":
        process_rewrites.extend(mode_rewrites)

    for rw_request in process_rewrites:
        rw_messages = _build_rewrite_messages(
            rewrite_request=rw_request,
            candidate_payload=candidate_raw,
            locale=locale,
            mode=mode,
            inference=inference,
            rewrite_response_schema=llm_rewrite_schema,
        )
        rw_response = _complete(effective_config, rw_messages)
        rw_text = _extract_text(rw_response)

        rw_finish = None
        try:
            rw_finish = rw_response.choices[0].finish_reason
        except (AttributeError, IndexError, TypeError):
            pass

        if rw_finish == "length":
            raise ContentTailorError("LLM rewrite response was truncated (finish_reason=length).")

        validated_rw = parse_and_validate_rewrite_response(rw_text, rewrite_response_schema, rw_request)
        rewrites_dict = validated_rw.get("rewrites", {})
        _apply_rewrite_to_payload(rw_request.get("target_kind", ""), rewrites_dict, candidate_raw)

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

    _validate_candidate_json(final_candidate_json, candidate_schema)

    lint_before_info = {"status": "not_run", "ok": 0, "warn": 0, "fail": 0}
    lint_after_info = {"status": "not_run", "ok": 0, "warn": 0, "fail": 0}

    from .content_lint import lint_candidate as _lint
    import io as _io
    from contextlib import redirect_stdout

    buf = _io.StringIO()
    with redirect_stdout(buf):
        lint_code_before = _lint(candidate)
    lint_before_info = _parse_lint_output(buf.getvalue())

    if lint_code_before != 0:
        raise ContentTailorError(
            "Content lint FAILED — tailoring aborted. "
            "Fix candidate data quality issues before tailoring."
        )

    temp_json = json.dumps(final_candidate_json)
    import tempfile as _tf
    with _tf.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(temp_json)
        tmp_path = f.name
    try:
        temp_candidate = _load_candidate(tmp_path)
        buf2 = _io.StringIO()
        with redirect_stdout(buf2):
            lint_code_after = _lint(temp_candidate)
        lint_after_info = _parse_lint_output(buf2.getvalue())
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if lint_code_after != 0:
        raise ContentTailorError(
            "Final tailored candidate FAILED content lint. "
            "Review the tailored JSON and ensure it is complete and valid."
        )

    report_data = _build_report_data(
        plan=validated_plan,
        changes=structural_changes,
        rewrites=rewrite_results,
        lint_before=lint_before_info,
        lint_after=lint_after_info,
        locale=locale,
        final_target_role=final_target_role,
    )
    _validate_report(report_data, report_schema)

    return report_data | {"tailored_candidate": final_candidate_json, "report_data": report_data}


def tailor_candidate_file(
    candidate_path: Path | str,
    vacancy_path: Path | str,
    output: str,
    config_path: str | None = None,
    locale: str = "en",
    mode: str = "conservative",
    inference: str = "medium",
    extra_context: list[str] | None = None,
    report_output: str | None = None,
    report_format: str = "text",
    log: str | None = None,
    prompt: str | None = None,
    timeout_seconds: int | None = None,
    max_tokens: int | None = None,
    verbose: int = 0,
) -> tuple[str, dict | None, dict | None]:
    from .content_tailor import run_tailor
    from .llm.config import load_config

    cfg = load_config(config_path, profile="content_tailor")
    from .content_tailor import load_prompt as _load_tailor_prompt

    prompt_text = _load_tailor_prompt(prompt)

    return run_tailor(
        candidate_path=str(candidate_path),
        vacancy_path=str(vacancy_path),
        config=cfg,
        mode=mode,
        inference=inference,
        locale=locale,
        report_format=report_format,
        output_path=output,
        report_output_path=report_output,
        log_path=log,
        prompt_text=prompt_text,
        extra_context_paths=extra_context,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
        verbose=verbose,
    )


# ---------------------------------------------------------------------------
# LinkedIn Generate
# ---------------------------------------------------------------------------


def generate_linkedin_report(
    candidate: Candidate,
    config: Any,
    locale: str = "en",
    prompt_text: str | None = None,
    extra_contexts: list[str] | None = None,
    timeout_seconds: int | None = None,
    max_tokens: int | None = None,
    verbose: int = 0,
) -> dict:
    from .linkedin_generate import (
        LinkedInGenerateError,
        _build_candidate_payload,
        load_linkedin_schema,
        load_default_linkedin_prompt,
        _build_llm_output_schema,
        _build_effective_config,
        _build_linkedin_messages,
        parse_and_validate_response,
    )
    from .llm.client import _complete, _extract_text, _extract_usage

    prompt = prompt_text or load_default_linkedin_prompt()
    candidate_payload = _build_candidate_payload(candidate)
    linkedin_schema = load_linkedin_schema()
    llm_schema = _build_llm_output_schema(linkedin_schema)
    effective_config = _build_effective_config(config, timeout_seconds, max_tokens)

    messages = _build_linkedin_messages(
        candidate_payload=candidate_payload,
        prompt=prompt,
        locale=locale,
        llm_schema=llm_schema,
        extra_contexts=extra_contexts,
    )

    response = _complete(effective_config, messages)
    raw_text = _extract_text(response)

    finish_reason = None
    try:
        finish_reason = response.choices[0].finish_reason
    except (AttributeError, IndexError, TypeError):
        pass

    if finish_reason == "length":
        snippet = raw_text[-200:] if len(raw_text) > 200 else raw_text
        raise LinkedInGenerateError(
            f"LLM response was truncated (finish_reason=length). "
            f"Raw response tail: ...{repr(snippet)}"
        )

    validated = parse_and_validate_response(raw_text, linkedin_schema)
    return validated


def generate_linkedin_report_file(
    candidate_path: Path | str,
    output: str,
    config_path: str | None = None,
    locale: str = "en",
    format: str = "txt",
    log: str | None = None,
    prompt: str | None = None,
    extra_context: list[str] | None = None,
    timeout_seconds: int | None = None,
    max_tokens: int | None = None,
    verbose: int = 0,
) -> tuple[str, dict, dict]:
    from .linkedin_generate import run_generate
    from .llm.config import load_config

    cfg = load_config(config_path, profile="linkedin_generate")
    from .linkedin_generate import load_prompt as _load_linkedin_prompt

    prompt_text = _load_linkedin_prompt(prompt)

    return run_generate(
        candidate_path=str(candidate_path),
        config=cfg,
        locale=locale,
        format=format,
        output_path=output,
        log_path=log,
        prompt_text=prompt_text,
        extra_context_paths=extra_context,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
        verbose=verbose,
    )


# ---------------------------------------------------------------------------
# Bootstrap helpers
# ---------------------------------------------------------------------------


def bootstrap_candidate_file(output_path: Path | str, force: bool = False) -> Path:
    src = example_candidate_path()
    if not src.exists():
        raise FileNotFoundError(f"example candidate template not found at {src}")
    dst = Path(output_path)
    if dst.exists() and not force:
        raise FileExistsError(
            f"candidate file already exists: {dst}\n"
            f"Use force=True to overwrite it or choose another path."
        )
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    except OSError as e:
        raise OSError(f"cannot write candidate file: {dst} — {e}")
    return dst


def bootstrap_config_file(output_path: Path | str, force: bool = False) -> Path:
    src = config_template_path()
    if not src.exists():
        raise FileNotFoundError(f"config template not found at {src}")
    dst = Path(output_path)
    if dst.exists() and not force:
        raise FileExistsError(
            f"config file already exists: {dst}\n"
            f"Use force=True to overwrite it or choose another path."
        )
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    except OSError as e:
        raise OSError(f"cannot write config file: {dst} — {e}")
    return dst
