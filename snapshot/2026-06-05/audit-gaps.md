# Audit gaps — 2026-06-05

**Offline pass:** YES (local HTML assets + zero YouTube embed refs)

## Metrics that matter

| Check | Count | Meaning |
|-------|------:|---------|
| Local HTML missing assets | 0 | Mirrorable URLs in snapshot HTML not on disk — **must be 0** |
| YouTube embed refs (local) | 0 | Runtime YouTube iframes left in HTML — **must be 0** |
| Real missing manifest files | 6 | Manifest keys with no file; only count if referenced in HTML |

## Informational (not offline blockers)

| Check | Count | Meaning |
|-------|------:|---------|
| Live HTML CDN drift | 23 | Live Squarespace bundle hashes newer than snapshot |
| Manifest phantom entries | 42 | Regex false-positives (`h1`, `blockquote`, etc.) — ignore |
| Download errors (manifest) | 48 | Mostly phantom URLs from inline JS |

## Deprecated counter (do not use)

`missing_mirrorable_refs_page_occurrences` = **661** — same URL counted once per page;
not unique missing files. Use `truly_missing_assets_local_html` instead.

Machine-readable details: `audit-report.json`.

## Sample real manifest orphans

- `https://static1.squarespace.com/static/58949e5a3e00bef5fa228481/593fec7637c58186` → `_cdn/static1.squarespace.com/6b864fd278a7bc802d39.jpg`
- `https://static1.squarespace.com/static/58949e5a3e00bef5fa228481/593fec7637c58186` → `_cdn/static1.squarespace.com/02a2257d6e10930c7e14.jpg`
- `https://static1.squarespace.com/static/58949e5a3e00bef5fa228481/593fec7637c58186` → `_cdn/static1.squarespace.com/1567e6233a7d2b1fdf6c.jpg`
- `https://static1.squarespace.com/static/58949e5a3e00bef5fa228481/593fee2da5790aad` → `_cdn/static1.squarespace.com/c8d7db6ed07ba23685ae.jpg`
- `https://static1.squarespace.com/static/58949e5a3e00bef5fa228481/593fee2da5790aad` → `_cdn/static1.squarespace.com/7b8eef87a9201dc06e1b.jpg`
- `https://static1.squarespace.com/static/ta/4f9adbe124ac5df956fdf900/869/scripts/` → `_cdn/static1.squarespace.com/290cc65233fda796c37b`
