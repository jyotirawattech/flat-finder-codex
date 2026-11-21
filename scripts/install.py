#!/usr/bin/env python3
"""Install the bundled skill locally; never overwrite a different installation."""
import hashlib
import json
import os
import argparse
import datetime as dt
import fcntl
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "flat-finder"


def hashes(folder):
    result = {}
    for p in folder.rglob("*"):
        if p.is_symlink():
            raise ValueError("Symlinks are not permitted in the skill")
        if p.is_file() and p.name != "MANIFEST.json" and "__pycache__" not in p.parts and p.suffix != ".pyc":
            result[p.relative_to(folder).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--update', action='store_true', help='Update an unmodified installation, retaining a backup')
    args = parser.parse_args()
    expected = json.loads((SOURCE / "MANIFEST.json").read_text())
    if hashes(SOURCE) != expected["files"]:
        raise ValueError("Package integrity does not match MANIFEST.json")
    root = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills"
    root.mkdir(parents=True, exist_ok=True)
    destination = root / "flat-finder"
    if destination.is_symlink():
        raise ValueError("Existing destination is a symlink; left unchanged")
    if destination.exists():
        if hashes(destination) == expected["files"]:
            print(f"Already installed and verified: {destination}")
            return
        if not args.update:
            raise ValueError("A different flat-finder skill exists; left unchanged. Review it before using --update.")
        installed = json.loads((destination / 'MANIFEST.json').read_text())
        if hashes(destination) != installed['files']:
            raise ValueError('Installed skill has local changes; left unchanged. Reconcile those changes first.')
    with tempfile.TemporaryDirectory(prefix=".flat-finder-install-", dir=root) as temp:
        staged = Path(temp) / "flat-finder"
        shutil.copytree(SOURCE, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if hashes(staged) != expected["files"]:
            raise ValueError("Staged copy failed verification")
        lock_fd = os.open(root.parent / '.flat-finder-install.lock', os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(lock_fd, 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            backup = None
            if destination.exists():
                current = json.loads((destination / 'MANIFEST.json').read_text())
                if not args.update or hashes(destination) != current['files']:
                    raise ValueError('Installation changed while staging; left unchanged')
                backups = root.parent / 'skill-backups/flat-finder'
                backups.mkdir(parents=True, exist_ok=True)
                backup = backups / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                destination.rename(backup)
            try:
                staged.rename(destination)
            except OSError:
                if backup and not destination.exists():
                    backup.rename(destination)
                raise
            if backup:
                print(f'Previous verified installation backed up: {backup}')
    print(f"Installed and verified: {destination}\nUse $flat-finder in Codex. Open a new chat if discovery has not refreshed.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as e:
        raise SystemExit(str(e))
