# Getting started

A step-by-step guide. Aim: translate two XLIFF files in your terminal in under 5 minutes, with zero API keys.

If anything breaks, jump to [Troubleshooting](#troubleshooting).

---

## 0. Prerequisites

You need:
- **Python 3.10+** (`python3 --version`)
- **git** (`git --version`)
- A Unix-like shell (macOS Terminal, Linux, WSL on Windows)

That's it for the demo. API keys are only needed for live translation.

---

## 1. Clone and run the demo

```bash
git clone https://github.com/gokhanagarer/xliff-translator.git
cd xliff-translator
make demo
```

What just happened:
- `make demo` created `.venv/` and installed `python-dotenv`
- Used the offline stub translator (no network)
- Read the two bundled XLIFF files in `examples/source/`
- Applied the demo glossary (`examples/glossary.json`)
- Wrote translated XLIFF + ZIP to `output/`

Open one of the translated files. Every `<target>` block that was empty in the source now has translated content with `[EN]` prefixes — that's the stub backend's "I translated this" marker. With a real backend (next section), the prefix disappears.

The ZIP at `output/translated.zip` is the format WPML expects for re-import.

---

## 2. Switch to a real backend

The repo ships three backends. Pick whichever fits.

### Option A — Google Translate, free, no API key

```bash
cp .env.example .env
# In .env, set:
#   OFFLINE=0
#   TRANSLATOR_BACKEND=google
```

Install the dev deps (Google backend uses `deep-translator`):

```bash
make install-dev
```

Run again:

```bash
.venv/bin/python -m src.main \
  --source examples/source \
  --output output/translated \
  --all
```

You'll see real Turkish-to-English translations. Free tier is rate-limited (~1 req/5 s) but unmetered.

### Option B — Claude (Anthropic), paid, highest quality

1. Get a key at https://console.anthropic.com
2. In `.env`:
   ```
   OFFLINE=0
   TRANSLATOR_BACKEND=anthropic
   ANTHROPIC_API_KEY=sk-ant-...
   ANTHROPIC_MODEL=claude-sonnet-4-6
   ```
3. Run:
   ```bash
   .venv/bin/python -m src.main --source examples/source --output output/translated --all
   ```

Claude understands HTML structure and idiom better than free MT — worth the cost for content where quality matters more than throughput.

---

## 3. Translate your own XLIFF files

### 3.1 Export from WPML

In your WordPress admin: **WPML** → **Translation Management** → select posts → export as XLIFF → download the ZIP.

### 3.2 Run

```bash
unzip your-export.zip -d ~/my-translations/source
.venv/bin/python -m src.main \
  --source ~/my-translations/source \
  --output ~/my-translations/translated \
  --all
```

When done, `~/my-translations/translated.zip` is ready to import back into WPML.

### 3.3 Resume mode (don't re-translate what's already done)

Re-running without `--all` skips any file that already exists in `output/`. Useful when you hit a rate limit mid-batch and want to pick up where you left off:

```bash
# Just run without --all
.venv/bin/python -m src.main --source ~/my-translations/source --output ~/my-translations/translated
```

The console prints `Source: 50 · Translated: 32 · To do: 18` so you can see progress at a glance.

---

## 4. Custom glossary

The glossary enforces canonical translations after the MT pass. It's a flat JSON file of `{ "machine-translated term": "canonical replacement" }`.

The bundled `examples/glossary.json` is tiny — for real work, build your own. Example for a SaaS use case:

```json
{
  "user experience":  "user experience",
  "ux":               "UX",
  "customer journey": "customer journey",
  "open source":      "open source",
  "the saas":         "the SaaS"
}
```

Pass with `--glossary path/to/your-glossary.json`. Matches are case-insensitive but **whole-word**, so `ux` won't trigger inside `auxiliary`.

> **Tip**: rebuild your glossary iteratively. After a real run, scan the output for terms the MT got wrong, add the wrong→right mapping, re-run with `--all`. After 2–3 iterations the glossary covers your most-frequent misses.

---

## 5. What "HTML-tag protection" means

If your XLIFF has source text like:

```html
This is <strong>important</strong> for <a href="https://example.com">growth</a>.
```

Naive MT often breaks the tags — translates `strong` as "güçlü", drops the closing tag, mangles the URL. The pipeline:

1. **Protects** every `<...>` with a `§TAG0§` placeholder before sending to the MT backend
2. **Translates** just the plain text
3. **Restores** the original tags exactly where the placeholders were

You'll see this in the tests — `tests/test_xliff.py::test_replace_targets_writes_translated_text` round-trips an HTML-laden source through the pipeline.

---

## 6. CDATA safety

WPML XLIFF wraps `<source>` and `<target>` text in CDATA blocks. Translations that happen to contain `]]>` (rare but real) would break the file. The pipeline escapes them by splitting the CDATA:

```
before ]]> after
→
before ]]]]><![CDATA[> after
```

(Yes that's weird-looking. It's the only safe way; the test `test_replace_targets_escapes_cdata_terminator` pins this behaviour.)

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `make: command not found` | `make` not installed | macOS: `xcode-select --install`. Linux: `sudo apt install build-essential` |
| `No XLIFF files in examples/source` | Wrong working directory | `cd` into the repo root before running |
| Translations come out reversed with `[EN]` prefix | Still using the stub | Set `OFFLINE=0` and a real `TRANSLATOR_BACKEND` in `.env` |
| `deep_translator` import error | Forgot `make install-dev` | Run it; Google backend isn't in the base requirements |
| Google backend stops translating mid-batch | Hit free-tier rate limit | Wait 60 s, re-run without `--all` to resume |
| Anthropic `401 Unauthorized` | Wrong API key or missing prefix | Anthropic keys start with `sk-ant-` |
| Tags broken in output | Backend stripped placeholders | Open an issue with a small repro — the regex handling lives in `src/pipeline.py` |

---

## Where to look next

- `src/xliff.py` — the CDATA-safe parser and rewriter (50 lines, fully tested)
- `src/translators.py` — adding a backend takes ~30 lines; implement `translate(text)` on a class and register it in `_BACKENDS`
- `src/pipeline.py` — chunking + HTML-tag protection
