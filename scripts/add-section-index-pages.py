#!/usr/bin/env python3
"""Deprecated: section grids are built by restructure-menu-sections.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

V1 = Path(__file__).resolve().parents[1]


def main():
    subprocess.check_call(
        [sys.executable, str(V1 / "scripts" / "restructure-menu-sections.py")],
        cwd=str(V1),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
