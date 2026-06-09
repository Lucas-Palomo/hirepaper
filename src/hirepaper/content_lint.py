import re
from dataclasses import dataclass, field
from typing import Optional

from .models import Candidate, Experience, Project


_PLACEHOLDER_PATTERNS: list[re.Pattern] = [
    re.compile(r"Your Name"),
    re.compile(r"Company Name"),
    re.compile(r"Target Position Title"),
    re.compile(r"Optional:?"),
    re.compile(r"Previous Company"),
    re.compile(r"Previous Role"),
    re.compile(r"University Name"),
    re.compile(r"Degree Title"),
    re.compile(r"Category Name"),
    re.compile(r"Another Category"),
    re.compile(r"Project Name"),
    re.compile(r"Simpler Project"),
    re.compile(r"Certification Name"),
    re.compile(r"Issuing Organization"),
    re.compile(r"Award Name"),
    re.compile(r"Issuing Entity"),
    re.compile(r"Organization Name"),
    re.compile(r"Your Language"),
    re.compile(r"Another Language"),
    re.compile(r"\bTech1\b"),
    re.compile(r"\bTech2\b"),
    re.compile(r"\bTech3\b"),
    re.compile(r"\bTechA\b"),
    re.compile(r"\bTechB\b"),
    re.compile(r"\bSkill A\b"),
    re.compile(r"\bSkill B\b"),
    re.compile(r"\bSkill C\b"),
    re.compile(r"\bSkill X\b"),
    re.compile(r"\bSkill Y\b"),
    re.compile(r"\bSkill Z\b"),
    re.compile(r"\bStack\b"),
    re.compile(r"you@email\.com"),
    re.compile(r"yourportfolio\.dev"),
    re.compile(r"yourprofile"),
    re.compile(r"github\.com/yourprofile"),
    re.compile(r"linkedin\.com/in/yourprofile"),
    re.compile(r"project\.url"),
    re.compile(r"verify\.issuer"),
    re.compile(r"credential-id"),
    re.compile(r"What you did"),
    re.compile(r"What happened"),
    re.compile(r"Optional measurable"),
    re.compile(r"Or use a single summary"),
    re.compile(r"Falls back to simple"),
    re.compile(r"Another achievement"),
    re.compile(r"Another highlight"),
    re.compile(r"Another contribution"),
    re.compile(r"Specific achievement"),
    re.compile(r"Your contribution"),
    re.compile(r"What you accomplished"),
    re.compile(r"Optional context"),
]


class LintResult:
    def __init__(self) -> None:
        self.ok: int = 0
        self.warn: int = 0
        self.fail: int = 0

    def ok_(self, msg: str) -> None:
        self.ok += 1
        print(f"[OK] {msg}")

    def warn_(self, msg: str) -> None:
        self.warn += 1
        print(f"[WARN] {msg}")

    def fail_(self, msg: str) -> None:
        self.fail += 1
        print(f"[FAIL] {msg}")


def _word_count(text: str) -> int:
    return len(text.split())


def _experience_bullets(exp: Experience) -> list[str]:
    if exp.achievements:
        bullets: list[str] = []
        for a in exp.achievements:
            if a.summary:
                bullets.append(a.summary)
            else:
                parts = [p for p in (a.action, a.result) if p]
                if parts:
                    bullet = " — ".join(parts)
                    if a.metrics:
                        bullet += f" ({a.metrics})"
                    bullets.append(bullet)
        return bullets
    return list(exp.highlights)


def _all_experience_bullets(exps: list[Experience]) -> list[tuple[Experience, list[str]]]:
    return [(exp, _experience_bullets(exp)) for exp in exps]


def _all_project_bullets(projects: list[Project]) -> list[tuple[Project, list[str]]]:
    return [(proj, list(proj.highlights)) for proj in projects]


def _check_structural(candidate: Candidate, result: LintResult) -> None:
    if candidate.summary.strip():
        result.ok_("Summary is present")
    else:
        result.fail_("Summary is missing or empty")

    has_exp = bool(candidate.experience)
    has_proj = bool(candidate.projects)
    if has_exp or has_proj:
        if has_exp:
            result.ok_(f"Experience section has {len(candidate.experience)} entry(ies)")
        if has_proj:
            result.ok_(f"Projects section has {len(candidate.projects)} entry(ies)")
    else:
        result.fail_("No experience or project entries found")

    if candidate.skills and any(cat.items for cat in candidate.skills.categories):
        result.ok_("Skills section is present and non-empty")
    else:
        result.fail_("Skills section is missing or all categories are empty")

    if candidate.education:
        result.ok_(f"Education section has {len(candidate.education)} entry(ies)")
    else:
        result.warn_("Education section is missing")


def _check_summary(candidate: Candidate, result: LintResult) -> None:
    if not candidate.summary.strip():
        result.fail_("Summary is empty")
        return
    wc = _word_count(candidate.summary)
    if wc < 25:
        result.warn_(f"Summary is short ({wc} words)")
    elif wc <= 80:
        result.ok_(f"Summary length is reasonable ({wc} words)")
    else:
        result.warn_(f"Summary is dense for fast scanning ({wc} words)")


def _check_experience(candidate: Candidate, result: LintResult) -> None:
    if not candidate.experience:
        return
    bullet_data = _all_experience_bullets(candidate.experience)
    total_bullets = 0
    for exp, bullets in bullet_data:
        total_bullets += len(bullets)
        if len(bullets) > 5:
            result.warn_(
                f"Role '{exp.position}' at '{exp.company}' has {len(bullets)} bullet(s); "
                f"consider prioritizing the strongest 4-5"
            )
        for b in bullets:
            wc = _word_count(b)
            if wc > 32:
                result.warn_(f"Bullet in '{exp.position}' is {wc} words (max recommended: 32)")

    if total_bullets > 20:
        result.warn_(f"Total experience bullets ({total_bullets}) exceed recommended maximum (20)")
    elif total_bullets > 18:
        result.warn_(
            f"Total experience bullets ({total_bullets}) are near the recommended maximum; "
            f"consider trimming less impactful entries"
        )
    else:
        result.ok_(f"Experience density is reasonable ({total_bullets} total bullet(s))")


def _check_skills(candidate: Candidate, result: LintResult) -> None:
    if not candidate.skills or not candidate.skills.categories:
        result.fail_("Skills section is missing or has no categories")
        return
    cats = candidate.skills.categories
    total_items = 0
    for cat in cats:
        n = len(cat.items)
        total_items += n
        if n > 10:
            result.warn_(f"Skills category '{cat.name}' has {n} items (max recommended: 8-10)")
        elif n > 8:
            result.warn_(f"Skills category '{cat.name}' has {n} items (max recommended: 8-10)")

    if total_items > 35:
        result.warn_(f"Skills section is overpacked ({total_items} items across {len(cats)} categories)")
    elif total_items > 30:
        result.warn_(f"Skills section has {total_items} items (max recommended: 30-35)")
    else:
        result.ok_(f"Skills section has {total_items} items across {len(cats)} categories")


def _check_projects(candidate: Candidate, result: LintResult) -> None:
    projects = candidate.projects
    if not projects:
        return
    if len(projects) > 3:
        result.warn_(f"Projects section has {len(projects)} entries; consider limiting to the strongest 3")

    bullet_data = _all_project_bullets(projects)
    for proj, bullets in bullet_data:
        if proj.description:
            wc = _word_count(proj.description)
            if wc > 80:
                result.warn_(f"Project '{proj.name}' description is {wc} words (max recommended: 60-80)")
            elif wc > 60:
                result.warn_(f"Project '{proj.name}' description is {wc} words (max recommended: 60-80)")
        if len(bullets) > 3:
            result.warn_(f"Project '{proj.name}' has {len(bullets)} highlight(s); consider limiting to 3")


def _check_education(candidate: Candidate, result: LintResult) -> None:
    if not candidate.education:
        return
    for edu in candidate.education:
        sub_details = []
        if edu.gpa:
            sub_details.append(edu.gpa)
        if edu.honors:
            sub_details.append(edu.honors)
        total_detail = sum(len(d) for d in sub_details)
        if total_detail > 80:
            result.warn_(f"Education entry '{edu.degree}' at '{edu.institution}' has verbose details ({total_detail} chars)")


def _check_balance(candidate: Candidate, result: LintResult) -> None:
    exp_bullet_data = _all_experience_bullets(candidate.experience)
    proj_bullet_data = _all_project_bullets(candidate.projects)

    total_exp_bullets = sum(len(b) for _, b in exp_bullet_data)
    total_proj_bullets = sum(len(b) for _, b in proj_bullet_data)

    if total_proj_bullets > total_exp_bullets and total_exp_bullets > 0:
        result.warn_("Projects section carries more bullet detail than experience section")

    total_skills = 0
    if candidate.skills:
        total_skills = sum(len(cat.items) for cat in candidate.skills.categories)

    if total_exp_bullets > 0 and total_skills > 2 * total_exp_bullets:
        result.warn_(
            f"Skills count ({total_skills}) is more than 2x experience bullet count ({total_exp_bullets}); "
            f"consider whether the skills section is disproportionately large"
        )

    total_narrative = _word_count(candidate.summary)
    for exp, bullets in exp_bullet_data:
        for b in bullets:
            total_narrative += _word_count(b)
    for proj, bullets in proj_bullet_data:
        if proj.description:
            total_narrative += _word_count(proj.description)
        for b in bullets:
            total_narrative += _word_count(b)

    if total_narrative > 500:
        result.warn_(
            f"Total narrative word count ({total_narrative}) is high for compact one-page scanability; "
            f"consider trimming less essential content"
        )


def _check_placeholders(candidate: Candidate, result: LintResult) -> None:
    text_bodies: list[str] = []

    text_bodies.append(candidate.summary)
    if candidate.personal:
        text_bodies.append(candidate.personal.name)
        text_bodies.append(candidate.personal.headline or "")
        text_bodies.append(candidate.personal.email)
        text_bodies.append(candidate.personal.location)

    for exp in candidate.experience:
        text_bodies.append(exp.company)
        text_bodies.append(exp.position)
        text_bodies.append(exp.role_summary or "")
        for t in exp.technologies:
            text_bodies.append(t)
        if exp.achievements:
            for a in exp.achievements:
                text_bodies.append(a.summary or "")
                text_bodies.append(a.action or "")
                text_bodies.append(a.result or "")
                text_bodies.append(a.metrics or "")
                text_bodies.append(a.situation or "")
        for h in exp.highlights:
            text_bodies.append(h)

    if candidate.skills:
        for cat in candidate.skills.categories:
            text_bodies.append(cat.name)
            for item in cat.items:
                text_bodies.append(item)

    for proj in candidate.projects:
        text_bodies.append(proj.name)
        text_bodies.append(proj.description)
        text_bodies.append(proj.role or "")
        for t in proj.technologies:
            text_bodies.append(t)
        for h in proj.highlights:
            text_bodies.append(h)

    for edu in candidate.education:
        text_bodies.append(edu.institution)
        text_bodies.append(edu.degree)
        text_bodies.append(edu.gpa or "")
        text_bodies.append(edu.honors or "")

    for cert in candidate.certifications:
        text_bodies.append(cert.name)
        text_bodies.append(cert.issuer)

    for award in candidate.awards:
        text_bodies.append(award.name)
        text_bodies.append(award.issuer)
        text_bodies.append(award.description or "")

    for vol in candidate.volunteer:
        text_bodies.append(vol.organization)
        text_bodies.append(vol.position)
        for h in vol.highlights:
            text_bodies.append(h)

    for lang in candidate.languages:
        text_bodies.append(lang.language)

    full_text = "\n".join(text_bodies)

    found: list[str] = []
    for pat in _PLACEHOLDER_PATTERNS:
        m = pat.search(full_text)
        if m:
            found.append(m.group())

    if found:
        unique = sorted(set(found))
        result.fail_(f"Placeholder text detected: {', '.join(unique)}")
    else:
        result.ok_("No placeholder text detected")


def lint_candidate(candidate: Candidate) -> int:
    print(f"Content lint for candidate: {candidate.personal.name}\n")

    result = LintResult()

    _check_structural(candidate, result)
    _check_summary(candidate, result)
    _check_experience(candidate, result)
    _check_skills(candidate, result)
    _check_projects(candidate, result)
    _check_education(candidate, result)
    _check_balance(candidate, result)
    _check_placeholders(candidate, result)

    print()
    if result.fail > 0:
        print(f"Result: FAIL ({result.fail} failure(s), {result.warn} warning(s), {result.ok} ok)")
        return 1
    elif result.warn > 0:
        print(f"Result: PASS with warnings ({result.warn} warning(s), {result.ok} ok)")
        return 0
    else:
        print(f"Result: PASS ({result.ok} checks passed)")
        return 0
