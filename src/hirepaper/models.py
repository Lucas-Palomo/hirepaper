from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Link:
    label: str
    url: str


@dataclass
class Phone:
    value: str
    hyperlink: str


@dataclass
class Personal:
    name: str
    email: str
    phone: Phone
    location: str
    headline: Optional[str] = None
    links: list[Link] = field(default_factory=list)
    extra_links: list[Link] = field(default_factory=list)


@dataclass
class AchievementContext:
    action: Optional[str] = None
    result: Optional[str] = None
    metrics: Optional[str] = None


@dataclass
class Achievement:
    situation: Optional[str] = None
    task: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None
    metrics: Optional[str] = None
    summary: Optional[str] = None
    context: Optional[AchievementContext] = None


@dataclass
class Experience:
    company: str
    position: str
    location: str
    start_date: str
    end_date: Optional[str]
    current: bool
    technologies: list[str] = field(default_factory=list)
    role_summary: Optional[str] = None
    scope: Optional[str] = None
    employment_type: Optional[str] = None
    achievements: list[Achievement] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)


@dataclass
class Education:
    institution: str
    degree: str
    location: str
    start_date: str
    end_date: str
    gpa: Optional[str] = None
    honors: Optional[str] = None


@dataclass
class SkillCategory:
    name: str
    items: list[str] = field(default_factory=list)


@dataclass
class Skills:
    categories: list[SkillCategory] = field(default_factory=list)


@dataclass
class Project:
    name: str
    description: str
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    technologies: list[str] = field(default_factory=list)
    url: Optional[str] = None
    highlights: list[str] = field(default_factory=list)


@dataclass
class Certification:
    name: str
    issuer: str
    date: str


@dataclass
class Language:
    language: str
    proficiency: str


@dataclass
class Award:
    name: str
    issuer: str
    date: str
    description: Optional[str] = None


@dataclass
class VolunteerExperience:
    organization: str
    position: str
    location: str
    start_date: str
    end_date: Optional[str]
    current: bool
    highlights: list[str] = field(default_factory=list)


@dataclass
class Candidate:
    personal: Personal
    summary: str
    target_role: Optional[str] = None
    experience: list[Experience] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)
    skills: Optional[Skills] = None
    projects: list[Project] = field(default_factory=list)
    certifications: list[Certification] = field(default_factory=list)
    languages: list[Language] = field(default_factory=list)
    awards: list[Award] = field(default_factory=list)
    volunteer: list[VolunteerExperience] = field(default_factory=list)
