"""Glossary post-processor: enforces canonical translations after the MT pass.

Glossary file is JSON: `{ "mt_term_lowercase": "canonical replacement", ... }`.
Matches are case-insensitive but whole-word, so "POS" won't match inside "POST".
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def load(path: str | Path) -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def apply(text: str, glossary: dict[str, str]) -> str:
    for mt_term, canonical in glossary.items():
        text = re.compile(r"\b" + re.escape(mt_term) + r"\b", re.IGNORECASE).sub(canonical, text)
    return text
