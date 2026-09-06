#!/usr/bin/env python3
"""Install Project Context skills and initialize a target repository."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
INITIALIZER = ROOT / "skills" / "project-context-init" / "scripts" / "project_context_init.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default=".", type=Path)
    parser.add_argument("--profile", choices=("core", "full"), default="core")
    parser.add_argument(
        "--repo-type",
        choices=("auto", "code", "document", "research", "writing", "mixed", "general"),
        default="auto",
    )
    parser.add_argument(
        "--repository-stage",
        choices=("brand-new", "existing"),
        default="existing",
    )
    parser.add_argument(
        "--placement",
        choices=("in-repo", "local-only", "private-sibling"),
        default="in-repo",
        help=(
            "where project-context/ sits relative to version control; the two "
            "non-tracked choices add /project-context/ to .gitignore"
        ),
    )
    parser.add_argument(
        "--install-hooks",
        action="store_true",
        help="also wire the session trigger hooks into .claude/settings.json",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    command = [
        sys.executable,
        str(INITIALIZER),
        "init",
        "--target",
        str(args.target),
        "--profile",
        args.profile,
        "--repo-type",
        args.repo_type,
        "--repository-stage",
        args.repository_stage,
        "--placement",
        args.placement,
        "--install-skills",
        *(["--install-hooks"] if args.install_hooks else []),
        "--apply" if args.apply else "--dry-run",
    ]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
