#!/usr/bin/env python3
"""Validate repository structure and public-safety invariants."""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md",
    "LICENSE",
    "skills/project-context/SKILL.md",
    "skills/project-context/agents/openai.yaml",
    "skills/project-context-init/SKILL.md",
    "skills/project-context-init/agents/openai.yaml",
    "skills/project-context-init/scripts/project_context_init.py",
    "skills/project-context-init/references/optional-tools.md",
    "skills/project-context-init/assets/project-context/README.md",
    "skills/project-context-init/assets/project-context/NOW.md",
    "skills/project-context-init/assets/project-context/DECISIONS.md",
    "skills/project-context-init/assets/project-context/LEARNINGS.md",
    "skills/project-context-init/assets/project-context/decisions/TEMPLATE.md",
    "skills/project-context-init/assets/project-context/designs/TEMPLATE.md",
    "skills/project-context-init/assets/project-context/incidents/TEMPLATE.md",
    "skills/project-context-init/assets/project-context/tasks/TEMPLATE.md",
    "tests/test_project_context_init.py",
)

TEXT_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".txt", ""}
PRIVATE_PATTERNS = (
    re.compile(r"/Users/(?!example|your-name|username)[^/\s]+"),
    re.compile(r"sk-(?:proj-|or-v1-)?[A-Za-z0-9_-]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def validate_skill(path: Path) -> list[str]:
    errors: list[str] = []
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        errors.append(f"{path.relative_to(ROOT)}: missing YAML frontmatter")
        return errors
    frontmatter = content.split("---\n", 2)[1]
    for key in ("name:", "description:"):
        if key not in frontmatter:
            errors.append(f"{path.relative_to(ROOT)}: missing {key[:-1]}")
    if "TODO" in content or "Replace with" in content:
        errors.append(f"{path.relative_to(ROOT)}: unfinished scaffold text")
    return errors


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    for skill in ROOT.glob("skills/*/SKILL.md"):
        errors.extend(validate_skill(skill))

    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in {".git", "work", "outputs", "__pycache__"} for part in path.parts):
            continue
        if path == Path(__file__).resolve():
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name != "LICENSE":
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for pattern in PRIVATE_PATTERNS:
            if pattern.search(content):
                errors.append(f"{path.relative_to(ROOT)}: possible private path or credential")

    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8") if (ROOT / "LICENSE").exists() else ""
    if "MIT License" not in license_text or "Permission is hereby granted" not in license_text:
        errors.append("LICENSE is not the standard MIT grant")

    if errors:
        print("Repository validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Repository validation passed ({len(REQUIRED)} required files checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
