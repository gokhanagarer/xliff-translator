"""Pluggable translation backends.

- `OfflineStubTranslator` — deterministic, no network. Used by `make demo` and tests.
- `GoogleFreeTranslator` — `deep-translator` wrapper, free, no API key.
- `AnthropicTranslator` — Claude. Requires `ANTHROPIC_API_KEY`.

Pick a backend by name with `get(name)`. Pass `OFFLINE=1` (or leave it unset) and
the offline stub is used; otherwise the requested backend is constructed.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Protocol

log = logging.getLogger(__name__)


class Translator(Protocol):
    """Minimal contract — every backend implements this."""

    def translate(self, text: str) -> str: ...


# ── 1. Offline stub ───────────────────────────────────────────────────────────

class OfflineStubTranslator:
    """Deterministic, no network. Pretends to translate by:
       - leaving ASCII tokens (likely HTML / URLs / brand names) alone
       - reversing other tokens and prefixing `[EN]`
    The output is recognisably "translated" without claiming to be real translation.
    """

    def translate(self, text: str) -> str:
        if not text.strip():
            return text

        def transform(token: str) -> str:
            if not token or token.isspace():
                return token
            if re.fullmatch(r"[\s\w\.,;:/?!()\-=\+]+", token) and token.isascii():
                return token
            return f"[EN]{token[::-1]}"

        tokens = re.split(r"(\s+)", text)
        return "".join(transform(t) for t in tokens)


# ── 2. deep-translator (free Google Translate) ────────────────────────────────

class GoogleFreeTranslator:
    """`deep-translator` Google backend with retry/backoff."""

    def __init__(self, source: str = "tr", target: str = "en"):
        from deep_translator import GoogleTranslator
        self._t = GoogleTranslator(source=source, target=target)

    def translate(self, text: str) -> str:
        from deep_translator.exceptions import RequestError, TooManyRequests
        for delay in (0, 2, 5, 15, 30):
            if delay:
                log.warning("retry in %ds", delay)
                time.sleep(delay)
            try:
                return self._t.translate(text)
            except (RequestError, TooManyRequests) as e:
                last = e
                continue
        raise RuntimeError(f"GoogleFreeTranslator failed after retries: {last}")


# ── 3. Anthropic ──────────────────────────────────────────────────────────────

class AnthropicTranslator:
    """Claude-backed translator. Requires ANTHROPIC_API_KEY."""

    DEFAULT_SYSTEM = (
        "You are a senior content translator. Translate the user's text fully. "
        "Preserve every HTML tag, URL, and brand name exactly. Output ONLY the "
        "translated text — no commentary, no preamble."
    )

    def __init__(self, model: str | None = None, system: str | None = None,
                 source: str = "Turkish", target: str = "English"):
        import anthropic
        self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self._model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        self._system = system or self.DEFAULT_SYSTEM
        self._source = source
        self._target = target

    def translate(self, text: str) -> str:
        prompt = f"Translate from {self._source} to {self._target}:\n\n{text}"
        resp = self._client.messages.create(
            model=self._model,
            system=self._system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
        )
        return resp.content[0].text.strip()


# ── factory ───────────────────────────────────────────────────────────────────

_BACKENDS = {
    "stub": OfflineStubTranslator,
    "google": GoogleFreeTranslator,
    "anthropic": AnthropicTranslator,
}


def get(name: str | None = None) -> Translator:
    """Return a translator instance. Honors OFFLINE=1 unless name is explicit."""
    if name is None:
        if os.environ.get("OFFLINE", "0") == "1" or not os.environ.get("TRANSLATOR_BACKEND"):
            name = "stub"
        else:
            name = os.environ["TRANSLATOR_BACKEND"]
    cls = _BACKENDS.get(name)
    if not cls:
        raise ValueError(f"Unknown translator: {name}. Available: {list(_BACKENDS)}")
    return cls()
