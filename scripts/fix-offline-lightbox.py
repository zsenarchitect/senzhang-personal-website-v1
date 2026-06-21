#!/usr/bin/env python3
"""Patch snapshot HTML so Squarespace lightbox works offline and recovers from stuck overlays."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

BASE_EMPTY_RE = re.compile(r'<base href="">', re.IGNORECASE)

LIGHTBOX_STYLE = """
<style id="offline-lightbox-fix">
/* Offline archive: hide Squarespace lightbox layers; we use the fallback viewer instead. */
.yui3-lightbox2,
.yui3-lightboxoverlay,
.sqs-lightbox-overlay,
.sqs-lightbox-slideshow,
.sqs-lightbox-close {
  display: none !important;
}
.offline-fs-lightbox {
  position: fixed;
  inset: 0;
  z-index: 10000001;
  background: rgba(0, 0, 0, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 72px;
  box-sizing: border-box;
  opacity: 0;
  transition: opacity 0.45s ease;
}
.offline-fs-lightbox.is-open {
  opacity: 1;
}
.offline-fs-lightbox-stage {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  max-width: 1600px;
  min-height: 120px;
}
.offline-fs-lightbox-photo {
  max-width: 100%;
  max-height: calc(100vh - 96px);
  width: auto;
  height: auto;
  object-fit: contain;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.45);
  user-select: none;
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  opacity: 0;
  transition: opacity 0.65s ease-in-out;
  pointer-events: none;
}
.offline-fs-lightbox-photo.is-active {
  opacity: 1;
  z-index: 1;
}
.offline-fs-lightbox-nav {
  position: fixed;
  top: 50%;
  transform: translateY(-50%);
  border: 0;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  font-size: 42px;
  line-height: 1;
  cursor: pointer;
  padding: 12px 16px;
  z-index: 10000002;
  border-radius: 4px;
}
.offline-fs-lightbox-nav:hover {
  background: rgba(255, 255, 255, 0.22);
}
.offline-fs-lightbox-prev {
  left: 16px;
}
.offline-fs-lightbox-next {
  right: 16px;
}
.offline-fs-lightbox-nav[disabled] {
  opacity: 0.25;
  cursor: default;
}
.offline-fs-lightbox-meta {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 16px;
  text-align: center;
  color: rgba(255, 255, 255, 0.88);
  font-size: 14px;
  line-height: 1.4;
  pointer-events: none;
  z-index: 10000002;
  padding: 0 72px;
  opacity: 1;
  transition: opacity 0.35s ease-in-out;
}
.offline-fs-lightbox.is-meta-fading .offline-fs-lightbox-meta {
  opacity: 0.25;
}
.offline-fs-lightbox-counter {
  display: block;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.75;
  margin-bottom: 4px;
}
.offline-fs-lightbox-caption:empty {
  display: none;
}
.offline-fs-lightbox.is-single .offline-fs-lightbox-nav,
.offline-fs-lightbox.is-single .offline-fs-lightbox-counter {
  display: none;
}
.offline-fs-lightbox-close {
  position: fixed;
  top: 16px;
  right: 20px;
  border: 0;
  background: transparent;
  color: #fff;
  font-size: 36px;
  line-height: 1;
  cursor: pointer;
  padding: 8px;
  z-index: 10000002;
}
html.offline-fs-lightbox-open,
html.offline-fs-lightbox-open body {
  overflow: hidden;
}
</style>
"""

LIGHTBOX_SCRIPT = r"""
<script id="offline-lightbox-fix">
(function () {
  var lightboxState = null;
  var SLIDE_FADE_MS = 650;
  var OVERLAY_FADE_MS = 450;

  var MEDIA_EXT_RE =
    /\.(jpe?g|png|gif|webp|bmp|svg|mp4|m4v|mov|webm|avi|pdf|tiff?)$/i;
  var CDN_HASH_FILENAME_RE =
    /^[a-f0-9]{8,}\.(jpe?g|png|gif|webp|bmp|svg|mp4|m4v|mov|webm|avi|pdf|tiff?)$/i;
  var CAMERA_EXPORT_RE =
    /^(IMG[_-]|DSC[_-]?|DSCN|P\d{7}|DSCF|SAM[_-]|Screenshot|Screen\s?Shot)/i;

  function sanitizePublicLabel(text) {
    if (!text) {
      return "";
    }
    text = String(text).replace(/\s+/g, " ").trim();
    if (!text) {
      return "";
    }
    if (CDN_HASH_FILENAME_RE.test(text)) {
      return "";
    }
    if (MEDIA_EXT_RE.test(text)) {
      return "";
    }
    if (CAMERA_EXPORT_RE.test(text) && /\d/.test(text)) {
      return "";
    }
    return text;
  }

  function normalizeImageUrl(src) {
    if (!src) {
      return "";
    }
    if (
      src.indexOf("http://") === 0 ||
      src.indexOf("https://") === 0 ||
      src.indexOf("data:") === 0
    ) {
      return src;
    }
    if (src.charAt(0) === "/") {
      return src;
    }
    return "/" + src.replace(/^\.\//, "");
  }

  function bestImageUrl(img) {
    if (!img) {
      return "";
    }
    var srcset = img.getAttribute("srcset");
    if (srcset) {
      var best = "";
      var bestW = -1;
      srcset.split(",").forEach(function (part) {
        part = part.trim();
        var bits = part.split(/\\s+/);
        if (bits.length < 2) {
          return;
        }
        var url = bits[0];
        var descriptor = bits[bits.length - 1];
        if (descriptor.slice(-1) !== "w") {
          return;
        }
        var width = parseInt(descriptor.slice(0, -1), 10);
        if (width > bestW) {
          bestW = width;
          best = url;
        }
      });
      if (best) {
        return best;
      }
    }
    return (
      img.getAttribute("data-image") ||
      img.getAttribute("data-src") ||
      img.currentSrc ||
      img.src ||
      ""
    );
  }

  function isProjectNavLink(anchor) {
    if (!anchor) {
      return false;
    }
    var href = anchor.getAttribute("href") || "";
    return /\.html$/i.test(href) && href.indexOf("#") !== 0;
  }

  function closeSquarespaceLightbox() {
    var close = document.querySelector(".sqs-lightbox-close");
    if (close) {
      close.click();
    }
  }

  function closeFallbackLightbox() {
    if (lightboxState && lightboxState.timer) {
      clearTimeout(lightboxState.timer);
    }
    if (lightboxState && lightboxState.transitionTimer) {
      clearTimeout(lightboxState.transitionTimer);
    }
    if (lightboxState && lightboxState.closeTimer) {
      clearTimeout(lightboxState.closeTimer);
    }
    var el = document.getElementById("offline-fs-lightbox");
    if (!el) {
      lightboxState = null;
      document.documentElement.classList.remove("offline-fs-lightbox-open");
      document.removeEventListener("keydown", onLightboxKeydown, true);
      return;
    }
    if (lightboxState && lightboxState.closing) {
      return;
    }
    if (lightboxState) {
      lightboxState.closing = true;
    }
    el.classList.remove("is-open");
    var closeTimer = setTimeout(function () {
      if (el.parentNode) {
        el.parentNode.removeChild(el);
      }
      lightboxState = null;
      document.documentElement.classList.remove("offline-fs-lightbox-open");
      document.removeEventListener("keydown", onLightboxKeydown, true);
    }, OVERLAY_FADE_MS);
    if (lightboxState) {
      lightboxState.closeTimer = closeTimer;
    }
  }

  function onLightboxKeydown(event) {
    if (!lightboxState) {
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      closeFallbackLightbox();
      closeSquarespaceLightbox();
      return;
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      stepLightbox(-1, true);
      return;
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      stepLightbox(1, true);
    }
  }

  function galleryAutoplayMs(galleryBlock) {
    if (!galleryBlock) {
      return 0;
    }
    var raw = galleryBlock.getAttribute("data-block-json");
    if (!raw) {
      return 0;
    }
    try {
      var json = JSON.parse(raw);
      if (json.autoplay && json["autoplay-duration"]) {
        return parseInt(json["autoplay-duration"], 10) * 1000;
      }
    } catch (ignore) {}
    return 0;
  }

  function collectGalleryItems(galleryBlock, clickedImg) {
    var slideNodes = galleryBlock.querySelectorAll(".slide");
    var items = [];
    var startIndex = 0;
    slideNodes.forEach(function (slide) {
      var img = slide.querySelector("img");
      if (!img) {
        return;
      }
      var src = bestImageUrl(img);
      if (!src) {
        return;
      }
      var captionEl = slide.querySelector(".meta-title, .meta-description, .meta");
      var caption = captionEl ? captionEl.textContent.replace(/\s+/g, " ").trim() : "";
      if (!caption) {
        caption = img.getAttribute("alt") || "";
      }
      caption = sanitizePublicLabel(caption);
      if (img === clickedImg) {
        startIndex = items.length;
      }
      items.push({
        src: src,
        alt: sanitizePublicLabel(img.getAttribute("alt") || ""),
        caption: caption
      });
    });
    return { items: items, startIndex: startIndex };
  }

  function clearAutoplayTimer() {
    if (lightboxState && lightboxState.timer) {
      clearTimeout(lightboxState.timer);
      lightboxState.timer = null;
    }
  }

  function scheduleAutoplay(delayMs) {
    if (
      !lightboxState ||
      !lightboxState.autoplayMs ||
      lightboxState.items.length < 2 ||
      lightboxState.closing ||
      lightboxState.paused
    ) {
      return;
    }
    clearAutoplayTimer();
    var wait = typeof delayMs === "number" ? delayMs : lightboxState.autoplayMs;
    lightboxState.timer = setTimeout(autoplayTick, wait);
  }

  function autoplayTick() {
    if (!lightboxState || lightboxState.closing || lightboxState.paused) {
      return;
    }
    lightboxState.timer = null;
    if (lightboxState.transitioning) {
      scheduleAutoplay(150);
      return;
    }
    if (!stepLightbox(1, false)) {
      scheduleAutoplay(150);
      return;
    }
    scheduleAutoplay();
  }

  function restartAutoplay() {
    scheduleAutoplay();
  }

  function pauseAutoplay() {
    if (!lightboxState) {
      return;
    }
    lightboxState.paused = true;
    clearAutoplayTimer();
  }

  function resumeAutoplay() {
    if (!lightboxState) {
      return;
    }
    lightboxState.paused = false;
    scheduleAutoplay();
  }

  function updateLightboxMeta(overlay) {
    if (!lightboxState || !overlay) {
      return;
    }
    var item = lightboxState.items[lightboxState.index];
    var counter = overlay.querySelector(".offline-fs-lightbox-counter");
    var caption = overlay.querySelector(".offline-fs-lightbox-caption");
    var prev = overlay.querySelector(".offline-fs-lightbox-prev");
    var next = overlay.querySelector(".offline-fs-lightbox-next");
    if (counter) {
      counter.textContent =
        lightboxState.index + 1 + " / " + lightboxState.items.length;
    }
    if (caption) {
      caption.textContent = sanitizePublicLabel(item.caption || "");
    }
    if (prev) {
      prev.disabled =
        lightboxState.items.length < 2 || !!lightboxState.transitioning;
    }
    if (next) {
      next.disabled =
        lightboxState.items.length < 2 || !!lightboxState.transitioning;
    }
  }

  function getStagePhotos(overlay) {
    return overlay.querySelectorAll(".offline-fs-lightbox-photo");
  }

  function showLightboxSlide(animate) {
    if (!lightboxState) {
      return;
    }
    var overlay = document.getElementById("offline-fs-lightbox");
    if (!overlay) {
      return;
    }
    var photos = getStagePhotos(overlay);
    if (!photos.length) {
      return;
    }
    var item = lightboxState.items[lightboxState.index];
    var url = normalizeImageUrl(item.src);
    var alt =
      sanitizePublicLabel(item.alt) ||
      sanitizePublicLabel(item.caption) ||
      "";
    var active =
      overlay.querySelector(".offline-fs-lightbox-photo.is-active") || photos[0];
    var inactive = active === photos[0] ? photos[1] : photos[0];

    function applyToPhoto(photo) {
      photo.src = url;
      photo.alt = alt;
    }

    function finishTransition() {
      if (!lightboxState) {
        return;
      }
      lightboxState.transitioning = false;
      if (lightboxState.transitionTimer) {
        clearTimeout(lightboxState.transitionTimer);
        lightboxState.transitionTimer = null;
      }
      overlay.classList.remove("is-meta-fading");
      updateLightboxMeta(overlay);
      if (
        lightboxState.autoplayMs &&
        !lightboxState.paused &&
        !lightboxState.timer &&
        !lightboxState.closing
      ) {
        scheduleAutoplay();
      }
    }

    updateLightboxMeta(overlay);

    if (
      !animate ||
      photos.length < 2 ||
      normalizeImageUrl(active.src) === url
    ) {
      applyToPhoto(active);
      active.classList.add("is-active");
      if (photos[1]) {
        photos[1].classList.remove("is-active");
      }
      finishTransition();
      return;
    }

    if (lightboxState.transitioning) {
      return;
    }
    lightboxState.transitioning = true;
    overlay.classList.add("is-meta-fading");
    updateLightboxMeta(overlay);
    if (lightboxState.transitionTimer) {
      clearTimeout(lightboxState.transitionTimer);
    }
    lightboxState.transitionTimer = setTimeout(function () {
      if (lightboxState && lightboxState.transitioning) {
        finishTransition();
      }
    }, SLIDE_FADE_MS + 8000);

    var revealed = false;
    function revealLoadedSlide() {
      if (revealed || !lightboxState || !lightboxState.transitioning) {
        return;
      }
      revealed = true;
      applyToPhoto(inactive);
      inactive.classList.add("is-active");
      active.classList.remove("is-active");
      setTimeout(function () {
        finishTransition();
      }, SLIDE_FADE_MS);
    }

    var loader = new Image();
    loader.onload = revealLoadedSlide;
    loader.onerror = function () {
      applyToPhoto(active);
      active.classList.add("is-active");
      inactive.classList.remove("is-active");
      finishTransition();
    };
    loader.src = url;
    if (loader.complete && loader.naturalWidth > 0) {
      revealLoadedSlide();
    }
  }

  function stepLightbox(delta, manual) {
    if (
      !lightboxState ||
      lightboxState.items.length < 2 ||
      lightboxState.transitioning ||
      lightboxState.closing
    ) {
      return false;
    }
    var count = lightboxState.items.length;
    lightboxState.index = (lightboxState.index + delta + count) % count;
    showLightboxSlide(true);
    if (manual) {
      restartAutoplay();
    }
    return true;
  }

  function openFallbackLightbox(items, startIndex, autoplayMs) {
    if (!items || !items.length) {
      return;
    }
    startIndex = startIndex || 0;
    if (startIndex < 0 || startIndex >= items.length) {
      startIndex = 0;
    }
    closeFallbackLightbox();
    closeSquarespaceLightbox();
    document.documentElement.classList.add("offline-fs-lightbox-open");
    var overlay = document.createElement("div");
    overlay.id = "offline-fs-lightbox";
    overlay.className = "offline-fs-lightbox";
    if (items.length < 2) {
      overlay.classList.add("is-single");
    }
    overlay.innerHTML =
      '<button type="button" class="offline-fs-lightbox-close" aria-label="Close">&times;</button>' +
      '<button type="button" class="offline-fs-lightbox-nav offline-fs-lightbox-prev" aria-label="Previous image">&lsaquo;</button>' +
      '<button type="button" class="offline-fs-lightbox-nav offline-fs-lightbox-next" aria-label="Next image">&rsaquo;</button>' +
      '<div class="offline-fs-lightbox-stage">' +
      '<img class="offline-fs-lightbox-photo is-active" src="" alt="">' +
      '<img class="offline-fs-lightbox-photo" src="" alt="">' +
      "</div>" +
      '<div class="offline-fs-lightbox-meta">' +
      '<span class="offline-fs-lightbox-counter"></span>' +
      '<span class="offline-fs-lightbox-caption"></span>' +
      "</div>";
    overlay.querySelector(".offline-fs-lightbox-close").addEventListener(
      "click",
      function (event) {
        event.stopPropagation();
        closeFallbackLightbox();
      }
    );
    overlay.querySelector(".offline-fs-lightbox-prev").addEventListener(
      "click",
      function (event) {
        event.stopPropagation();
        stepLightbox(-1, true);
      }
    );
    overlay.querySelector(".offline-fs-lightbox-next").addEventListener(
      "click",
      function (event) {
        event.stopPropagation();
        stepLightbox(1, true);
      }
    );
    var pauseTargets = overlay.querySelectorAll(
      ".offline-fs-lightbox-nav, .offline-fs-lightbox-close"
    );
    pauseTargets.forEach(function (btn) {
      btn.addEventListener("mouseenter", pauseAutoplay);
      btn.addEventListener("mouseleave", resumeAutoplay);
    });
    overlay.addEventListener("click", function (event) {
      if (event.target === overlay) {
        closeFallbackLightbox();
      }
    });
    document.body.appendChild(overlay);
    lightboxState = {
      items: items,
      index: startIndex,
      autoplayMs: autoplayMs || 0,
      timer: null,
      transitioning: false,
      transitionTimer: null,
      paused: false,
      closing: false,
      closeTimer: null
    };
    showLightboxSlide(false);
    restartAutoplay();
    document.addEventListener("keydown", onLightboxKeydown, true);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        overlay.classList.add("is-open");
      });
    });
  }

  function openFallbackLightboxFromImage(img) {
    var galleryBlock = img.closest(".sqs-block-gallery");
    if (galleryBlock) {
      var gallery = collectGalleryItems(galleryBlock, img);
      if (gallery.items.length) {
        openFallbackLightbox(
          gallery.items,
          gallery.startIndex,
          galleryAutoplayMs(galleryBlock)
        );
        return;
      }
    }
    var src = bestImageUrl(img);
    if (!src) {
      return;
    }
    var label = sanitizePublicLabel(img.getAttribute("alt") || "");
    openFallbackLightbox(
      [
        {
          src: src,
          alt: label,
          caption: label
        }
      ],
      0,
      0
    );
  }

  function findLightboxImage(target) {
    if (!target || !target.closest) {
      return null;
    }
    var btn = target.closest("[data-sqsp-image-classic-block-lightbox-button]");
    if (btn) {
      return btn.querySelector("img");
    }
    var slide = target.closest(
      ".sqs-gallery-block-slideshow .slide, .sqs-block-gallery .slide"
    );
    if (slide) {
      return slide.querySelector("img");
    }
    var img = target.closest("img");
    if (!img) {
      return null;
    }
    if (!img.closest(".sqs-block-image, .sqs-block-gallery")) {
      return null;
    }
    if (img.closest("[data-sqsp-image-classic-block-lightbox-button]")) {
      return img;
    }
    if (img.hasAttribute("data-sqsp-image-classic-block-image")) {
      return img;
    }
    return null;
  }

  function lightboxImageVisible() {
    var lbImg = document.querySelector(".sqs-lightbox-slideshow img");
    if (!lbImg || lbImg.naturalWidth < 1) {
      return false;
    }
    var rect = lbImg.getBoundingClientRect();
    if (rect.width < 120 || rect.height < 120) {
      return false;
    }
    if (rect.bottom <= 0 || rect.top >= window.innerHeight) {
      return false;
    }
    if (rect.right <= 0 || rect.left >= window.innerWidth) {
      return false;
    }
    var slide = lbImg.closest(".sqs-lightbox-slide");
    if (slide) {
      var slideOpacity = parseFloat(
        window.getComputedStyle(slide).opacity || "0"
      );
      if (slideOpacity < 0.5) {
        return false;
      }
    }
    return true;
  }

  function suppressSquarespaceLightbox() {
    closeSquarespaceLightbox();
    var overlays = document.querySelectorAll(".sqs-lightbox-overlay");
    overlays.forEach(function (overlay) {
      overlay.style.display = "none";
      overlay.style.opacity = "0";
    });
  }

  document.addEventListener(
    "click",
    function (event) {
      var img = findLightboxImage(event.target);
      if (!img) {
        return;
      }
      var nav = img.closest("a[href]");
      if (nav && isProjectNavLink(nav)) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      if (event.stopImmediatePropagation) {
        event.stopImmediatePropagation();
      }

      openFallbackLightboxFromImage(img);
    },
    true
  );

  setInterval(function () {
    if (document.getElementById("offline-fs-lightbox")) {
      suppressSquarespaceLightbox();
      return;
    }
    var overlay = document.querySelector(".sqs-lightbox-overlay");
    if (!overlay) {
      return;
    }
    var opacity = parseFloat(window.getComputedStyle(overlay).opacity || "0");
    if (opacity < 0.5) {
      return;
    }
    if (!lightboxImageVisible()) {
      suppressSquarespaceLightbox();
    }
  }, 500);
})();
</script>
"""

OLD_LIGHTBOX_STYLE_RE = re.compile(
    r'<style id="offline-lightbox-fix">.*?</style>\s*',
    re.DOTALL | re.IGNORECASE,
)
OLD_LIGHTBOX_SCRIPT_RE = re.compile(
    r'<script id="offline-lightbox-fix">.*?</script>\s*',
    re.DOTALL | re.IGNORECASE,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def patch_html(html: str) -> tuple[str, bool]:
    changed = False
    original = html

    if BASE_EMPTY_RE.search(html):
        html = BASE_EMPTY_RE.sub('<base href="/">', html)

    if OLD_LIGHTBOX_STYLE_RE.search(html):
        html = OLD_LIGHTBOX_STYLE_RE.sub(lambda _m: LIGHTBOX_STYLE, html, count=1)
    if OLD_LIGHTBOX_SCRIPT_RE.search(html):
        html = OLD_LIGHTBOX_SCRIPT_RE.sub(lambda _m: LIGHTBOX_SCRIPT, html, count=1)

    if 'id="offline-lightbox-fix"' not in html:
        html = html.replace("</head>", LIGHTBOX_STYLE + LIGHTBOX_SCRIPT + "\n</head>", 1)

    if html != original:
        changed = True
    return html, changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix offline Squarespace lightbox in snapshot HTML")
    parser.add_argument("date", nargs="?", default="2026-06-05")
    args = parser.parse_args()

    snap = repo_root() / "snapshot" / args.date
    if not snap.is_dir():
        raise SystemExit("Missing snapshot: {}".format(snap))

    patched: list[str] = []
    for html_path in sorted(snap.glob("*.html")):
        original = html_path.read_text(encoding="utf-8")
        updated, changed = patch_html(original)
        if changed:
            html_path.write_text(updated, encoding="utf-8")
            patched.append(html_path.name)

    print("Patched {} HTML files for offline lightbox.".format(len(patched)))
    for name in patched:
        print("  {}".format(name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
