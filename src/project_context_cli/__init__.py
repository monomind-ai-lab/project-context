"""Console entry point for the bundled Project Context tools.

The tool locates its own templates and sibling skills relative to its file, so
the wheel carries the whole ``skills/`` tree unmodified under ``_bundle/``.
This shim only loads the bundled script and forwards its arguments; it does not
duplicate the CLI.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType


def _load_script(skill: str, filename: str) -> ModuleType | None:
    script = (
        Path(__file__).resolve().parent
        / "_bundle"
        / "skills"
        / skill
        / "scripts"
        / filename
    )
    module_name = filename.removesuffix(".py")
    if not script.is_file():
        print(f"bundled Project Context tool missing: {script}", file=sys.stderr)
        return None
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        print(f"bundled Project Context tool missing: {script}", file=sys.stderr)
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    argv = sys.argv[1:]
    module = _load_script("project-context-init", "project_context_init.py")
    if module is None:
        return 2
    return int(module.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
