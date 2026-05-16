"""End-to-end demo run — translates bundled fixtures using the offline stub."""

import os
from pathlib import Path

from src.main import main


def test_offline_demo_writes_translated_xliff(monkeypatch, tmp_path):
    monkeypatch.setenv("OFFLINE", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    project = Path(__file__).resolve().parent.parent
    out = tmp_path / "out"

    rc = main(["--source", str(project / "examples" / "source"),
               "--output", str(out),
               "--glossary", str(project / "examples" / "glossary.json"),
               "--all"])

    assert rc == 0
    files = list(out.glob("*.xliff"))
    assert len(files) == 2

    for f in files:
        content = f.read_text(encoding="utf-8")
        # Every target block must now have a non-empty CDATA (stub translator output)
        assert "<target><![CDATA[]]></target>" not in content
        # Stub prefix appears in non-ASCII content
        assert "[EN]" in content
