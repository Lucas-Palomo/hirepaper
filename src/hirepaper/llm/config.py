from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib


DEFAULT_CONFIG_PATH = "config.toml"
_OPTIONAL_DEFAULTS = {
    "temperature": 0.2,
    "timeout_seconds": 60,
    "max_tokens": 256,
}
_CONTENT_COMMAND_FALLBACKS = {
    "content_match": {
        "timeout_seconds": 300,
        "max_tokens": 60000,
    },
    "content_tailor": {
        "timeout_seconds": 300,
        "max_tokens": 60000,
    },
    "linkedin_generate": {
        "timeout_seconds": 300,
        "max_tokens": 60000,
    },
}
_KNOWN_COMMAND_PROFILES = frozenset({
    "content_match",
    "content_tailor",
    "linkedin_generate",
})


class LLMConfigError(Exception):
    pass


class LLMConfig:
    def __init__(self, data: dict[str, Any]) -> None:
        self.base_url: str = data["base_url"]
        self.api_key: str = data["api_key"]
        self.model: str = data["model"]
        self.temperature: float = data.get("temperature", _OPTIONAL_DEFAULTS["temperature"])
        self.timeout_seconds: int = data.get("timeout_seconds", _OPTIONAL_DEFAULTS["timeout_seconds"])
        self.max_tokens: int = data.get("max_tokens", _OPTIONAL_DEFAULTS["max_tokens"])
        self.source_format: str = data.get("_source_format", "env")
        self.profile: str | None = data.get("_profile")
        self.config_path: str | None = data.get("_config_path")


def _ensure_dict(value: object, ctx: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LLMConfigError(f"invalid config {ctx} — expected a TOML table")
    return value


def _parse_optional_number(value: object, field_name: str, source_name: str) -> float | int:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise LLMConfigError(f"invalid {source_name} — field '{field_name}' must be a number")
    return value


def _read_toml_file(path: Path, config_path_str: str) -> dict[str, Any]:
    if not path.exists():
        raise LLMConfigError(f"config file not found: {config_path_str}")
    if not os.access(path, os.R_OK):
        raise LLMConfigError(f"config file not readable: {config_path_str}")
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        raise LLMConfigError(f"config file read error: {config_path_str} — {e}")
    try:
        data = tomllib.loads(raw)
    except tomllib.TOMLDecodeError as e:
        raise LLMConfigError(f"invalid config TOML: {config_path_str} — {e}")
    return _ensure_dict(data, "root")


def _env_number(name: str) -> float | int | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    try:
        if any(ch in raw for ch in (".", "e", "E")):
            return float(raw)
        return int(raw)
    except ValueError as e:
        raise LLMConfigError(f"invalid environment variable '{name}' — expected a number ({e})")


def _env_string(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    return raw


def _profile_env_prefix(profile: str | None) -> str | None:
    if profile == "content_match":
        return "LLM_CONTENT_MATCH"
    if profile == "content_tailor":
        return "LLM_CONTENT_TAILOR"
    if profile == "linkedin_generate":
        return "LLM_LINKEDIN_GENERATE"
    return None


def _load_env_sections(profile: str | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    llm = {}
    defaults = {}
    profile_section = {}

    base_url = _env_string("LLM_BASE_URL")
    api_key = _env_string("LLM_API_KEY")
    model = _env_string("LLM_MODEL")
    if base_url is not None:
        llm["base_url"] = base_url
    if api_key is not None:
        llm["api_key"] = api_key
    if model is not None:
        llm["model"] = model

    temperature = _env_number("LLM_TEMPERATURE")
    timeout_seconds = _env_number("LLM_TIMEOUT_SECONDS")
    max_tokens = _env_number("LLM_MAX_TOKENS")
    if temperature is not None:
        defaults["temperature"] = temperature
    if timeout_seconds is not None:
        defaults["timeout_seconds"] = timeout_seconds
    if max_tokens is not None:
        defaults["max_tokens"] = max_tokens

    env_prefix = _profile_env_prefix(profile)
    if env_prefix is not None:
        profile_timeout = _env_number(f"{env_prefix}_TIMEOUT_SECONDS")
        profile_max_tokens = _env_number(f"{env_prefix}_MAX_TOKENS")
        if profile_timeout is not None:
            profile_section["timeout_seconds"] = profile_timeout
        if profile_max_tokens is not None:
            profile_section["max_tokens"] = profile_max_tokens

    return llm, defaults, profile_section


def _merge_sections(
    env_sections: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
    file_sections: tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    llm = dict(env_sections[0])
    defaults = dict(env_sections[1])
    profile_section = dict(env_sections[2])

    if file_sections is not None:
        llm.update(file_sections[0])
        defaults.update(file_sections[1])
        profile_section.update(file_sections[2])

    return llm, defaults, profile_section


def _extract_toml_sections(raw: dict[str, Any], profile: str | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    llm = _ensure_dict(raw.get("llm", {}), "section 'llm'")
    defaults = _ensure_dict(llm.get("defaults", {}), "section 'llm.defaults'")
    profile_section: dict[str, Any] = {}
    if profile is not None:
        profile_section = _ensure_dict(llm.get(profile, {}), f"section 'llm.{profile}'")

    return dict(llm), dict(defaults), dict(profile_section)


def _resolve_required_string(llm: dict[str, Any], field_name: str) -> str:
    value = llm.get(field_name)
    if not isinstance(value, str) or value.strip() == "":
        raise LLMConfigError(
            f"missing required configuration value '{field_name}' "
            f"(set it in {DEFAULT_CONFIG_PATH} or the matching environment variable)"
        )
    return value


def _resolve_optional_number(
    profile_section: dict[str, Any],
    defaults: dict[str, Any],
    llm: dict[str, Any],
    field_name: str,
) -> float | int | None:
    for section_name, section in (
        ("profile", profile_section),
        ("defaults", defaults),
        ("llm", llm),
    ):
        if field_name in section:
            return _parse_optional_number(section[field_name], field_name, f"{section_name} config")
    return None


def load_config(config_path_str: str | None = None, profile: str | None = None) -> LLMConfig:
    if profile is not None and profile not in _KNOWN_COMMAND_PROFILES:
        raise LLMConfigError(f"unknown config profile: {profile}")

    env_sections = _load_env_sections(profile)
    config_path: Path | None = None
    source_format = "env"

    if config_path_str is not None:
        config_path = Path(config_path_str)
    else:
        default_path = Path(DEFAULT_CONFIG_PATH)
        if default_path.exists():
            config_path = default_path

    file_sections = None
    if config_path is not None:
        raw = _read_toml_file(config_path, str(config_path))
        file_sections = _extract_toml_sections(raw, profile)
        source_format = "toml"

    llm, defaults, profile_section = _merge_sections(env_sections, file_sections)

    resolved = {
        "base_url": _resolve_required_string(llm, "base_url"),
        "api_key": _resolve_required_string(llm, "api_key"),
        "model": _resolve_required_string(llm, "model"),
        "_source_format": source_format,
        "_profile": profile,
        "_config_path": str(config_path) if config_path is not None else None,
    }

    temperature = _resolve_optional_number(profile_section, defaults, llm, "temperature")
    timeout_seconds = _resolve_optional_number(profile_section, defaults, llm, "timeout_seconds")
    max_tokens = _resolve_optional_number(profile_section, defaults, llm, "max_tokens")

    if temperature is not None:
        resolved["temperature"] = temperature

    if timeout_seconds is not None:
        resolved["timeout_seconds"] = timeout_seconds
    elif profile in _CONTENT_COMMAND_FALLBACKS:
        resolved["timeout_seconds"] = _CONTENT_COMMAND_FALLBACKS[profile]["timeout_seconds"]

    if max_tokens is not None:
        resolved["max_tokens"] = max_tokens
    elif profile in _CONTENT_COMMAND_FALLBACKS:
        resolved["max_tokens"] = _CONTENT_COMMAND_FALLBACKS[profile]["max_tokens"]

    return LLMConfig(resolved)
