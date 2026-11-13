#!/usr/bin/env python3
"""Remove one owner's devserve previews, or list stale try-it previews read-only."""

import argparse
import json
from pathlib import Path
import subprocess
import sys


def previews():
    result = subprocess.run(["devserve", "ls", "--json"], check=True,
                            capture_output=True, text=True, timeout=30)
    rows = json.loads(result.stdout)["previews"]
    if not isinstance(rows, list) or any(
        not isinstance(row, dict)
        or not isinstance(row.get("owner"), str) or not row["owner"]
        or not isinstance(row.get("unit"), str)
        or not row["unit"].startswith("devserve-")
        or not row["unit"].endswith(".service")
        for row in rows
    ):
        raise ValueError("invalid devserve preview listing")
    return rows


def foreman(*args, cwd=None):
    result = subprocess.run(["foreman", *args], cwd=cwd, check=True,
                            capture_output=True, text=True, timeout=30)
    data = json.loads(result.stdout)
    if not isinstance(data, dict) or "warning" in data or "error" in data:
        raise ValueError(f"foreman read failed: {result.stdout.strip()}")
    return data


def stale_reason(ticket):
    # doc path resolves the registered ticket prefix, not the preview's code repo.
    report = Path(foreman("doc", "path", "report", ticket, "--json")["path"])
    if not report.is_absolute() or report.parts[-3:] != ("builds", ticket, "report.md"):
        raise ValueError("invalid ticket report path")
    repo = report.parents[2]
    local = foreman("show", ticket, "--json", cwd=repo)
    if local.get("id") != ticket or "status" not in local:
        raise ValueError("invalid ticket status")
    if local["status"] == "closed":
        return "ticket closed"
    overlay = foreman("show", ticket, "--overlay", "--json", cwd=repo)
    if (overlay.get("id") != ticket or not isinstance(overlay.get("stage"), str)
            or not overlay["stage"]):
        raise ValueError("invalid board stage")
    stage = overlay["stage"]
    if stage in {"abandoned", "done", "pr_open", "merged"}:
        return f"board {stage}"
    return None


def list_stale(rows):
    failed = False
    reasons = {}
    for preview in rows:
        owner = preview["owner"]
        if not owner.startswith("try-it-"):
            continue
        ticket = owner[len("try-it-"):]
        try:
            if ticket not in reasons:
                reasons[ticket] = stale_reason(ticket)
            if reasons[ticket]:
                print(f'{preview["unit"]}\t{owner}\t{ticket}\t{reasons[ticket]}')
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
            print(f"Stale preview status unknown for {owner}: {error}", file=sys.stderr)
            failed = True
    return int(failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("owner", nargs="?", help="Exact build or try-it-<ticket> owner")
    parser.add_argument("--list-stale", action="store_true", help="Read-only stale try-it scan")
    args = parser.parse_args()
    if args.list_stale == (args.owner is not None):
        parser.error("provide an owner or --list-stale, not both")
    if args.owner is not None and not args.owner.strip():
        parser.error("owner must not be empty")
    try:
        if args.list_stale:
            return list_stale(previews())
        for preview in previews():
            if preview["owner"] == args.owner:
                subprocess.run(["devserve", "down", preview["unit"], "--drop-db"],
                               check=True, timeout=180)
        if any(preview["owner"] == args.owner for preview in previews()):
            raise ValueError(f"previews still registered for {args.owner}")
        print(f"Cleaned previews for {args.owner}")
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"Preview cleanup failed; keep the session window: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
