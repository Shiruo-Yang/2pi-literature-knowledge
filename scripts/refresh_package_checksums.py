"""Refresh hashes for Git-visible public assets, excluding the hash file itself."""
import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root).decode("utf-8").split("\0")
manifest_path = root / "package_manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
if "historical_study_build" not in manifest:
    manifest["historical_study_build"] = {k: manifest[k] for k in ("package", "release", "release_date", "principle", "builder_version", "builder_sha256", "source_asset_sha256")}
manifest.update(package="photoinitiator_literature_knowledge_database", release="normalized-literature-database", release_date="2026-10-15", principle="preserved evidence with explicit provenance and permitted-use status", builder_version="normalized_literature_database", builder_sha256=hashlib.sha256((root / "scripts/normalize_literature_database.py").read_bytes()).hexdigest())
import csv
with (root / "data/literature/input_assets.csv").open(encoding="utf-8-sig", newline="") as f:
    manifest["source_asset_sha256"] = {r["asset_key"]: r["sha256"] for r in csv.DictReader(f)}
manifest["file_sha256"] = {n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in sorted(set(files)) if n and n not in {"checksums.sha256", "package_manifest.json"} and (root / n).is_file()}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
lines = []
for name in sorted(set(files)):
    if not name or name == "checksums.sha256":
        continue
    path = root / name
    if path.is_file():
        lines.append(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + name)
(root / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print("Hashed", len(lines), "public files.")
