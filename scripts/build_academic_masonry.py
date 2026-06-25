#!/usr/bin/env python3
"""Backward-compatible shim; use build_section_masonry instead."""
from build_section_masonry import (  # noqa: F401
    ACADEMIC_LABELS,
    ACADEMIC_ORDER,
    ACADEMIC_SLUGS,
    SECTIONS,
    build_from_tile_dict,
    inject_masonry_style,
    render_masonry_inner,
)
from build_section_masonry import backup_legacy_grid as _backup_legacy_grid
from build_section_masonry import build_from_page_html as _build_from_page_html

_ACADEMIC = SECTIONS["academic"]
MARKER = _ACADEMIC.marker
STYLE_ID = "section-masonry"


def build_from_page_html(page_html):
    return _build_from_page_html(_ACADEMIC, page_html)


def backup_legacy_grid(path, page_html):
    return _backup_legacy_grid(path, page_html, _ACADEMIC.marker)
