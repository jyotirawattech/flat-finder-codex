#!/usr/bin/env python3
"""Deterministic companion to the Flat Finder Codex skill; never sends messages."""
import argparse
import contextlib
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import sys

from ff_core import (ValidationError, csv_report, markdown_report, merge_listings,
                     read_json, search_plan, validate_profile, workspace_state, write_json)

ASSETS = Path(__file__).resolve().parents[1] / "assets"


@contextlib.contextmanager
def workspace_lock(workspace):
    workspace.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(workspace / ".write.lock", os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def init_workspace(workspace, profile=None, demo=False):
    with workspace_lock(workspace):
        if (workspace / "profile.json").exists() or (workspace / "listings.json").exists():
            raise ValidationError("Workspace already exists; initialization will not overwrite it")
        p = read_json(ASSETS / "examples/profile.json") if demo else read_json(profile)
        p = validate_profile(p)
        data = read_json(ASSETS / "examples/listings.json") if demo else {"listings": [], "events": [], "access": []}
        write_json(workspace / "profile.json", p)
        write_json(workspace / "listings.json", data)
    return workspace_state(workspace)


def import_data(workspace, payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("listings"), list):
        raise ValidationError("Import requires a listings array")
    with workspace_lock(workspace):
        old = read_json(workspace / "listings.json")
        data = {"listings": merge_listings(old["listings"], payload["listings"]),
                "events": (payload.get("events", []) + old.get("events", []))[:100],
                "access": payload.get("access", old.get("access", []))}
        # Validate the complete candidate before atomic replacement. Invalid input
        # must not destroy a user's last usable dataset.
        import tempfile
        with tempfile.TemporaryDirectory() as candidate:
            write_json(Path(candidate) / "profile.json", read_json(workspace / "profile.json"))
            write_json(Path(candidate) / "listings.json", data)
            workspace_state(candidate)
        write_json(workspace / "listings.json", data)
    return workspace_state(workspace)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "import", "report", "plan", "serve", "state"])
    parser.add_argument("--workspace", type=Path, help="Private data directory, outside the shareable skill")
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--demo", action="store_true", help="Use only bundled synthetic data")
    parser.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown")
    parser.add_argument("--include-held", action="store_true")
    parser.add_argument("--port", type=int, default=43126)
    args = parser.parse_args()
    try:
        if args.command == "serve" and args.demo:
            from ff_server import serve
            return serve(None, args.port, demo=True)
        if not args.workspace:
            parser.error("--workspace is required except for serve --demo")
        if args.command == "init":
            if not args.demo and not args.profile:
                parser.error("init needs --profile or --demo")
            state = init_workspace(args.workspace, args.profile, args.demo)
        elif args.command == "import":
            if not args.input:
                parser.error("import needs --input")
            state = import_data(args.workspace, read_json(args.input))
        elif args.command == "serve":
            from ff_server import serve
            return serve(args.workspace, args.port)
        else:
            state = workspace_state(args.workspace)
        if args.command == "plan":
            print(json.dumps(search_plan(state), indent=2, ensure_ascii=False))
        elif args.command == "report" and args.format == "csv":
            print(csv_report(state), end="")
        elif args.command == "state" or args.format == "json":
            print(json.dumps(state, indent=2, ensure_ascii=False))
        else:
            print(markdown_report(state, args.include_held))
    except (ValidationError, ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        print(f"Flat Finder: input or workspace error ({type(exc).__name__}). Check the data contract and local files.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
