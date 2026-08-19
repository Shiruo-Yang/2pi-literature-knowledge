from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures = []
for line in (ROOT / "checksums.sha256").read_text(encoding="utf-8").splitlines():
    digest, relative = line.split("  ", 1)
    path = ROOT / relative
    if not path.exists():
        failures.append(f"missing: {relative}")
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != digest:
        failures.append(f"checksum mismatch: {relative}")
for path in ROOT.rglob("*"):
    if not path.is_file() or path.name in {"checksums.sha256", "package_manifest.json"}:
        continue
    if path.relative_to(ROOT).as_posix() == "scripts/validate_release.py":
        continue
    if path.suffix.lower() not in {".csv", ".md", ".json", ".txt", ".py"} and path.name != "VERSION":
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for pattern in (r"[A-Z]:\\", r"/share/home/", r"(?i)round\s*29", r"(?i)methods_c1|#\s*C1\b|\bC1 formalises"):
        if re.search(pattern, text):
            failures.append(f"sensitive/internal token in {path.relative_to(ROOT)}: {pattern}")
if failures:
    raise SystemExit("\n".join(failures))
print("Release validation passed.")
