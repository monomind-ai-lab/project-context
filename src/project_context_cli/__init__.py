"""Console entry point for the bundled Project Context initializer.

The initializer locates its templates and the sibling ``project-context``
skill relative to its own file, so the wheel carries the whole ``skills/``
tree unmodified under ``_bundle/`` and this shim simply runs the bundled
script in place. Nothing here duplicates the CLI: one script, two homes.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def main() -> int:
    script = (
        Path(__file__).resolve().parent
        / "_bundle"
        / "skills"
        / "project-context-init"
        / "scripts"
        / "project_context_init.py"
    )
    spec = importlib.util.spec_from_file_location("project_context_init", script)
    if spec is None or spec.loader is None:
        print(f"bundled initializer missing: {script}", file=sys.stderr)
        return 2
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())
