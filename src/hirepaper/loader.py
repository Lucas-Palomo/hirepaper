import json
import re
from pathlib import Path

from .models import (
    Achievement, AchievementContext, Award, Candidate, Certification,
    Education, Experience, Language, Link, Personal, Phone, Project,
    SkillCategory, Skills, VolunteerExperience,
)


def _is_whitespace(ch: str) -> bool:
    return ch in ' \t\n\r'


def _strip_jsonc(text: str) -> str:
    out: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    escape = False

    while i < n:
        ch = text[i]

        if in_string:
            if escape:
                escape = False
                out.append(ch)
                i += 1
                continue
            if ch == '\\':
                escape = True
                out.append(ch)
                i += 1
                continue
            if ch == '"':
                in_string = False
                out.append(ch)
                i += 1
                continue
            out.append(ch)
            i += 1
            continue

        # Not in string
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue

        # Line comment
        if ch == '/' and i + 1 < n and text[i + 1] == '/':
            i += 2
            while i < n and text[i] != '\n':
                i += 1
            continue

        # Block comment
        if ch == '/' and i + 1 < n and text[i + 1] == '*':
            i += 2
            while i < n:
                if text[i] == '*' and i + 1 < n and text[i + 1] == '/':
                    i += 2
                    break
                i += 1
            continue

        out.append(ch)
        i += 1

    return ''.join(out)


def load_json(path: str | Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    clean = _strip_jsonc(text)
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON (after stripping JSONC comments): {e}")


def load_candidate(path: str | Path) -> Candidate:
    raw = load_json(path)
    _validate(raw)
    return _parse(raw)


def _validate(raw: dict) -> None:
    if "personal" not in raw:
        raise ValueError("Missing required field: 'personal'")
    personal = raw["personal"]
    for key in ("name", "email", "phone", "location"):
        if key not in personal:
            raise ValueError(f"Missing required field: 'personal.{key}'")


def _parse_achievements(raw_list: list[dict]) -> list[Achievement]:
    result: list[Achievement] = []
    for a in raw_list:
        ctx_raw = a.get("context")
        filtered = {k: v for k, v in a.items() if k != "context"}
        ach = Achievement(**filtered)
        if ctx_raw and isinstance(ctx_raw, dict):
            ach.context = AchievementContext(
                action=ctx_raw.get("action"),
                result=ctx_raw.get("result"),
                metrics=ctx_raw.get("metrics"),
            )
        elif ach.action or ach.result or ach.metrics:
            ach.context = AchievementContext(
                action=ach.action,
                result=ach.result,
                metrics=ach.metrics,
            )
        result.append(ach)
    return result


def _parse_phone(raw: object) -> Phone:
    if isinstance(raw, str):
        return Phone(value=raw, hyperlink=f"tel:{raw.replace(' ', '')}")
    if isinstance(raw, dict):
        if "value" not in raw or "hyperlink" not in raw:
            raise ValueError("Missing required field in 'personal.phone': 'value' and 'hyperlink' are required")
        return Phone(value=raw["value"], hyperlink=raw["hyperlink"])
    raise ValueError("'personal.phone' must be a string or an object with 'value' and 'hyperlink'")


def _parse(raw: dict) -> Candidate:
    personal = Personal(
        name=raw["personal"]["name"],
        email=raw["personal"]["email"],
        phone=_parse_phone(raw["personal"]["phone"]),
        location=raw["personal"]["location"],
        headline=raw["personal"].get("headline"),
        links=[Link(**lnk) for lnk in raw["personal"].get("links", [])],
        extra_links=[Link(**lnk) for lnk in raw["personal"].get("extra_links", [])],
    )

    experience = [
        Experience(
            company=e["company"],
            position=e["position"],
            location=e.get("location", ""),
            start_date=e["start_date"],
            end_date=e.get("end_date"),
            current=e.get("current", False),
            technologies=e.get("technologies", []),
            role_summary=e.get("role_summary"),
            scope=e.get("scope"),
            employment_type=e.get("employment_type"),
            achievements=_parse_achievements(e.get("achievements", [])),
            highlights=e.get("highlights", []),
        )
        for e in raw.get("experience", [])
    ]

    education = [
        Education(
            institution=e["institution"],
            degree=e["degree"],
            location=e.get("location", ""),
            start_date=e["start_date"],
            end_date=e["end_date"],
            gpa=e.get("gpa"),
            honors=e.get("honors"),
        )
        for e in raw.get("education", [])
    ]

    skills_raw = raw.get("skills")
    skills: Skills | None = None
    if skills_raw:
        skills = Skills(
            categories=[
                SkillCategory(name=cat["name"], items=cat.get("items", []))
                for cat in skills_raw.get("categories", [])
            ]
        )

    projects = [
        Project(
            name=p["name"],
            description=p.get("description", ""),
            role=p.get("role"),
            start_date=p.get("start_date"),
            end_date=p.get("end_date"),
            technologies=p.get("technologies", []),
            url=p.get("url"),
            highlights=p.get("highlights", []),
        )
        for p in raw.get("projects", [])
    ]

    certifications = [
        Certification(
            name=c["name"],
            issuer=c["issuer"],
            date=c["date"],
        )
        for c in raw.get("certifications", [])
    ]

    languages = [
        Language(language=lang["language"], proficiency=lang["proficiency"])
        for lang in raw.get("languages", [])
    ]

    awards = [
        Award(
            name=a["name"],
            issuer=a["issuer"],
            date=a["date"],
            description=a.get("description"),
        )
        for a in raw.get("awards", [])
    ]

    volunteer = [
        VolunteerExperience(
            organization=v["organization"],
            position=v["position"],
            location=v.get("location", ""),
            start_date=v["start_date"],
            end_date=v.get("end_date"),
            current=v.get("current", False),
            highlights=v.get("highlights", []),
        )
        for v in raw.get("volunteer", [])
    ]

    return Candidate(
        personal=personal,
        summary=raw.get("summary", ""),
        target_role=raw.get("target_role"),
        experience=experience,
        education=education,
        skills=skills,
        projects=projects,
        certifications=certifications,
        languages=languages,
        awards=awards,
        volunteer=volunteer,
    )
