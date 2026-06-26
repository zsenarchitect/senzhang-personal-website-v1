/**
 * Local dev only: corner "ID" button on portfolio assets to copy paths for AI edits.
 * Injected by scripts/serve.py into snapshot HTML pages.
 */
(function () {
  "use strict";

  var BTN_CLASS = "asset-corner-copy-id";
  var WRAP_CLASS = "asset-corner-wrap";
  var COPIED_MS = 1200;

  var style = document.createElement("style");
  style.textContent =
    "." + WRAP_CLASS + "{position:relative;display:inline-block;max-width:100%}" +
    "." + WRAP_CLASS + " > img," +
    "." + WRAP_CLASS + " > video{display:block;max-width:100%;height:auto}" +
    "." + BTN_CLASS + "{" +
    "position:absolute;top:6px;right:6px;z-index:20;" +
    "font:600 10px/1 system-ui,sans-serif;letter-spacing:0.04em;" +
    "padding:3px 6px;border-radius:3px;border:1px solid rgba(255,255,255,0.55);" +
    "background:rgba(0,0,0,0.55);color:#fff;cursor:pointer;" +
    "opacity:0;transition:opacity 0.15s ease;" +
    "}" +
    "." + WRAP_CLASS + ":hover ." + BTN_CLASS + ",." + BTN_CLASS + ":focus{opacity:1}" +
    "." + BTN_CLASS + ".copied{background:#0a5;border-color:#0a5}";
  document.head.appendChild(style);

  var projectSlug = null;
  var marker = document.body && document.body.innerHTML.match(/<!--\s*project-page-v1\s+slug=([^\s]+)/);
  if (marker) projectSlug = marker[1];

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand("copy") ? resolve() : reject(new Error("copy failed"));
      } catch (e) {
        reject(e);
      } finally {
        document.body.removeChild(ta);
      }
    });
  }

  function normalizeAssetId(raw) {
    if (!raw) return null;
    var s = String(raw).trim();
    if (!s || s.indexOf("data:") === 0) return null;
    try {
      if (/^https?:\/\//i.test(s)) {
        var u = new URL(s, window.location.origin);
        s = u.pathname;
      }
    } catch (e) { /* keep s */ }
    s = s.replace(/^\//, "");
    if (s.indexOf("_media/") >= 0) {
      s = s.slice(s.indexOf("_media/"));
    }
    if (s.indexOf("_media/") !== 0) return null;
    return s;
  }

  function assetIdFromElement(el) {
    var explicit = el.getAttribute("data-asset-id");
    if (explicit) {
      var n = normalizeAssetId(explicit);
      if (n) return n;
    }
    var src = el.getAttribute("src") || el.getAttribute("data-src") ||
      el.getAttribute("data-offline-video") || "";
    return normalizeAssetId(src);
  }

  function isEligibleMedia(el) {
    if (!el || el.dataset.assetCornerDone) return false;
    if (el.closest("." + BTN_CLASS)) return false;
    if (el.closest(".has-aspect-ratio, .menu-hub-aspect")) return false;
    var tag = el.tagName;
    if (tag !== "IMG" && tag !== "VIDEO") return false;
    var id = assetIdFromElement(el);
    if (!id) return false;
    if (!el.closest(".main-content") &&
        !el.closest(".sqs-block-image") &&
        id.indexOf("_media/") !== 0) {
      return false;
    }
    return true;
  }

  function ensureWrap(media) {
    var parent = media.parentElement;
    if (parent && parent.classList.contains(WRAP_CLASS)) return parent;
    var wrap = document.createElement("span");
    wrap.className = WRAP_CLASS;
    media.parentNode.insertBefore(wrap, media);
    wrap.appendChild(media);
    return wrap;
  }

  function makeButton(assetId) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = BTN_CLASS;
    btn.title = "Copy asset ID: " + assetId;
    btn.textContent = "ID";
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      copyText(assetId).then(function () {
        var prev = btn.textContent;
        btn.textContent = "Copied!";
        btn.classList.add("copied");
        setTimeout(function () {
          btn.textContent = prev;
          btn.classList.remove("copied");
        }, COPIED_MS);
      }).catch(function () {
        btn.textContent = "Err";
        setTimeout(function () { btn.textContent = "ID"; }, COPIED_MS);
      });
    });
    return btn;
  }

  function decorateMedia(media) {
    if (!isEligibleMedia(media)) return;
    var assetId = assetIdFromElement(media);
    if (!assetId) return;
    media.dataset.assetCornerDone = "1";
    var wrap = ensureWrap(media);
    if (wrap.querySelector("." + BTN_CLASS)) return;
    wrap.appendChild(makeButton(assetId));
  }

  function scan(root) {
    var scope = root || document;
    var nodes = scope.querySelectorAll
      ? scope.querySelectorAll(".main-content img[src], .main-content video[src], .sqs-block-image img[src], img[src*=\"_media/\"], video[src*=\"_media/\"]")
      : [];
    for (var i = 0; i < nodes.length; i++) decorateMedia(nodes[i]);
  }

  function boot() {
    scan(document);
    var obs = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        var m = mutations[i];
        for (var j = 0; j < m.addedNodes.length; j++) {
          var node = m.addedNodes[j];
          if (node.nodeType !== 1) continue;
          if (node.tagName === "IMG" || node.tagName === "VIDEO") {
            decorateMedia(node);
          } else {
            scan(node);
          }
        }
      }
    });
    if (document.body) {
      obs.observe(document.body, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
