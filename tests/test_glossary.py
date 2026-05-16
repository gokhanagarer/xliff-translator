from src.glossary import apply, load
from pathlib import Path


def test_apply_replaces_case_insensitive_whole_word():
    g = {"open science": "Open Science"}
    assert apply("the OPEN science movement", g) == "the Open Science movement"


def test_apply_skips_partial_matches():
    g = {"pos": "POS"}
    assert apply("the POS rate increased to 12%", g) == "the POS rate increased to 12%"
    # Not part of POSITIVE
    assert apply("a positive trend", g) == "a positive trend"


def test_load_missing_file_returns_empty():
    assert load(Path("/nonexistent/glossary.json")) == {}
