#!/usr/bin/env python3
"""Check for a newer Project Context release and plan a safe upgrade.

An installed scaffold is usually a mix of two things: files that came from a
release untouched, and files the project has since adapted. Overwriting the
second kind silently is the failure this script exists to prevent, so it
compares three sides — the installed file, the release it came from, and the
release being offered — and only proposes a write where the installed file is
still identical to the release it came from.

Commands:
  check   report installed version against the latest published release
  plan    classify every scaffold file: create, update, conflict, or same
  apply   perform only the writes that plan classified as safe

Never touches NOW.md, DECISIONS.md, or LEARNINGS.md: those belong to the
project, not to the scaffold.
"""

from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request

DEFAULT_REPO = os.environ.get("PROJECT_CONTEXT_REPO", "monomind-ai-lab/project-context")
CONTEXT_DIR = "project-context"
METADATA = ".project-context.json"
USER_OWNED = {"NOW.md", "DECISIONS.md", "LEARNINGS.md"}
SKILL_NAMES = ("project-context", "project-context-init", "project-context-update")
DOC_SOURCE = "skills/project-context-init/assets/project-context"
SKIP_NAMES = {".DS_Store"}
SKIP_PARTS = {"__pycache__"}


def api(path: str, repo: str) -> dict:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/{path}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "project-context-update"},
    )
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return {}


def parse_version(value: str) -> tuple:
    parts: list[int] = []
    for chunk in re.split(r"[.\-+]", str(value).strip().lstrip("vV")):
        if not chunk.isdigit():
            break
        parts.append(int(chunk))
    return tuple(parts)


def metadata_value(target: Path, key: str, default: str = "") -> str:
    path = target / CONTEXT_DIR / METADATA
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get(key, default))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        return default


def installed_version(target: Path) -> str:
    return metadata_value(target, "template_version")


def installed_profile(target: Path) -> str:
    return metadata_value(target, "profile", "core")


def download_tree(repo: str, ref: str, destination: Path) -> Path | None:
    """Extract a tag's tarball and return its root directory."""
    url = f"https://api.github.com/repos/{repo}/tarball/{ref}"
    request = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json", "User-Agent": "project-context-update"}
    )
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
    except (urllib.error.URLError, OSError):
        return None
    destination.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
            members = [m for m in archive.getmembers() if not m.name.startswith("/") and ".." not in Path(m.name).parts]
            try:
                archive.extractall(destination, members=members, filter="data")
            except TypeError:  # Python < 3.12 has no extraction filters
                archive.extractall(destination, members=members)
    except (tarfile.TarError, OSError):
        return None
    roots = [child for child in destination.iterdir() if child.is_dir()]
    return roots[0] if len(roots) == 1 else destination


def scaffold_files(root: Path, profile: str = "core") -> dict[str, Path]:
    """Map install-relative path -> file in the release tree.

    A core install stays core: the full profile's evidence folders are only
    offered to an install that already has them.
    """
    mapping: dict[str, Path] = {}
    for name in SKILL_NAMES:
        source = root / "skills" / name
        if not source.is_dir():
            continue
        for path in sorted(source.rglob("*")):
            if not path.is_file() or path.name in SKIP_NAMES:
                continue
            if SKIP_PARTS.intersection(path.parts):
                continue
            mapping[str(Path(".agents/skills") / name / path.relative_to(source))] = path
    docs = root / DOC_SOURCE
    if docs.is_dir():
        for path in sorted(docs.rglob("*")):
            if not path.is_file() or path.name in SKIP_NAMES:
                continue
            if SKIP_PARTS.intersection(path.parts):
                continue
            relative = path.relative_to(docs)
            if relative.name in USER_OWNED:
                continue
            if profile != "full" and relative.parent != Path("."):
                continue
            mapping[str(Path(CONTEXT_DIR) / relative)] = path
    return mapping


def read(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


def classify(target: Path, new_root: Path, old_root: Path | None, profile: str) -> list[dict]:
    """Three-way comparison of installed files against two release trees."""
    offered = scaffold_files(new_root, profile)
    baseline = scaffold_files(old_root, profile) if old_root else {}
    rows: list[dict] = []
    for relative, source in sorted(offered.items()):
        local_path = target / relative
        new_bytes = read(source)
        if new_bytes is None:
            continue
        if not local_path.exists():
            rows.append({"path": relative, "state": "create"})
            continue
        local_bytes = read(local_path)
        if local_bytes == new_bytes:
            rows.append({"path": relative, "state": "same"})
            continue
        base_source = baseline.get(relative)
        base_bytes = read(base_source) if base_source else None
        if base_bytes is not None and base_bytes == local_bytes:
            rows.append({"path": relative, "state": "update"})
        elif base_bytes is None:
            rows.append({"path": relative, "state": "review", "why": "no baseline release to compare against"})
        else:
            rows.append({"path": relative, "state": "conflict", "why": "changed locally since the installed release"})
    return rows


def summarize(rows: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["state"]] = counts.get(row["state"], 0) + 1
    return counts


def resolve_release(repo: str, tag: str | None) -> dict:
    if tag:
        payload = api(f"releases/tags/{tag}", repo)
    else:
        payload = api("releases/latest", repo)
    if not payload.get("tag_name"):
        return {}
    return {
        "tag": str(payload["tag_name"]),
        "name": str(payload.get("name") or payload["tag_name"]),
        "url": str(payload.get("html_url") or ""),
        "published": str(payload.get("published_at") or "")[:10],
        "notes": str(payload.get("body") or ""),
    }


def command_check(args) -> int:
    target = args.target.resolve()
    installed = installed_version(target)
    release = resolve_release(args.repo, args.tag)
    result = {
        "target": str(target),
        "installed": installed or "unknown",
        "repo": args.repo,
        "latest": release.get("tag", ""),
        "published": release.get("published", ""),
        "url": release.get("url", ""),
    }
    if not release:
        result["status"] = "unavailable"
    elif not installed:
        result["status"] = "unknown-install"
    elif parse_version(release["tag"]) > parse_version(installed):
        result["status"] = "update-available"
    else:
        result["status"] = "current"
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def build_plan(args) -> dict:
    target = args.target.resolve()
    if not (target / CONTEXT_DIR).is_dir():
        return {"error": f"no {CONTEXT_DIR}/ in {target}"}
    installed = installed_version(target)
    release = resolve_release(args.repo, args.tag)
    if not release:
        return {"error": "no published release found"}
    workspace = Path(tempfile.mkdtemp(prefix="project-context-update-"))
    try:
        new_root = download_tree(args.repo, release["tag"], workspace / "new")
        if new_root is None:
            return {"error": f"could not download {release['tag']}"}
        old_root = None
        if installed:
            for candidate in (f"v{installed}", installed):
                old_root = download_tree(args.repo, candidate, workspace / "old")
                if old_root is not None:
                    break
        profile = installed_profile(target)
        rows = classify(target, new_root, old_root, profile)
        plan = {
            "target": str(target),
            "repo": args.repo,
            "installed": installed or "unknown",
            "profile": profile,
            "release": release["tag"],
            "published": release.get("published", ""),
            "url": release.get("url", ""),
            "baseline": bool(old_root),
            "summary": summarize(rows),
            "files": rows,
        }
        if args.apply:
            plan["applied"] = apply_plan(target, new_root, rows, profile)
            metadata = target / CONTEXT_DIR / METADATA
            try:
                data = json.loads(metadata.read_text(encoding="utf-8"))
                data["template_version"] = release["tag"].lstrip("vV")
                metadata.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                plan["template_version"] = data["template_version"]
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                plan["template_version"] = "unchanged"
        return plan
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def apply_plan(target: Path, new_root: Path, rows: list[dict], profile: str) -> list[str]:
    offered = scaffold_files(new_root, profile)
    written: list[str] = []
    for row in rows:
        if row["state"] not in {"create", "update"}:
            continue
        source = offered.get(row["path"])
        if source is None:
            continue
        destination = target / row["path"]
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            written.append(row["path"])
        except OSError:
            continue
    return written


def command_plan(args) -> int:
    plan = build_plan(args)
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 1 if plan.get("error") else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, helptext in (
        ("check", "compare the installed version against the latest release"),
        ("plan", "classify every scaffold file without writing"),
        ("apply", "perform only the writes plan classified as safe"),
    ):
        subparser = subparsers.add_parser(name, help=helptext)
        subparser.add_argument("--target", default=".", type=Path)
        subparser.add_argument("--repo", default=DEFAULT_REPO)
        subparser.add_argument("--tag", default=None, help="a specific release instead of the latest")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.apply = args.command == "apply"
    if args.command == "check":
        return command_check(args)
    return command_plan(args)


if __name__ == "__main__":
    sys.exit(main())
