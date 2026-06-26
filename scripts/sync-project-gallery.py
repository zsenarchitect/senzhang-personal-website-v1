#!/usr/bin/env python3
"""Rebuild project HTML gallery sections from numbered files on disk."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import project_page


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "slugs",
        nargs="*",
        help="Project slugs to sync (default: all with numbered gallery files)",
    )
    args = parser.parse_args()

    if args.slugs:
        for slug in args.slugs:
            path = project_page.sync_project_gallery(slug)
            print("synced {0} -> {1}".format(slug, path.relative_to(project_page.V1)))
    else:
        synced = project_page.sync_all_project_galleries()
        for slug in synced:
            print("synced {0}".format(slug))
        if not synced:
            print("no project galleries to sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
