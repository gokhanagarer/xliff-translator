"""XLIFF (WPML flavour) parsing and rewriting — CDATA-safe."""

from __future__ import annotations

import re

# Captures (trans_unit_id, source_text) pairs even when the file has noisy
# attribute ordering; CDATA contents are kept verbatim including HTML tags.
_UNIT_PATTERN = re.compile(
    r'<trans-unit[^>]+id="([^"]+)"[^>]*>.*?<source><!\[CDATA\[(.*?)\]\]></source>',
    re.DOTALL,
)


def extract_units(xml: str) -> list[tuple[str, str]]:
    """Return [(id, source_text)] for every translatable trans-unit."""
    return [(m.group(1), m.group(2).strip()) for m in _UNIT_PATTERN.finditer(xml)]


def _cdata_escape(text: str) -> str:
    """Make `text` safe to embed inside a `<![CDATA[ ... ]]>` block."""
    return text.replace("]]>", "]]]]><![CDATA[>")


def replace_targets(xml: str, translations: dict[str, str]) -> str:
    """Replace the `<target>` CDATA for each translated id. Leaves other markup intact."""
    for uid, translation in translations.items():
        safe = _cdata_escape(translation)
        pattern = re.compile(
            r'(<trans-unit[^>]+id="'
            + re.escape(uid)
            + r'"[^>]*>.*?<target><!\[CDATA\[)(.*?)(\]\]></target>)',
            re.DOTALL,
        )
        xml = pattern.sub(lambda m, s=safe: m.group(1) + s + m.group(3), xml)
    return xml
