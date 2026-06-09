from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager

from .config import LLMConfig


class LLMClientError(Exception):
    pass


class _StderrFilter:
    _BANNER_LINES = frozenset({
        "\x1b[1;31mGive Feedback / Get Help: https://github.com/BerriAI/litellm/issues/new\x1b[0m",
        "LiteLLM.Info: If you need to debug this error, use `litellm._turn_on_debug()`.",
    })
    _SUBSTRING_PATTERNS = (
        "Failed to fetch remote model cost map",
    )

    def __init__(self, original) -> None:
        self._original = original

    def write(self, s: str) -> int:
        stripped = s.rstrip("\n")
        if stripped in self._BANNER_LINES:
            return len(s)
        if any(pattern in stripped for pattern in self._SUBSTRING_PATTERNS):
            return len(s)
        return self._original.write(s)

    def flush(self) -> None:
        self._original.flush()

    def __getattr__(self, name):
        return getattr(self._original, name)


@contextmanager
def _filtered_stderr():
    original = sys.stderr
    sys.stderr = _StderrFilter(original)
    try:
        yield
    finally:
        sys.stderr = original


_HELLO_SYSTEM_PROMPT = "You are a connectivity test assistant for hirepaper."
_HELLO_USER_PROMPT = "Reply with a short confirmation that the LiteLLM proxy connection works."
_DIAGNOSTIC_SYSTEM_PROMPT = "You are a diagnostic assistant for hirepaper."
_DIAGNOSTIC_USER_PROMPT = "Reply with a short confirmation."


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return key[:4] + "****"
    return key[:4] + "****" + key[-4:]


def _print_curl(config: LLMConfig, messages: list[dict]) -> None:
    url = config.base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    })
    print(f"curl -X POST {url} \\", file=sys.stderr)
    print(f"  -H \"Content-Type: application/json\" \\", file=sys.stderr)
    print(f"  -H \"Authorization: Bearer {_mask_key(config.api_key)}\" \\", file=sys.stderr)
    print(f"  -d '{body}'", file=sys.stderr)
    print(file=sys.stderr)


def _dump_response(response) -> None:
    try:
        data = response.model_dump()
    except AttributeError:
        try:
            data = response.dict()
        except AttributeError:
            data = dict(response)
    print(json.dumps(data, indent=2, default=str), file=sys.stderr)


def _setup_verbose(verbose: int) -> None:
    if verbose >= 2:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        import litellm
        litellm._turn_on_debug()
        if verbose < 3:
            logging.getLogger("httpx").setLevel(logging.WARNING)
            logging.getLogger("httpcore").setLevel(logging.WARNING)
            logging.getLogger("openai").setLevel(logging.WARNING)


def _extract_text(response) -> str:
    try:
        text = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError):
        try:
            text = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise LLMClientError("model returned no usable text response")
    if not text or not text.strip():
        raise LLMClientError("model returned no usable text response")
    return text.strip()


def _obj_to_dict(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, dict):
        return {k: _obj_to_dict(v) for k, v in obj.items()}
    return obj


def _extract_usage(response) -> dict:
    try:
        usage = response.usage
    except AttributeError:
        try:
            usage = response.get("usage")
        except (KeyError, IndexError, TypeError, AttributeError):
            raise LLMClientError("model returned no usable usage information")
    if usage is None:
        raise LLMClientError("model returned no usable usage information")
    return _obj_to_dict(usage)


def _complete(config: LLMConfig, messages: list[dict]) -> object:
    try:
        with _filtered_stderr():
            import litellm
            from litellm import completion

            litellm.suppress_debug_info = True
            litellm.set_verbose = False
            response = completion(
                model=config.model,
                messages=messages,
                api_base=config.base_url,
                api_key=config.api_key,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                timeout=config.timeout_seconds,
            )
    except Exception as e:
        raise LLMClientError(f"LLM request failed: {e}")
    return response


def send_hello(config: LLMConfig, verbose: int = 0) -> str:
    with _filtered_stderr():
        if verbose == 1:
            _print_curl(config, [
                {"role": "system", "content": _HELLO_SYSTEM_PROMPT},
                {"role": "user", "content": _HELLO_USER_PROMPT},
            ])
        _setup_verbose(verbose)

        response = _complete(config, [
            {"role": "system", "content": _HELLO_SYSTEM_PROMPT},
            {"role": "user", "content": _HELLO_USER_PROMPT},
        ])

    text = _extract_text(response)

    if verbose == 1:
        _dump_response(response)

    return text


def check_health(config: LLMConfig, verbose: int = 0) -> str:
    with _filtered_stderr():
        if verbose == 1:
            _print_curl(config, [
                {"role": "system", "content": _DIAGNOSTIC_SYSTEM_PROMPT},
                {"role": "user", "content": _DIAGNOSTIC_USER_PROMPT},
            ])
        _setup_verbose(verbose)

        response = _complete(config, [
            {"role": "system", "content": _DIAGNOSTIC_SYSTEM_PROMPT},
            {"role": "user", "content": _DIAGNOSTIC_USER_PROMPT},
        ])

    text = _extract_text(response)

    if verbose == 1:
        _dump_response(response)

    return text


def get_usage(config: LLMConfig, verbose: int = 0) -> dict[str, int]:
    with _filtered_stderr():
        if verbose == 1:
            _print_curl(config, [
                {"role": "system", "content": _DIAGNOSTIC_SYSTEM_PROMPT},
                {"role": "user", "content": _DIAGNOSTIC_USER_PROMPT},
            ])
        _setup_verbose(verbose)

        response = _complete(config, [
            {"role": "system", "content": _DIAGNOSTIC_SYSTEM_PROMPT},
            {"role": "user", "content": _DIAGNOSTIC_USER_PROMPT},
        ])

    tokens = _extract_usage(response)

    if verbose == 1:
        _dump_response(response)

    return tokens
