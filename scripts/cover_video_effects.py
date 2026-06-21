#!/usr/bin/env python3
"""Squarespace cover-page video effect helpers (filter + playback speed)."""
from __future__ import annotations

import re

# Matches @squarespace/video-background-rendering (slides bundle 149643).
FILTER_OPTIONS = [
    "none",
    "blur",
    "brightness",
    "contrast",
    "invert",
    "opacity",
    "saturate",
    "sepia",
    "drop-shadow",
    "grayscale",
    "hue-rotate",
]


def filter_css(filter_index: int, strength: int) -> tuple[str, bool]:
    """Return (css filter value, is_blur). filter_index is 1-based like data-config-filter."""
    if filter_index <= 0:
        return "", False
    name = FILTER_OPTIONS[filter_index - 1]
    if name == "none":
        return "", False
    if name == "blur":
        px = round(strength * 0.3, 2)
        return "blur({}px)".format(px), True
    if name == "brightness":
        val = round(strength * 0.009 + 0.1, 3)
        return "brightness({})".format(val), False
    if name == "contrast":
        val = round(strength * 0.4 + 80, 2)
        return "contrast({}%)".format(val), False
    if name == "grayscale":
        return "grayscale({}%)".format(strength), False
    if name == "hue-rotate":
        val = round(strength * 3.6, 2)
        return "hue-rotate({}deg)".format(val), False
    if name == "invert":
        return "invert(1)", False
    if name == "opacity":
        return "opacity({}%)".format(strength), False
    if name == "saturate":
        val = round(strength * 2, 2)
        return "saturate({}%)".format(val), False
    if name == "sepia":
        return "sepia({}%)".format(strength), False
    return "", False


GALLERY_CONFIG_RE = re.compile(
    r'class="sqs-slice-gallery-item gallery-video-background[^"]*"[^>]*'
    r'data-config-playback-speed="([^"]+)"[^>]*'
    r'data-config-filter="(\d+)"[^>]*'
    r'data-config-filter-strength="(\d+)"',
    re.IGNORECASE | re.DOTALL,
)

GALLERY_CONFIG_RE_ALT = re.compile(
    r'data-config-filter="(\d+)"[^>]*data-config-filter-strength="(\d+)"[^>]*'
    r'data-config-playback-speed="([^"]+)"',
    re.IGNORECASE | re.DOTALL,
)

COVER_STYLE_RE = re.compile(
    r'<style id="offline-cover-video-style">.*?</style>',
    re.DOTALL | re.IGNORECASE,
)

COVER_SCRIPT_RE = re.compile(
    r'<script id="offline-cover-video-fx">.*?</script>',
    re.DOTALL | re.IGNORECASE,
)


def parse_gallery_config(html: str) -> tuple[float, int, int]:
    m = GALLERY_CONFIG_RE.search(html)
    if m:
        speed = float(m.group(1))
        filt = int(m.group(2))
        strength = int(m.group(3))
        return speed, filt, strength
    m = GALLERY_CONFIG_RE_ALT.search(html)
    if m:
        filt = int(m.group(1))
        strength = int(m.group(2))
        speed = float(m.group(3))
        return speed, filt, strength
    return 1.5, 2, 13


def build_cover_style(filter_index: int, strength: int) -> str:
    css_filter, is_blur = filter_css(filter_index, strength)
    blur_bg = (
        ".sqs-slide-layer.layer-back .offline-cover-video-shell.filter-blur "
        "{ background-color: #7f7f7f; }\n"
        if is_blur
        else ""
    )
    filter_rules = ""
    if css_filter:
        scale = " scale(1.08)" if is_blur else ""
        filter_rules = (
            "  filter: {f};\n"
            "  -webkit-filter: {f};\n"
            "  transform: translate(-50%, -50%){scale};\n"
        ).format(f=css_filter, scale=scale)

    return (
        "<style id=\"offline-cover-video-style\">\n"
        ".sqs-slide-layer.layer-back {{ position: relative; }}\n"
        ".sqs-slide-layer.layer-back .offline-cover-video-shell {{\n"
        "  position: absolute; top: 0; left: 0; width: 100%; height: 100%;\n"
        "  z-index: 0; overflow: hidden;\n"
        "}}\n"
        "{blur_bg}"
        ".sqs-slide-layer.layer-back .offline-cover-video-shell video.offline-cover-video {{\n"
        "  position: absolute; top: 50%; left: 50%; min-width: 100%; min-height: 100%;\n"
        "  width: auto; height: auto; object-fit: cover;\n"
        "{filter_rules}"
        "}}\n"
        ".sqs-slice-gallery-item.gallery-video-background #player {{ display: none !important; }}\n"
        ".sqs-slice-gallery-item.gallery-video-background .custom-fallback-image "
        "{{ display: none !important; }}\n"
        "</style>"
    ).format(blur_bg=blur_bg, filter_rules=filter_rules)


def build_playback_script(speed: float) -> str:
    return (
        '<script id="offline-cover-video-fx">'
        "document.addEventListener('DOMContentLoaded',function(){"
        "document.querySelectorAll('.offline-cover-video-shell video.offline-cover-video')"
        ".forEach(function(v){v.playbackRate=" + str(speed) + ";});"
        "});"
        "</script>"
    )


def apply_cover_effects(html: str) -> tuple[str, bool]:
    speed, filt, strength = parse_gallery_config(html)
    _, is_blur = filter_css(filt, strength)
    style = build_cover_style(filt, strength)
    script = build_playback_script(speed)

    if COVER_STYLE_RE.search(html):
        html = COVER_STYLE_RE.sub(style, html, count=1)
    else:
        html = html.replace("</head>", style + "\n</head>", 1)

    if COVER_SCRIPT_RE.search(html):
        html = COVER_SCRIPT_RE.sub(script, html, count=1)
    elif 'id="offline-cover-video-fx"' not in html:
        html = html.replace("</head>", script + "\n</head>", 1)

    shell_class = 'class="offline-cover-video-shell filter-blur"' if is_blur else 'class="offline-cover-video-shell"'
    html = html.replace('class="offline-cover-video-shell"', shell_class)

    return html, True
