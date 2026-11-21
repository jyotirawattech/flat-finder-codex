#!/usr/bin/env python3
"""Build an allowlisted, synthetic-only release. No private workspace argument."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "flat-finder"
sys.path.insert(0, str(SKILL / "scripts"))
from ff_core import VERSION, csv_report, markdown_report, read_json, workspace_state
from flat_finder import init_workspace
from install import hashes

ALLOWED_ROOT_FILES = {"README.md", "LICENSE", "AGENTS.md", ".gitignore"}


def source_files():
    files = [ROOT / p for p in sorted(ALLOWED_ROOT_FILES)]
    for name in ["flat-finder", "scripts", "tests", "docs"]:
        for p in sorted((ROOT / name).rglob("*")):
            if p.is_symlink():
                raise ValueError("Release contains a symlink")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                files.append(p)
    return files


def check():
    profile = read_json(SKILL / "assets/examples/profile.json")
    data = read_json(SKILL / "assets/examples/listings.json")
    assert profile["demo"] is True
    assert all(x.get("demo") is True and x["source_url"].startswith("https://example.org/")
               and not x.get("contact", {}).get("phone") for x in data["listings"]), "Only synthetic example offers can be released"
    provenance = read_json(SKILL / "assets/viewer/vendor/provenance.json")
    for name, digest in provenance["files"].items():
        p = SKILL / "assets/viewer/vendor" / name
        assert hashlib.sha256(p.read_bytes()).hexdigest() == digest, "Vendor digest mismatch"
    for p in source_files():
        if p.suffix not in {".png"}:
            raw = p.read_text(encoding="utf-8")
            # Catch accidental home paths, credentials or a private project dump.
            for token in ["/" + "Users/", "BEGIN " + "PRIVATE KEY", "\"access_" + "token\":", "\"refresh_" + "token\":"]:
                if token in raw:
                    raise ValueError(f"Private/secret marker in {p.relative_to(ROOT)}")
    expected = read_json(SKILL / "MANIFEST.json")
    assert hashes(SKILL) == expected["files"], "Skill manifest is stale; rebuild the release"


def archive(path, pairs):
    manifest = {}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in sorted(pairs):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, body)
            manifest[name] = hashlib.sha256(body).hexdigest()
        z.writestr("RELEASE-MANIFEST.json", json.dumps({"version": VERSION, "files": manifest}, indent=2))


def build():
    (SKILL / "MANIFEST.json").write_text(json.dumps({"version": VERSION, "files": hashes(SKILL)}, indent=2) + "\n")
    check()
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    skill_pairs = [("flat-finder/" + p.relative_to(SKILL).as_posix(), p.read_bytes()) for p in source_files() if p.is_relative_to(SKILL)]
    skill_pairs.append(("LICENSE", (ROOT / "LICENSE").read_bytes()))
    archive(dist / "flat-finder-skill.zip", skill_pairs)
    site = ROOT / "site"
    if site.exists():
        shutil.rmtree(site)
    shutil.copytree(SKILL / "assets/viewer", site)
    # Fixed assessment clock makes the synthetic illustration reproducible. Each
    # record and UI notice explicitly says that it is not a real rental offer.
    with tempfile.TemporaryDirectory() as temp:
        init_workspace(Path(temp), demo=True)
        state = workspace_state(temp, dt.datetime(2026, 11, 21, 13, tzinfo=dt.timezone.utc))
    (site / "demo-state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2))
    (site / "api").mkdir()
    (site / "api/report.md").write_text(markdown_report(state, True))
    (site / "api/export.csv").write_text(csv_report(state))
    (site / "downloads").mkdir()
    shutil.copyfile(dist / "flat-finder-skill.zip", site / "downloads/flat-finder-skill.zip")
    (site / "_headers").write_text("/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://tile.openstreetmap.org; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'\n")
    archive(dist / "flat-finder-demo-site.zip", [(p.relative_to(site).as_posix(), p.read_bytes()) for p in site.rglob("*") if p.is_file()])
    archive(dist / f"flat-finder-codex-{VERSION}.zip", [("flat-finder-codex/" + p.relative_to(ROOT).as_posix(), p.read_bytes()) for p in source_files()])
    sums = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dist.glob("*.zip"))}
    (dist / "SHA256SUMS.json").write_text(json.dumps(sums, indent=2) + "\n")
    print(json.dumps({"version": VERSION, "artifacts": sums, "privacy": "Synthetic fixture only; private workspace not accepted"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check()
        print("Release checks passed: synthetic data, vendor hashes, private-marker scan, skill manifest")
    else:
        build()
