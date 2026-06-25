#!/usr/bin/env python3
"""Normalize Vercel build output paths for Linux deploy (Windows backslash fix)."""
from __future__ import annotations

import json
from pathlib import Path


def normalize_path(p: str) -> str:
    p = p.replace("\\", "/")
    if p.endswith("/index"):
        p = p[: -len("/index")]
    return p


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    cfg_path = repo / ".vercel" / "output" / "config.json"
    if not cfg_path.is_file():
        raise SystemExit("missing {}".format(cfg_path))

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    overrides = cfg.get("overrides") or {}
    fixed = {}
    for key, val in overrides.items():
        nkey = key.replace("\\", "/")
        path = normalize_path(val.get("path", ""))
        fixed[nkey] = {"path": path}
    cfg["overrides"] = fixed
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print("normalized {} override paths".format(len(fixed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())