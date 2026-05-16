"""XLIFF parser + rewriter unit tests."""

from src.xliff import extract_units, replace_targets


SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2">
  <file>
    <body>
      <trans-unit id="a">
        <source><![CDATA[hello]]></source>
        <target><![CDATA[]]></target>
      </trans-unit>
      <trans-unit id="b">
        <source><![CDATA[<strong>world</strong>]]></source>
        <target><![CDATA[]]></target>
      </trans-unit>
    </body>
  </file>
</xliff>"""


def test_extract_units():
    units = extract_units(SAMPLE)
    assert units == [("a", "hello"), ("b", "<strong>world</strong>")]


def test_replace_targets_writes_translated_text():
    out = replace_targets(SAMPLE, {"a": "merhaba", "b": "<strong>dünya</strong>"})
    assert "<target><![CDATA[merhaba]]></target>" in out
    assert "<target><![CDATA[<strong>dünya</strong>]]></target>" in out


def test_replace_targets_escapes_cdata_terminator():
    """A translation containing `]]>` must not break the CDATA block."""
    nasty = "before ]]> after"
    out = replace_targets(SAMPLE, {"a": nasty})
    # The raw `]]>` must not appear inside the target CDATA;
    # it should have been split by the CDATA escape.
    assert "<target><![CDATA[before ]]]]><![CDATA[> after]]></target>" in out
