from dataclasses import dataclass


@dataclass(frozen=True)
class DensityPolicy:
    max_experience_items: int | None
    max_experience_bullets: int | None
    show_role_summary: bool
    show_experience_technologies: bool
    max_skills_per_category: int | None
    max_projects: int | None
    max_project_bullets: int | None
    show_awards: bool
    show_volunteer: bool
    show_languages: bool
    min_extra_links_for_section: int


COMPACT = DensityPolicy(
    max_experience_items=3,
    max_experience_bullets=2,
    show_role_summary=False,
    show_experience_technologies=True,
    max_skills_per_category=5,
    max_projects=1,
    max_project_bullets=1,
    show_awards=False,
    show_volunteer=False,
    show_languages=True,
    min_extra_links_for_section=2,
)

FULL = DensityPolicy(
    max_experience_items=None,
    max_experience_bullets=4,
    show_role_summary=True,
    show_experience_technologies=True,
    max_skills_per_category=8,
    max_projects=3,
    max_project_bullets=2,
    show_awards=True,
    show_volunteer=True,
    show_languages=True,
    min_extra_links_for_section=1,
)


DENSITY_MAP: dict[str, DensityPolicy] = {
    "compact": COMPACT,
    "full": FULL,
}
