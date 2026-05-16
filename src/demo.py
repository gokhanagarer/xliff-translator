"""`make demo` entrypoint — run the pipeline on bundled XLIFF files, offline."""

import os

from .main import main

if __name__ == "__main__":
    os.environ.setdefault("OFFLINE", "1")
    raise SystemExit(main([]))
