import re
from pathlib import Path

from ._resources import templates_dir
from .density import DENSITY_MAP, DensityPolicy
from .locale import Locale
from .models import Achievement, Award, Candidate, Education, Experience, Link, Phone, Project, Skills, VolunteerExperience


_TEMPLATE_PATH = templates_dir() / "standard.tex"


def _sanitize_for_pdf(text: str) -> str:
    chars = {
        "{": "\\{",
        "}": "\\}",
        "#": "\\#",
        "%": "\\%",
        "&": "\\&",
        "_": "\\_",
        "^": " ",
        "~": " ",
    }
    for old, new in chars.items():
        text = text.replace(old, new)
    return text


def _render_metadata(candidate: Candidate, policy: DensityPolicy | None = None) -> str:
    def _extract_skills() -> list[str]:
        if not candidate.skills:
            return []
        result: list[str] = []
        for cat in candidate.skills.categories:
            items = cat.items
            if policy and policy.max_skills_per_category is not None and len(items) > policy.max_skills_per_category:
                items = items[: policy.max_skills_per_category]
            result.extend(items)
        return result

    skills_kw = _extract_skills()
    exp_limited = candidate.experience
    if policy and policy.max_experience_items is not None:
        exp_limited = exp_limited[: policy.max_experience_items]
    exp_kw: list[str] = []
    for e in exp_limited:
        exp_kw.extend(e.technologies)
    proj_limited = candidate.projects
    if policy and policy.max_projects is not None:
        proj_limited = proj_limited[: policy.max_projects]
    proj_kw: list[str] = []
    for p in proj_limited:
        proj_kw.extend(p.technologies)

    all_kw = list(dict.fromkeys(skills_kw + exp_kw + proj_kw))
    exp_kw_dedup = list(dict.fromkeys(exp_kw))
    proj_kw_dedup = list(dict.fromkeys(proj_kw))

    def fmt(kws: list[str]) -> str:
        return (", ").join(kws)

    kw_skills = fmt(skills_kw)
    kw_exp = fmt(exp_kw)
    kw_proj = fmt(proj_kw)
    kw_all = fmt(all_kw)

    def escape(kw: str) -> str:
        return _sanitize_for_pdf(kw)

    kw_skills_e = escape(kw_skills)
    kw_exp_e = escape(kw_exp)
    kw_proj_e = escape(kw_proj)
    kw_all_e = escape(kw_all)

    combined = kw_all_e

    x_pdfinfo_parts = (
        f"  /X-App (hirepaper)",
        f"  /X-Engine (lualatex)",
        f"  /X-Keywords-Skills ({_sanitize_for_pdf(kw_skills)})",
        f"  /X-Keywords-Experience ({_sanitize_for_pdf(fmt(exp_kw_dedup))})",
        f"  /X-Keywords-Projects ({_sanitize_for_pdf(fmt(proj_kw_dedup))})",
    )

    pdfinfo_block = "\\immediate\\pdfextension info {\n" + "\n".join(x_pdfinfo_parts) + "\n}"

    name_escaped = escape(candidate.personal.name)
    headline_escaped = escape(candidate.personal.headline or "")

    parts = [
        "\\hypersetup{",
        f"  pdfauthor={{{name_escaped}}},",
        f"  pdfsubject={{{headline_escaped}}},",
        f"  pdfkeywords={{{combined}}},",
        "}",
        pdfinfo_block,
    ]
    latex_block = "\n".join(parts)

    return latex_block


def generate_latex(
    candidate: Candidate,
    locale: Locale | None = None,
    template_path: str | Path | None = None,
    density: str = "compact",
) -> str:
    locale = locale or Locale()
    policy = DENSITY_MAP.get(density, DENSITY_MAP["compact"])
    path = Path(template_path) if template_path else _TEMPLATE_PATH
    template_text = path.read_text(encoding="utf-8")

    sections: list[tuple[str, str, str]] = [
        ("PROFILE", _render_summary(candidate), locale.get("section.profile")),
        ("EXPERIENCE", _render_experience(candidate.experience, locale, policy), locale.get("section.experience")),
        ("EDUCATION", _render_education(candidate.education, locale), locale.get("section.education")),
        ("SKILLS", _render_skills(candidate.skills, policy), locale.get("section.skills")),
        ("PROJECTS", _render_projects(candidate.projects, locale, policy), locale.get("section.projects")),
        ("CERTIFICATIONS", _render_certifications(candidate.certifications, locale), locale.get("section.certifications")),
        ("AWARDS", _render_awards(candidate.awards, locale, policy), locale.get("section.awards")),
        ("VOLUNTEER", _render_volunteer(candidate.volunteer, locale, policy), locale.get("section.volunteer")),
        ("LANGUAGES", _render_languages(candidate.languages, policy), locale.get("section.languages")),
        ("EXTRA_LINKS", _render_links_section(candidate, policy), locale.get("section.links")),
    ]

    metadata_block = _render_metadata(candidate, policy)

    email = candidate.personal.email
    phone = candidate.personal.phone
    replacements: dict[str, str] = {
        "METADATA": metadata_block,
        "NAME": _render_name(candidate),
        "HEADLINE": _render_headline(candidate),
        "EMAIL": f"\\href{{mailto:{email}}}{{{_escape_tex(email)}}}",
        "PHONE": f"\\href{{{phone.hyperlink}}}{{{_escape_tex(phone.value)}}}",
        "PHONE_VALUE": _escape_tex(phone.value),
        "PHONE_HYPERLINK": phone.hyperlink,
        "LOCATION": candidate.personal.location,
        "LINKS": _render_links(candidate, policy),
        "CONTACT_TABLE": _render_contact_table(candidate, locale),
        "LABEL_EMAIL": locale.get("label.email"),
        "LABEL_PHONE": locale.get("label.phone"),
        "LABEL_LOCATION": locale.get("label.location"),
    }

    for i, lnk in enumerate(candidate.personal.links):
        display = _clean_url(lnk.url)
        label = _escape_tex(lnk.label)
        replacements[f"LINK{i}"] = f"\\mbox{{\\iconLink\\ {label}: \\href{{{lnk.url}}}{{{display}}}}}"

    for key, content, title in sections:
        if content.strip():
            replacements[key] = content
            replacements[f"SECTION_{key}"] = title
        else:
            replacements[key] = ""
            replacements[f"SECTION_{key}"] = ""

    cert_has = bool(replacements.get("CERTIFICATIONS", "").strip())
    lang_has = bool(replacements.get("LANGUAGES", "").strip())
    links_has = bool(replacements.get("EXTRA_LINKS", "").strip())
    right_has = lang_has or links_has

    if cert_has and right_has:
        right_parts = []
        if lang_has:
            right_parts.append(
                "\\resumeBandSection{" + replacements["SECTION_LANGUAGES"] + "}\n"
                + replacements["LANGUAGES"]
            )
        if links_has:
            right_parts.append(
                "\\resumeBandSection{" + replacements["SECTION_EXTRA_LINKS"] + "}\n"
                + replacements["EXTRA_LINKS"]
            )
        replacements["BAND_LEFT"] = (
            "\\resumeBandSection{" + replacements["SECTION_CERTIFICATIONS"] + "}\n"
            + replacements["CERTIFICATIONS"]
        )
        replacements["BAND_RIGHT"] = "\n\\vspace{6pt}\n".join(right_parts)
        replacements["BAND"] = (
            "\\resumeSectionRule\n"
            "\\noindent\n"
            "\\begin{tabular}{@{}p{0.60\\textwidth}@{\\hspace{0.02\\textwidth}}!{\\color{subdued!40!white}\\vrule}@{\\hspace{0.02\\textwidth}}p{0.30\\textwidth}@{}}\n"
            "\\parbox[t]{\\linewidth}{" + replacements["BAND_LEFT"] + "} &\n"
            "\\parbox[t]{\\linewidth}{" + replacements["BAND_RIGHT"] + "} \\\\\n"
            "\\end{tabular}"
        )
    elif cert_has:
        replacements["BAND"] = (
            "\\resumeSectionRule\n"
            "\\resumeSection{" + replacements["SECTION_CERTIFICATIONS"] + "}\n"
            + replacements["CERTIFICATIONS"]
        )
    elif right_has:
        parts = []
        if lang_has:
            parts.append(
                "\\resumeSection{" + replacements["SECTION_LANGUAGES"] + "}\n"
                + replacements["LANGUAGES"]
            )
        if links_has:
            parts.append(
                "\\resumeSection{" + replacements["SECTION_EXTRA_LINKS"] + "}\n"
                + replacements["EXTRA_LINKS"]
            )
        replacements["BAND"] = "\\resumeSectionRule\n" + "\n".join(parts)
    else:
        replacements["BAND"] = ""
        replacements["BAND_LEFT"] = ""
        replacements["BAND_RIGHT"] = ""

    result = template_text
    for key, value in replacements.items():
        placeholders = [f"{{{key}}}", f"{{{{{key}}}}}"]
        for placeholder in placeholders:
            result = result.replace(placeholder, value)

    result = re.sub(r"\\resumeSection\{\}\s*\n", "", result)

    return result


def _render_name(candidate: Candidate) -> str:
    return candidate.personal.name


def _render_headline(candidate: Candidate) -> str:
    if candidate.personal.headline:
        return f"\\resumeHeadline{{{_escape_tex(candidate.personal.headline)}}}"
    return ""


def _clean_url(url: str) -> str:
    cleaned = url.replace("https://", "").replace("http://", "")
    cleaned = cleaned.rstrip("/")
    cleaned = cleaned.replace("~", "\\textasciitilde{}")
    return cleaned


def _render_links(candidate: Candidate, policy: DensityPolicy) -> str:
    links = candidate.personal.links
    if not links:
        return ""
    link_strs = []
    for lnk in links:
        display = _clean_url(lnk.url)
        label = _escape_tex(lnk.label)
        link_strs.append(
            f"\\mbox{{\\iconLink\\ {label}: \\href{{{lnk.url}}}{{{display}}}}}"
        )
    rendered = " \\quad ".join(link_strs)
    return rendered


def _render_contact_table(candidate: Candidate, locale: Locale) -> str:
    links = candidate.personal.links
    email = _escape_tex(candidate.personal.email)
    phone = candidate.personal.phone
    contact_rows = [
        f"\\iconEmail\\ {locale.get('label.email')}: \\href{{mailto:{candidate.personal.email}}}{{{email}}}",
        f"\\iconPhone\\ {locale.get('label.phone')}: \\href{{{phone.hyperlink}}}{{{_escape_tex(phone.value)}}}",
        f"\\iconPin\\ {locale.get('label.location')}: {_escape_tex(candidate.personal.location)}",
    ]

    def fmt(lnk: Link) -> str:
        display = _clean_url(lnk.url)
        label = _escape_tex(lnk.label)
        return f"\\mbox{{\\iconLink\\ {label}: \\href{{{lnk.url}}}{{{display}}}}}"

    table_rows = []
    for i, contact in enumerate(contact_rows):
        link = fmt(links[i]) if i < len(links) else ""
        sep = "\\\\[3pt]" if i < 2 else "\\\\"
        table_rows.append(f"    {contact} & {link} {sep}")

    for i in range(3, len(links)):
        table_rows.append(f"    & {fmt(links[i])} \\\\")

    if not table_rows:
        return ""

    return (
        "\\noindent\n"
        "\\begin{tabular}{@{}>{\\raggedright\\arraybackslash}p{0.60\\textwidth}@{}>{\\raggedleft\\arraybackslash}p{0.40\\textwidth}@{}}\n"
        + "\n".join(table_rows) + "\n"
        "\\end{tabular}\\par%\n"
    )


def _render_links_section(candidate: Candidate, policy: DensityPolicy) -> str:
    extra_links = candidate.personal.extra_links
    if not extra_links:
        return ""
    if len(extra_links) < policy.min_extra_links_for_section:
        return ""
    parts = []
    for lnk in extra_links:
        display = _clean_url(lnk.url)
        label = _escape_tex(lnk.label)
        parts.append(f"\\resumeEntrySub{{{label}: \\href{{{lnk.url}}}{{{display}}}}}")
    return "\n".join(parts)


def _render_summary(candidate: Candidate) -> str:
    return candidate.summary or ""


def _sanitize_unicode(text: str) -> str:
    chars = {
        "\u2014": "---",
        "\u2013": "--",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "\\textbullet{}",
        "\u2026": "\\dots{}",
        "\u00a0": " ",
    }
    for old, new in chars.items():
        text = text.replace(old, new)
    return text


def _escape_tex(text: str) -> str:
    text = _sanitize_unicode(text)
    chars = {
        "{": "\\{",
        "}": "\\}",
        "\\": "\\textbackslash{}",
        "~": "\\textasciitilde{}",
        "^": "\\textasciicircum{}",
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "_": "\\_",
    }
    for old, new in chars.items():
        text = text.replace(old, new)
    return text


def _format_date(date_str: str | None, locale: Locale) -> str:
    if date_str is None:
        return locale.get("label.present")
    parts = date_str.split("-")
    if len(parts) == 2:
        month = locale.month_abbr(parts[1])
        return f"{month} {parts[0]}"
    return date_str


def _format_tech(technologies: list[str]) -> str:
    if not technologies:
        return ""
    return _escape_tex(", ".join(technologies))


def _bullet_score(text: str) -> int:
    score = 0
    if re.search(r"\d", text):
        score += 3
    if re.search(r"\d+%", text):
        score += 2
    if "—" in text or "\u2014" in text:
        score += 2
    if any(kw in text.lower() for kw in ("led", "built", "designed", "created", "developed", "implemented", "architected")):
        score += 1
    if any(kw in text.lower() for kw in ("million", "thousand", "users", "customers", "revenue", "uptime")):
        score += 1
    return score


def _score_and_sort(items: list[str]) -> list[str]:
    scored = [(item, _bullet_score(item)) for item in items]
    scored.sort(key=lambda x: (-x[1], x[0]))
    return [item for item, _ in scored]


def _render_achievement_bullet(ach: Achievement) -> str:
    if ach.summary:
        return _escape_tex(ach.summary)
    parts = [p for p in (ach.action, ach.result) if p]
    if parts:
        bullet = " — ".join(parts)
        if ach.metrics:
            bullet += f" ({ach.metrics})"
        return _escape_tex(bullet)
    if ach.situation:
        return _escape_tex(ach.situation)
    return ""


def _render_bullets(items: list[str], max_items: int | None = None) -> str:
    if not items:
        return ""
    if max_items is not None and len(items) > max_items:
        items = items[:max_items]
    bullets = "\n".join(f"\\item -- {item}" for item in items)
    return "\\resumeHighlights{\n" + bullets + "\n}"


def _render_experience(experiences: list[Experience], locale: Locale, policy: DensityPolicy) -> str:
    if policy.max_experience_items is not None:
        experiences = experiences[: policy.max_experience_items]

    groups: list[str] = []
    for exp in experiences:
        lines: list[str] = []
        end = locale.get("label.present") if exp.current else _format_date(exp.end_date, locale)
        date_range = f"{_format_date(exp.start_date, locale)} -- {end}"
        lines.append(
            "\\resumeEntry{"
            f"\\mbox{{{_escape_tex(exp.company)}}}"
            "}{"
            f"\\mbox{{{_escape_tex(exp.position)}}}"
            "}{"
            f"{date_range}"
            "}{"
            f"{_escape_tex(exp.location)}"
            "}"
        )

        if policy.show_experience_technologies:
            tech = _format_tech(exp.technologies)
            if tech:
                lines.append(f"\\resumeEntrySub{{{tech}}}")

        if policy.show_role_summary and exp.role_summary:
            lines.append(f"\\resumeEntrySub{{\\textit{{{_escape_tex(exp.role_summary)}}}}}")

        if exp.employment_type:
            lines.append(f"\\resumeEntrySub{{{locale.get('label.employment_type')}: {_escape_tex(exp.employment_type)}}}")

        bullets: list[str] = []
        if exp.achievements:
            bullets = [
                b for a in exp.achievements
                if (b := _render_achievement_bullet(a))
            ]
        elif exp.highlights:
            bullets = [_escape_tex(h) for h in exp.highlights]

        if bullets:
            scored = _score_and_sort(bullets)
            lines.append(_render_bullets(scored, policy.max_experience_bullets))

        groups.append("\n".join(lines))

    return "\n\\resumeEntrySep\n".join(groups)


def _render_education(education: list[Education], locale: Locale) -> str:
    parts = []
    for edu in education:
        date_range = f"{_format_date(edu.start_date, locale)} -- {_format_date(edu.end_date, locale)}"
        parts.append(
            "\\resumeEntry{"
            f"\\mbox{{{_escape_tex(edu.degree)}}}"
            "}{"
            f"\\mbox{{{_escape_tex(edu.institution)}}}"
            "}{"
            f"{date_range}"
            "}{"
            f"{_escape_tex(edu.location)}"
            "}"
        )
        extras_parts = []
        if edu.gpa:
            extras_parts.append(f"{locale.get('label.gpa')}: {edu.gpa}")
        if edu.honors:
            extras_parts.append(_escape_tex(edu.honors))
        if extras_parts:
            extras_line = " \\textbullet{} ".join(extras_parts)
            parts.append(f"\\resumeEntrySub{{{extras_line}}}")
        parts.append("\\vspace{1pt}")
    return "\n".join(parts)


def _render_skills(skills: Skills | None, policy: DensityPolicy) -> str:
    if not skills or not skills.categories:
        return ""
    parts = []
    for cat in skills.categories:
        items = cat.items
        if policy.max_skills_per_category is not None and len(items) > policy.max_skills_per_category:
            items = items[: policy.max_skills_per_category]
        items_str = ", ".join(items)
        parts.append(
            "\\resumeSkillCategory{"
            f"{_escape_tex(cat.name)}"
            "}{"
            f"{_escape_tex(items_str)}"
            "}"
        )
    return "\n".join(parts)


def _render_projects(projects: list[Project], locale: Locale, policy: DensityPolicy) -> str:
    if policy.max_projects is not None:
        projects = projects[: policy.max_projects]

    parts = []
    for proj in projects:
        tech = _format_tech(proj.technologies) if proj.technologies else ""
        desc = _escape_tex(proj.description) if proj.description else ""

        date_range = ""
        if proj.start_date or proj.end_date:
            if proj.start_date:
                date_range += _format_date(proj.start_date, locale)
            if proj.end_date:
                date_range += f" -- {_format_date(proj.end_date, locale)}"

        lines = []
        lines.append(
            "\\resumeEntry{"
            f"\\mbox{{{_escape_tex(proj.name)}}}"
            "}{"
            f"\\mbox{{{_escape_tex(proj.role or '')}}}"
            "}{"
            f"{date_range}"
            "}{"
            f"{tech}"
            "}"
        )

        if desc:
            lines.append(desc + "\\par")

        if proj.highlights:
            scored = _score_and_sort([_escape_tex(h) for h in proj.highlights])
            lines.append(_render_bullets(scored, policy.max_project_bullets))

        if proj.url:
            display_url = _clean_url(proj.url)
            lines.append(
                f"\\resumeEntrySub{{URL: \\href{{{proj.url}}}{{{display_url}}}}}"
            )

        parts.append("\n".join(lines))
    return "\n\\resumeEntrySep\n".join(parts)


def _render_certifications(certifications: list, locale: Locale) -> str:
    parts = []
    for cert in certifications:
        parts.append(
            "\\resumeCertification{"
            f"{_escape_tex(cert.name)}"
            "}{"
            f"{_escape_tex(cert.issuer)}"
            "}{"
            f"{_format_date(cert.date, locale)}"
            "}"
        )
    return "\n".join(parts)


def _render_awards(awards: list[Award], locale: Locale, policy: DensityPolicy) -> str:
    if not policy.show_awards or not awards:
        return ""
    parts = []
    for award in awards:
        parts.append(
            "\\resumeAward{"
            f"{_escape_tex(award.name)}"
            "}{"
            f"{_escape_tex(award.issuer)}"
            "}{"
            f"{_format_date(award.date, locale)}"
            "}"
        )
        if award.description:
            parts.append(f"\\resumeEntrySub{{{_escape_tex(award.description)}}}")
    return "\n".join(parts)


def _render_volunteer(volunteer: list[VolunteerExperience], locale: Locale, policy: DensityPolicy) -> str:
    if not policy.show_volunteer or not volunteer:
        return ""
    parts = []
    for v in volunteer:
        end = locale.get("label.present") if v.current else _format_date(v.end_date, locale)
        date_range = f"{_format_date(v.start_date, locale)} -- {end}"
        parts.append(
            "\\resumeVolunteer{"
            f"\\mbox{{{_escape_tex(v.organization)}}}"
            "}{"
            f"\\mbox{{{_escape_tex(v.position)}}}"
            "}{"
            f"{date_range}"
            "}{"
            f"{_escape_tex(v.location)}"
            "}"
        )
        if v.highlights:
            esc = [_escape_tex(h) for h in v.highlights]
            parts.append(_render_bullets(esc))
        parts.append("\\vspace{4pt}")
    return "\n".join(parts)


def _render_languages(languages: list, policy: DensityPolicy) -> str:
    if not policy.show_languages or not languages:
        return ""
    parts = []
    for lang in languages:
        parts.append(
            "\\resumeLanguage{"
            f"{_escape_tex(lang.language)}"
            "}{"
            f"{_escape_tex(lang.proficiency)}"
            "}"
        )
    return "\n".join(parts)
