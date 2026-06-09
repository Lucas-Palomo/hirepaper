import sys
from pathlib import Path


def _project_root() -> Path:
    try:
        return Path(sys._MEIPASS)
    except AttributeError:
        return Path(__file__).parent.parent.parent


def templates_dir() -> Path:
    return _project_root() / "templates"


def locale_dir() -> Path:
    return _project_root() / "locale"


def icons_dir() -> Path:
    return _project_root() / "assets" / "icons"


def prompts_dir() -> Path:
    return _project_root() / "assets" / "prompts"


def schemas_dir() -> Path:
    return _project_root() / "assets" / "schemas"


def config_template_path() -> Path:
    return _project_root() / "assets" / "examples" / "config.example.toml"


def example_candidate_path() -> Path:
    return _project_root() / "assets" / "examples" / "candidate.example.json"
