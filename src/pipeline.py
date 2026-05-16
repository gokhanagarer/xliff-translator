"""Chunked, HTML-tag-safe translation of long source strings."""

from __future__ import annotations

import re

from .translators import Translator

MAX_CHARS = 4500


def _chunk(text: str) -> list[str]:
    """Split `text` into chunks under MAX_CHARS, preferring paragraph then sentence breaks."""
    if len(text) <= MAX_CHARS:
        return [text]
    chunks: list[str] = []
    for para in text.split("\n\n"):
        if len(para) <= MAX_CHARS:
            chunks.append(para)
            continue
        # sentence-level split
        sentences = re.split(r"(?<=[.!?])\s+", para)
        buf = ""
        for s in sentences:
            if len(buf) + len(s) + 1 > MAX_CHARS:
                if buf:
                    chunks.append(buf)
                buf = s
            else:
                buf = (buf + " " + s) if buf else s
        if buf:
            chunks.append(buf)
    return chunks


def translate_string(translator: Translator, text: str) -> str:
    """Translate `text` while preserving inline HTML tags exactly.

    Tags are replaced with `§TAGn§` placeholders before translation and restored after,
    so backends that mangle HTML (e.g. Google Translate) cannot break the XLIFF output.
    """
    if not text.strip():
        return text

    tags: list[str] = []

    def protect(m: re.Match[str]) -> str:
        tags.append(m.group(0))
        return f"§TAG{len(tags) - 1}§"

    protected = re.sub(r"<[^>]+>", protect, text)
    translated_chunks = [translator.translate(c) if c.strip() else c for c in _chunk(protected)]
    joined = "\n\n".join(translated_chunks)

    def restore(m: re.Match[str]) -> str:
        idx = int(m.group(1))
        return tags[idx] if idx < len(tags) else m.group(0)

    return re.sub(r"§TAG(\d+)§", restore, joined)
