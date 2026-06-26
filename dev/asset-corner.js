/**
 * Local dev only: corner metadata panel on portfolio assets (ID, file, size, dims).
 * Injected by scripts/serve.py into snapshot HTML pages.
 */
(function () {
  "use strict";

  var PANEL_CLASS = "asset-corner-panel";
  var ANCHOR_CLASS = "asset-corner-anchor";
  var COPIED_MS = 1200;
  var INFO_API = "/__dev__/asset-info";

  var style = document.createElement("style");
  style.textContent =
    "." + ANCHOR_CLASS + "{position:relative}" +
    "." + PANEL_CLASS + "{" +
    "position:absolute;left:4px;bottom:4px;z-index:25;max-width:min(240px,92%);" +
    "font:10px/1.35 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;" +
    "padding:4px 6px;border-radius:4px;border:1px solid rgba(255,255,255,0.35);" +
    "background:rgba(0,0,0,0.78);color:#f2f2f2;pointer-events:auto;" +
    "opacity:0;transition:opacity 0.15s ease;text-align:left;" +
    "}" +
    "." + ANCHOR_CLASS + ":hover ." + PANEL_CLASS + ",." + PANEL_CLASS + ":hover{opacity:1}" +
    "." + PANEL_CLASS + " .ac-row{margin:0;padding:1px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}" +
    "." + PANEL_CLASS + " .ac-row button{" +
    "all:unset;cursor:pointer;display:block;width:100%;text-align:left;color:inherit}" +
    "." + PANEL_CLASS + " .ac-row button:hover{text-decoration:underline}" +
    "." + PANEL_CLASS + " .ac-label{color:#9ab;display:inline}" +
    "." + PANEL_CLASS + " .ac-dup{color:#fc6}" +
    "." + PANEL_CLASS + " .ac-copied{color:#6f6}";
  document.head.appendChild(style);

  var pageCounts = Object.create(null);

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

  function formatBytes(n) {
    if (n == null || isNaN(n)) return "?";
    if (n < 1024) return n + " B";
    if (n < 1024 * 1024) return (n / 1024).toFixed(n < 10240 ? 1 : 0) + " KB";
    return (n / (1024 * 1024)).toFixed(n < 10485760 ? 2 : 1) + " MB";
  }

  function normalizeAssetPath(raw) {
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
    if (s.indexOf("_media/") >= 0) return s.slice(s.indexOf("_media/"));
    if (s.indexOf("_cdn/") >= 0) return s.slice(s.indexOf("_cdn/"));
    return null;
  }

  function assetPathFromElement(el) {
    var explicit = el.getAttribute("data-asset-id");
    if (explicit) {
      var n = normalizeAssetPath(explicit);
      if (n) return n;
    }
    var src = el.getAttribute("src") || el.getAttribute("data-src") ||
      el.getAttribute("data-offline-video") || "";
    return normalizeAssetPath(src);
  }

  function isEligibleMedia(el) {
    if (!el || el.dataset.assetCornerDone) return false;
    if (el.closest("." + PANEL_CLASS)) return false;
    var tag = el.tagName;
    if (tag !== "IMG" && tag !== "VIDEO") return false;
    var path = assetPathFromElement(el);
    if (!path) return false;
    if (!el.closest(".main-content") &&
        !el.closest(".sqs-block-image") &&
        !el.closest(".menu-hub-aspect") &&
        path.indexOf("_media/") !== 0 &&
        path.indexOf("_cdn/") !== 0) {
      return false;
    }
    return true;
  }

  function findAnchor(media) {
    var shaped = media.closest(".has-aspect-ratio, .menu-hub-aspect, .image-block-wrapper, .section-pin-link");
    if (shaped) return shaped;
    var parent = media.parentElement;
    if (parent && parent.classList.contains(ANCHOR_CLASS)) return parent;
    var wrap = document.createElement("span");
    wrap.className = ANCHOR_CLASS;
    media.parentNode.insertBefore(wrap, media);
    wrap.appendChild(media);
    return wrap;
  }

  function row(label, value, copyValue, extraClass) {
    var div = document.createElement("div");
    div.className = "ac-row" + (extraClass ? " " + extraClass : "");
    if (copyValue != null) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.innerHTML = '<span class="ac-label">' + label + "</span> " + value;
      btn.title = "Click to copy";
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        copyText(copyValue).then(function () {
          btn.classList.add("ac-copied");
          var prev = btn.innerHTML;
          btn.innerHTML = '<span class="ac-label">copied</span>';
          setTimeout(function () {
            btn.innerHTML = prev;
            btn.classList.remove("ac-copied");
          }, COPIED_MS);
        });
      });
      div.appendChild(btn);
    } else {
      div.innerHTML = '<span class="ac-label">' + label + "</span> " + value;
    }
    return div;
  }

  function setDupRow(panel, path) {
    var dup = panel.querySelector(".ac-dup");
    var count = pageCounts[path] || 0;
    if (count <= 1) {
      if (dup) dup.remove();
      return;
    }
    var text = "\u00d7" + count + " on page";
    if (!dup) {
      dup = document.createElement("div");
      dup.className = "ac-row ac-dup";
      panel.appendChild(dup);
    }
    dup.innerHTML = '<span class="ac-label">use</span> <span class="ac-dup">' + text + "</span>";
  }

  function loadFileMeta(panel, path) {
    var sizeRow = panel.querySelector(".ac-size");
    fetch(INFO_API + "?path=" + encodeURIComponent(path))
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data || !sizeRow) return;
        sizeRow.innerHTML = '<span class="ac-label">size</span> ' + formatBytes(data.size);
        if (data.name && data.name !== path.split("/").pop()) {
          var fileRow = panel.querySelector(".ac-file");
          if (fileRow) {
            fileRow.querySelector("button").innerHTML =
              '<span class="ac-label">file</span> ' + data.name;
          }
        }
      })
      .catch(function () { /* ignore */ });
  }

  function loadDimensions(panel, media) {
    var dimRow = panel.querySelector(".ac-dims");
    if (!dimRow) return;
    function apply() {
      var w = media.naturalWidth || media.videoWidth || 0;
      var h = media.naturalHeight || media.videoHeight || 0;
      if (w && h) {
        dimRow.innerHTML = '<span class="ac-label">dims</span> ' + w + "\u00d7" + h;
      }
    }
    if (media.tagName === "VIDEO") {
      if (media.readyState >= 1) apply();
      else media.addEventListener("loadedmetadata", apply, { once: true });
    } else {
      if (media.complete && media.naturalWidth) apply();
      else media.addEventListener("load", apply, { once: true });
    }
  }

  function buildPanel(media, path) {
    var name = path.split("/").pop();
    var panel = document.createElement("div");
    panel.className = PANEL_CLASS;
    panel.dataset.assetPath = path;
    panel.appendChild(row("id", path, path));
    panel.appendChild(row("file", name, name, "ac-file"));
    panel.appendChild(row("size", "\u2026", null, "ac-size"));
    panel.appendChild(row("dims", "\u2026", null, "ac-dims"));
    setDupRow(panel, path);
    loadFileMeta(panel, path);
    loadDimensions(panel, media);
    return panel;
  }

  function rebuildCounts() {
    pageCounts = Object.create(null);
    var done = document.querySelectorAll("[data-asset-corner-done]");
    for (var i = 0; i < done.length; i++) {
      var p = assetPathFromElement(done[i]);
      if (p) pageCounts[p] = (pageCounts[p] || 0) + 1;
    }
  }

  function decorateMedia(media) {
    if (!isEligibleMedia(media)) return;
    var path = assetPathFromElement(media);
    if (!path) return;
    media.dataset.assetCornerDone = "1";
    var anchor = findAnchor(media);
    if (anchor.querySelector("." + PANEL_CLASS)) return;
    if (window.getComputedStyle(anchor).position === "static") {
      anchor.style.position = "relative";
    }
    anchor.appendChild(buildPanel(media, path));
  }

  function refreshDuplicateRows() {
    var panels = document.querySelectorAll("." + PANEL_CLASS);
    for (var i = 0; i < panels.length; i++) {
      var p = panels[i].dataset.assetPath;
      if (p) setDupRow(panels[i], p);
    }
  }

  function scan(root) {
    var scope = root || document;
    var nodes = scope.querySelectorAll
      ? scope.querySelectorAll(
        ".main-content img[src], .main-content video[src], " +
        ".sqs-block-image img[src], .menu-hub-aspect img[src], " +
        "img[src*=\"_media/\"], img[src*=\"_cdn/\"], " +
        "video[src*=\"_media/\"], video[src*=\"_cdn/\"]"
      )
      : [];
    for (var i = 0; i < nodes.length; i++) decorateMedia(nodes[i]);
    rebuildCounts();
    refreshDuplicateRows();
  }

  function boot() {
    scan(document);
    var obs = new MutationObserver(function (mutations) {
      var touched = false;
      for (var i = 0; i < mutations.length; i++) {
        var m = mutations[i];
        for (var j = 0; j < m.addedNodes.length; j++) {
          var node = m.addedNodes[j];
          if (node.nodeType !== 1) continue;
          if (node.tagName === "IMG" || node.tagName === "VIDEO") {
            decorateMedia(node);
            touched = true;
          } else {
            scan(node);
            touched = true;
          }
        }
      }
      if (touched) refreshDuplicateRows();
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
