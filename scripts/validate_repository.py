#!/usr/bin/env python3
"""Validate repository structure and public-safety invariants."""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "docs/context-hub-architecture.md",
    "README.md",
    "LICENSE",
    "VERSION",
    "pyproject.toml",
    "src/project_context_cli/__init__.py",
    "assets/project-context-cover.jpg",
    "assets/project-context-tools.jpg",
    "docs/project-context-complete-guide.html",
    ".github/workflows/pages.yml",
    "examples/sample-project-context/README.md",
    "examples/sample-project-context/NOW.md",
    "examples/sample-project-context/DECISIONS.md",
    "examples/sample-project-context/LEARNINGS.md",
    "scripts/install.py",
    "prompts/install-project-context.md",
    "prompts/maintain-project-context.md",
    "prompts/create-context-hub.md",
    "scripts/build_site.py",
    "scripts/sync.sh",
    "web/layout/base.html",
    "web/assets/site.css",
    "web/assets/site.js",
    "web/static/favicon.svg",
    "web/static/clarity-bg.jpg",
    "web/content/index/meta.json",
    "web/content/index/page.html",
    "web/content/index/page.css",
    "web/content/index/i18n.js",
    "web/content/use-cases/meta.json",
    "web/content/use-cases/page.html",
    "web/content/use-cases/page.css",
    "web/content/use-cases/i18n.js",
    "web/content/use-cases/page.js",
    "skills/project-context/SKILL.md",
    "skills/project-context/agents/openai.yaml",
    "skills/project-context/scripts/context_triggers.py",
    "skills/project-context/scripts/context_index.py",
    "skills/project-context/scripts/context_doctor.py",
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
    "skills/context-hub/SKILL.md",
    "skills/context-hub/agents/openai.yaml",
    "skills/context-hub/scripts/context_hub.py",
    "skills/context-hub/assets/context-hub/README.md",
    "skills/context-hub/assets/context-hub/SUMMARY.md",
    "skills/context-hub/assets/context-hub/OVERVIEW.md",
    "skills/context-hub/assets/context-hub/.context-hub.json",
    "skills/context-hub/assets/context-hub/.context-hub/local.example.yaml",
    "skills/context-hub/assets/context-hub/.gitignore",
    "skills/context-hub/assets/context-hub/.graphifyignore",
    "skills/context-hub/assets/context-hub/actors/actor-context-hub.md",
    "skills/context-hub/assets/context-hub/schemas/common.schema.json",
    "skills/context-hub/assets/context-hub/schemas/project.schema.json",
    "skills/context-hub/assets/context-hub/schemas/actor.schema.json",
    "skills/context-hub/assets/context-hub/schemas/entity.schema.json",
    "skills/context-hub/assets/context-hub/schemas/episode.schema.json",
    "skills/context-hub/assets/context-hub/schemas/relationship.schema.json",
    "skills/context-hub/assets/context-hub/schemas/insight.schema.json",
    "skills/context-hub/assets/context-hub/templates/ACTOR.md",
    "skills/context-hub/assets/context-hub/templates/ENTITY.md",
    "skills/context-hub/assets/context-hub/templates/EPISODE.md",
    "skills/context-hub/assets/context-hub/templates/RELATIONSHIP.md",
    "skills/context-hub/assets/context-hub/templates/INSIGHT.md",
    "skills/context-hub/assets/context-hub/templates/project/PROJECT.md",
    "skills/context-hub/assets/context-hub/templates/project/SUMMARY.md",
    "skills/context-hub/assets/context-hub/templates/project/OVERVIEW.md",
    "skills/context-hub/assets/context-hub/templates/project/NOW.md",
    "skills/context-hub/assets/context-hub/templates/project/DECISIONS.md",
    "skills/context-hub/assets/context-hub/templates/project/LEARNINGS.md",
    "skills/context-hub/assets/context-hub/.obsidian/app.json",
    "skills/context-hub/assets/context-hub/.obsidian/core-plugins.json",
    "skills/context-hub/assets/context-hub/.obsidian/templates.json",
    "tests/test_project_context_init.py",
    "tests/test_context_hub.py",
)

TEXT_SUFFIXES = {
    ".html",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
    "",
}
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
    for required_clause in (
        "MIT + Commons Clause License Condition v1.0",
        "Permission is hereby granted",
        "Commons Clause Restriction",
        "do not sell, sublicense, or redistribute the components themselves",
    ):
        if required_clause not in license_text:
            errors.append("LICENSE is not the MIT + Commons Clause grant")
            break

    jpeg_assets = (
        (ROOT / "assets/project-context-cover.jpg", (1200, 675), "cover"),
        (ROOT / "assets/project-context-tools.jpg", (1200, 675), "optional-tools"),
    )
    for path, dimensions, label in jpeg_assets:
        if path.is_file():
            errors.extend(validate_jpeg(path, dimensions, label))

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else ""
    # The distribution version and embedded project scaffold version have
    # separate lifecycles. The initializer and doctor must still agree with one
    # another so the doctor does not report a phantom scaffold upgrade.
    versioned = {
        "initializer": ROOT / "skills/project-context-init/scripts/project_context_init.py",
        "doctor": ROOT / "skills/project-context/scripts/context_doctor.py",
    }
    template_versions: dict[str, str] = {}
    for label, source in versioned.items():
        content = source.read_text(encoding="utf-8") if source.is_file() else ""
        match = re.search(r'^TEMPLATE_VERSION = "([^"]+)"$', content, re.MULTILINE)
        if not match:
            errors.append(f"{label} does not declare TEMPLATE_VERSION")
        else:
            template_versions[label] = match.group(1)
    if len(set(template_versions.values())) > 1:
        errors.append("initializer and doctor template versions do not match")

    # Also check pyproject.toml has the same version
    pyproject_path = ROOT / "pyproject.toml"
    if pyproject_path.is_file():
        pyproject_content = pyproject_path.read_text(encoding="utf-8")
        if version and f'version = "{version}"' not in pyproject_content:
            errors.append(f"VERSION and pyproject.toml version do not match")

    readme = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").exists() else ""
    for expected in (
        "Shared project context that outlives any one person, agent, or chat",
        "context pipeline right into a repository or project",
        "Choose Where Context Lives",
        "no database, vector store, or server is required",
        "Linked",
        "prompts/create-context-hub.md",
        "assets/project-context-cover.jpg",
        "assets/project-context-tools.jpg",
        "https://monomind-ai-lab.github.io/project-context/project-context-complete-guide.html",
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

    guide = ROOT / "docs/project-context-complete-guide.html"
    if guide.is_file():
        guide_text = guide.read_text(encoding="utf-8")
        for expected in ("<!doctype html>", "<title>Project Context · How It Works</title>"):
            if expected not in guide_text:
                errors.append(f"interactive guide missing expected content: {expected}")
        if "file://" in guide_text:
            errors.append("interactive guide contains a local file URL")
        responsive_marker = "/* ── Responsive deck hardening"
        guide_layer_marker = "/* ═══════════════════════════════════════════════════════════════════\n   Guide layer"
        if responsive_marker not in guide_text:
            errors.append("interactive guide is missing responsive deck hardening")
        elif guide_layer_marker in guide_text and guide_text.rfind(responsive_marker) < guide_text.find(guide_layer_marker):
            errors.append("interactive guide responsive overrides must follow the guide layer")
        for expected in (
            "viewport-fit=cover",
            "overflow-y: auto",
            "min-height: 100svh",
            ".wf-track { grid-template-columns: 1fr;",
            "table-layout: fixed",
            "function viewportWidth()",
            "function resetVerticalScroll()",
        ):
            if expected not in guide_text:
                errors.append(f"interactive guide missing responsive behavior: {expected}")

    pages_workflow = ROOT / ".github/workflows/pages.yml"
    if pages_workflow.is_file():
        workflow_text = pages_workflow.read_text(encoding="utf-8")
        for expected in (
            "actions/configure-pages@v5",
            "actions/upload-pages-artifact@v3",
            "actions/deploy-pages@v4",
            "path: ./docs",
        ):
            if expected not in workflow_text:
                errors.append(f"Pages workflow missing expected configuration: {expected}")

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
        "skills/context-hub/SKILL.md": (
            "description: \"Use when",
            "No database, vector store, or server is required",
        ),
    }
    for relative, expected_values in trigger_expectations.items():
        content = (ROOT / relative).read_text(encoding="utf-8") if (ROOT / relative).exists() else ""
        for expected in expected_values:
            if expected not in content:
                errors.append(f"{relative}: missing discovery trigger: {expected}")
    for relative in (
        "skills/project-context/agents/openai.yaml",
        "skills/project-context-init/agents/openai.yaml",
        "skills/context-hub/agents/openai.yaml",
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
