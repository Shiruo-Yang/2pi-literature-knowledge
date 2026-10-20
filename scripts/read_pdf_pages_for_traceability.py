"""Isolated original-PDF text extraction in an existing pypdf environment."""
import json
import sys
from pathlib import Path
from pypdf import PdfReader

if __name__ == "__main__":
    source, output = map(Path, sys.argv[1:])
    reader = PdfReader(str(source))
    rows = [(str(i), page.extract_text() or "") for i, page in enumerate(reader.pages, 1)]
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(rows, handle, ensure_ascii=False)
