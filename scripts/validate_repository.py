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
    "VERSION",
    "assets/project-context-cover.jpg",
    "assets/project-context-tools.jpg",
    "examples/sample-project-context/README.md",
    "examples/sample-project-context/NOW.md",
    "examples/sample-project-context/DECISIONS.md",
    "examples/sample-project-context/LEARNINGS.md",
    "scripts/install.py",
    "prompts/install-project-context.md",
    "prompts/maintain-project-context.md",
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


def validate_jpeg(path: Path, expected_dimensions: tuple[int, int], label: str) -> list[str]:
    errors: list[str] = []
    data = path.read_bytes()
    if not data.startswith(b"\xff\xd8"):
        return [f"{label} asset is not a valid JPEG"]
    dimensions = None
    forbidden_markers: list[int] = []
    offset = 2
    while offset + 4 <= len(data) and data[offset] == 0xFF:
        marker = data[offset + 1]
        if marker in {0xD9, 0xDA}:
            break
        length = int.from_bytes(data[offset + 2 : offset + 4], "big")
        if length < 2 or offset + 2 + length > len(data):
            errors.append(f"{label} asset has a malformed JPEG segment")
            break
        if marker in {0xE1, 0xED, 0xFE}:
            forbidden_markers.append(marker)
        if marker in {0xC0, 0xC1, 0xC2} and length >= 7:
            dimensions = (
                int.from_bytes(data[offset + 7 : offset + 9], "big"),
                int.from_bytes(data[offset + 5 : offset + 7], "big"),
            )
        offset += 2 + length
    if dimensions != expected_dimensions:
        errors.append(
            f"{label} asset must remain {expected_dimensions[0]} x {expected_dimensions[1]}"
        )
    if forbidden_markers:
        errors.append(f"{label} asset contains removable author or comment metadata")
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

    jpeg_assets = (
        (ROOT / "assets/project-context-cover.jpg", (1200, 675), "cover"),
        (ROOT / "assets/project-context-tools.jpg", (1920, 1080), "optional-tools"),
    )
    for path, dimensions, label in jpeg_assets:
        if path.is_file():
            errors.extend(validate_jpeg(path, dimensions, label))

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else ""
    initializer = ROOT / "skills/project-context-init/scripts/project_context_init.py"
    if version and f'TEMPLATE_VERSION = "{version}"' not in initializer.read_text(encoding="utf-8"):
        errors.append("VERSION and initializer template version do not match")

    readme = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").exists() else ""
    for expected in (
        "Shared project context that outlives any one person, agent, or chat",
        "simple way to build a context pipeline right into a",
        "assets/project-context-cover.jpg",
        "assets/project-context-tools.jpg",
        "Attribution and independence",
        "affiliated with, sponsored by, or endorsed by",
        "prompts/install-project-context.md",
        "agent-operated and human-readable",
        "not expected to invoke skills or run Python commands themselves",
        "How agents find the instructions",
        "automatically installs or configures that selected tool",
        "the agent guides the user step by step",
    ):
        if expected not in readme:
            errors.append(f"README missing expected positioning: {expected}")

    init_skill_path = ROOT / "skills/project-context-init/SKILL.md"
    init_skill = init_skill_path.read_text(encoding="utf-8") if init_skill_path.exists() else ""
    for expected in (
        "Is this a brand-new repository?",
        "What will this repository primarily hold or support?",
        "Eliminate add-ons that do not help",
        "If Python is unavailable",
        "Guide secure authentication step by step",
    ):
        if expected not in init_skill:
            errors.append(f"initializer skill missing onboarding behavior: {expected}")

    trigger_expectations = {
        "skills/project-context/SKILL.md": ("description: \"Use when", "contains project-context/"),
        "skills/project-context-init/SKILL.md": ("description: Use when", "install, initialize, adopt"),
    }
    for relative, expected_values in trigger_expectations.items():
        content = (ROOT / relative).read_text(encoding="utf-8") if (ROOT / relative).exists() else ""
        for expected in expected_values:
            if expected not in content:
                errors.append(f"{relative}: missing discovery trigger: {expected}")
    for relative in (
        "skills/project-context/agents/openai.yaml",
        "skills/project-context-init/agents/openai.yaml",
    ):
        content = (ROOT / relative).read_text(encoding="utf-8") if (ROOT / relative).exists() else ""
        if "allow_implicit_invocation: true" not in content:
            errors.append(f"{relative}: implicit skill discovery is not enabled")

    if errors:
        print("Repository validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Repository validation passed ({len(REQUIRED)} required files checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
