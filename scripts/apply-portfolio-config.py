#!/usr/bin/env python3
"""Apply tracked data/projects.json to snapshot HTML (grids, menu, about-me)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

V1 = Path(__file__).resolve().parents[1]
REGISTRY = V1 / "data" / "projects.json"

STEPS = (
    "restructure-menu-sections.py",
    "port-about-resume.py",
)


def main() -> int:
    if not REGISTRY.is_file():
        raise SystemExit("missing tracked config: {}".format(REGISTRY.relative_to(V1)))

    sys.path.insert(0, str(V1 / "scripts"))
    from project_registry import merge_registry_on_disk

    merge_registry_on_disk()

    for name in STEPS:
        script = V1 / "scripts" / name
        if not script.is_file():
            raise SystemExit("missing script: {}".format(name))
        subprocess.check_call([sys.executable, str(script)], cwd=str(V1))

    print("applied portfolio config from", REGISTRY.relative_to(V1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
