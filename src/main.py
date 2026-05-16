"""Orchestrator: walk a directory of .xliff files, translate each unit, write output + ZIP."""

from __future__ import annotations

import argparse
import logging
import sys
import zipfile
from pathlib import Path

from dotenv import load_dotenv

from . import glossary, translators, xliff
from .pipeline import translate_string

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("xliff")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "examples" / "source"
DEFAULT_OUTPUT = ROOT / "output" / "translated"
DEFAULT_ZIP = ROOT / "output" / "translated.zip"
DEFAULT_GLOSSARY = ROOT / "examples" / "glossary.json"


def translate_units(
    units: list[tuple[str, str]],
    translator: translators.Translator,
    glossary_map: dict[str, str],
) -> dict[str, str]:
    out: dict[str, str] = {}
    for uid, source in units:
        if not source.strip():
            out[uid] = ""
            continue
        try:
            mt = translate_string(translator, source)
        except Exception:  # noqa: BLE001
            log.exception("  unit %s failed; keeping source", uid)
            out[uid] = source
            continue
        out[uid] = glossary.apply(mt, glossary_map)
    return out


def process(
    source_dir: Path,
    output_dir: Path,
    *,
    translate_all: bool,
    dry_run: bool,
    backend: str | None,
    glossary_path: Path,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    source_files = sorted(source_dir.glob("*.xliff"))
    if not source_files:
        log.error("No XLIFF files in %s", source_dir)
        return 1

    if translate_all:
        todo = source_files
    else:
        existing = {p.name for p in output_dir.glob("*.xliff")}
        todo = [p for p in source_files if p.name not in existing]

    log.info("Source: %d  ·  Translated: %d  ·  To do: %d",
             len(source_files), len(source_files) - len(todo), len(todo))

    if not todo:
        log.info("Nothing to do — output is up to date.")
        return 0

    if dry_run:
        for p in todo:
            log.info("  %s", p.name)
        return 0

    translator = translators.get(backend)
    glossary_map = glossary.load(glossary_path)
    log.info("Backend: %s · Glossary entries: %d",
             translator.__class__.__name__, len(glossary_map))

    success, failed = 0, []
    for i, src in enumerate(todo, 1):
        log.info("[%d/%d] %s", i, len(todo), src.name)
        try:
            raw = src.read_text(encoding="utf-8")
            units = xliff.extract_units(raw)
            if not units:
                log.info("  no trans-units; passing through")
                (output_dir / src.name).write_text(raw, encoding="utf-8")
                success += 1
                continue
            log.info("  translating %d unit(s)", len(units))
            translations = translate_units(units, translator, glossary_map)
            (output_dir / src.name).write_text(
                xliff.replace_targets(raw, translations), encoding="utf-8"
            )
            success += 1
        except Exception:  # noqa: BLE001
            log.exception("  failed")
            failed.append(src.name)

    log.info("Done. %d ok, %d failed.", success, len(failed))

    translated = list(output_dir.glob("*.xliff"))
    if translated:
        zip_path = output_dir.parent / "translated.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in translated:
                zf.write(p, p.name)
        log.info("ZIP: %s (%d files)", zip_path, len(translated))

    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="WPML XLIFF translator with pluggable backends")
    p.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="directory of .xliff files")
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="output directory")
    p.add_argument("--backend", choices=["stub", "google", "anthropic"], default=None,
                   help="override TRANSLATOR_BACKEND env")
    p.add_argument("--glossary", type=Path, default=DEFAULT_GLOSSARY,
                   help="JSON file of canonical replacements")
    p.add_argument("--all", action="store_true", help="re-translate everything (default: resume)")
    p.add_argument("--dry-run", action="store_true", help="list files only; no translation")
    args = p.parse_args(argv)

    return process(
        args.source,
        args.output,
        translate_all=args.all,
        dry_run=args.dry_run,
        backend=args.backend,
        glossary_path=args.glossary,
    )


if __name__ == "__main__":
    sys.exit(main())
