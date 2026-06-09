import gettext

from ._resources import locale_dir


_DOMAIN = "messages"
_FALLBACK_LOCALE = "en"


def _normalize(locale_id: str) -> str:
    return locale_id.replace("-", "_")


class Locale:
    def __init__(self, locale_id: str = "en"):
        locale_id = _normalize(locale_id)

        try:
            self._translations = gettext.translation(
                _DOMAIN,
                localedir=str(locale_dir()),
                languages=[locale_id, _FALLBACK_LOCALE],
                fallback=True,
            )
        except FileNotFoundError:
            self._translations = gettext.NullTranslations()

    def get(self, key: str, default: str | None = None) -> str:
        val = self._translations.gettext(key)
        if val == key:
            return default if default is not None else key
        return val

    def month_abbr(self, month_num: str) -> str:
        return self.get(f"month.{month_num}")
