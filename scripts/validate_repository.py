#!/usr/bin/env python3
"""Validate repository structure and public-safety invariants."""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "docs/archive/context-hub-architecture.md",
    "README.md",
    "LICENSE",
    "VERSION",
    "pyproject.toml",
    "src/project_context_cli/__init__.py",
    "assets/project-context-cover.jpg",
    "assets/project-context-tools.jpg",
    "docs/guide-builders.html",
    "docs/guide-owners.html",
    # A redirect stub, not a guide. GitHub Pages served the old complete
    # guide at this path for months and has no redirect rules, so the hop
    # lives in the document. Required here so a tidy-up does not reinstate
    # the 404 it exists to prevent.
    "docs/project-context-complete-guide.html",
    ".github/workflows/pages.yml",
    "examples/sample-project-context/README.md",
    "examples/sample-project-context/NOW.md",
    "examples/sample-project-context/DECISIONS.md",
    "examples/sample-project-context/LEARNINGS.md",
    "scripts/install.py",
    "prompts/install-project-context.md",
    "prompts/maintain-project-context.md",
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
    "web/content/guide/meta.json",
    "web/content/guide/page.html",
    "web/content/guide/page.css",
    "web/content/guide/i18n.js",
    "web/content/project-hub/meta.json",
    "web/content/project-hub/page.html",
    "web/content/project-hub/page.css",
    "web/content/project-hub/i18n.js",
    "web/content/docs-builders/meta.json",
    "web/content/docs-builders/page.html",
    "web/content/docs-builders/page.css",
    "web/content/docs-builders/i18n.js",
    "web/content/hub-owners-guide/meta.json",
    "web/content/hub-owners-guide/page.html",
    "web/content/hub-owners-guide/page.css",
    "web/content/hub-owners-guide/i18n.js",
    "web/nav.json",
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
    "tests/test_project_context_init.py",
    "tests/test_record_model.py",
    # The contract for anyone working on this product, and its host pointer.
    # Both, because the rule the installer enforces in a consuming repository
    # is one this repository should not be exempt from: a Claude session that
    # opens a folder with no CLAUDE.md gets no contract at all.
    "AGENTS.md",
    "CLAUDE.md",
    # Retrieval, conformance, and review (slice 7).
    "skills/project-context/scripts/context_packet.py",
    "skills/project-context/scripts/context_review.py",
    "skills/project-context/scripts/context_capture.py",
    "skills/project-context-init/assets/project-context/PLAN.md",
    "skills/project-context-init/assets/project-context/QUESTIONS.md",
    "skills/project-context-init/assets/project-context/questions/TEMPLATE.md",
    "skills/project-context-init/assets/project-context/inbox/TEMPLATE.md",
    "tests/test_context_doctor.py",
    "tests/test_context_index.py",
    "tests/test_context_triggers.py",
    "tests/test_context_packet.py",
    "tests/test_context_review.py",
    "tests/test_context_capture.py",
)

# Host pointer files. A pointer that restates a rule from `AGENTS.md` is how the
# two drift apart, so each one present is held to its shape: it must name the
# contract and stay short enough that it cannot have become a second copy.
POINTER_FILES = ("CLAUDE.md",)
POINTER_MAX_LINES = 40

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
# Directories that are on disk but not in the repository. A local virtualenv is
# full of absolute paths by construction, and reporting them as leaked
# credentials trains a contributor to ignore this validator — which is the one
# outcome a safety check cannot afford.
SKIP_PARTS = {
    ".git", "work", "outputs", "__pycache__",
    ".venv", "venv", "node_modules", ".pytest_cache", ".mypy_cache",
}
PRIVATE_PATTERNS = (
    re.compile(r"/Users/(?!example|your-name|username)[^/\s]+"),
    re.compile(r"sk-(?:proj-|or-v1-)?[A-Za-z0-9_-]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def validate_pointers() -> list[str]:
    errors: list[str] = []
    for relative in POINTER_FILES:
        path = ROOT / relative
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if "AGENTS.md" not in "\n".join(lines):
            errors.append(f"{relative}: a host pointer must name AGENTS.md")
        if len(lines) > POINTER_MAX_LINES:
            errors.append(
                f"{relative}: {len(lines)} lines; a pointer over {POINTER_MAX_LINES} is a second copy "
                "of the contract, which is the bug two layers exist to prevent"
            )
    return errors


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
    errors.extend(validate_pointers())

    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
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
    # One version number. TEMPLATE_VERSION and SCAFFOLD_VERSION are retired:
    # both scripts read VERSION, so the only thing left to hold is that neither
    # has quietly grown a constant of its own again.
    versioned = {
        "initializer": ROOT / "skills/project-context-init/scripts/project_context_init.py",
        "doctor": ROOT / "skills/project-context/scripts/context_doctor.py",
    }
    for label, source in versioned.items():
        content = source.read_text(encoding="utf-8") if source.is_file() else ""
        for retired in ("TEMPLATE_VERSION", "SCAFFOLD_VERSION"):
            if re.search(rf"^{retired} = ", content, re.MULTILINE):
                errors.append(f"{label} declares {retired}; there is one version, read from VERSION")
        if "def package_version(" not in content:
            errors.append(f"{label} does not read the package version from VERSION")
        if 'SCHEMA = "project-context/1"' not in content:
            errors.append(f"{label} does not declare the project-context/1 record schema")

    # Context Hub is superseded, not migrated. The one part of it that ships
    # forward is the doctor's recognition of a half-upgraded install, so that a
    # repository still carrying the old marker is reported rather than
    # certified healthy.
    doctor_text = (ROOT / "skills/project-context/scripts/context_doctor.py").read_text(encoding="utf-8")
    for expected in (
        'LEGACY_SCHEMA = "context-hub/1"',
        'LEGACY_START = "<!-- context-hub:start -->"',
    ):
        if expected not in doctor_text:
            errors.append(f"doctor no longer diagnoses a superseded Context Hub install: {expected}")
    if (ROOT / "skills/context-hub").exists():
        errors.append("skills/context-hub is superseded and must not be present")

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
        "Where Context Lives",
        "no database, vector store, or server is required",
        "One record model",
        "Context Hub is superseded",
        "assets/project-context-cover.jpg",
        "assets/project-context-tools.jpg",
        "https://projectcontext.monomind.one/guide/builders/",
        "https://projectcontext.monomind.one/guide/owners/",
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

    # Two decks now, one per audience, on the same Hi Ted, Meet Lisa
    # `monomind-deck` chassis. They are checked identically because the thing
    # worth guarding is the chassis, not the copy: every responsive fix below
    # was paid for once and is trivially lost when a deck is regenerated.
    for filename, must_name in (
        ("docs/guide-builders.html", "Project Context"),
        ("docs/guide-owners.html", "Project Hub"),
    ):
        guide = ROOT / filename
        if not guide.is_file():
            continue
        guide_text = guide.read_text(encoding="utf-8")
        if "<!doctype html>" not in guide_text:
            errors.append(f"{filename} missing expected content: <!doctype html>")
        # The decks are generated from the template rather than hand-maintained,
        # so a title travels with the deck's own naming. Assert that each is
        # still the right document, not that it kept one string a rename breaks.
        title = re.search(r"<title>([^<]*)</title>", guide_text)
        if not title or must_name not in title.group(1):
            errors.append(f"{filename} title no longer names {must_name}")
        # `file:///…` is an embedded local path and a real leak. A bare `file:`
        # protocol test is not: the deck legitimately hides its self-download
        # and language switch when opened from disk, and says so in a comment.
        if "file:///" in guide_text:
            errors.append(f"{filename} contains a local file URL")
        # A shipped placeholder is the failure mode of a template-filled deck.
        for placeholder in ("[DECK TITLE]", "[FIGURE]", "[SQUARE BRACKETS]"):
            if placeholder in guide_text:
                errors.append(f"{filename} still carries the placeholder {placeholder}")
        responsive_marker = "/* \u2500\u2500 Responsive deck hardening"
        guide_layer_marker = "/* \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\n   Guide layer"
        if responsive_marker not in guide_text:
            errors.append(f"{filename} is missing responsive deck hardening")
        elif (guide_layer_marker in guide_text
              and guide_text.rfind(responsive_marker) < guide_text.find(guide_layer_marker)):
            errors.append(f"{filename} responsive overrides must follow the guide layer")
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
                errors.append(f"{filename} missing responsive behavior: {expected}")

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
