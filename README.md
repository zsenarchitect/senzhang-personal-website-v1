# senzhang-legacy-website-archive

A **1:1 offline snapshot** of [senzhang.me](https://senzhang.me) — a Squarespace portfolio site — preserved so the full legacy website remains available after Squarespace is discontinued.

## What this archive contains

| Layer | Source | Notes |
|-------|--------|-------|
| HTML pages | `senzhang.me` | ~30 portfolio/project pages from sitemap |
| Images & media | `static1.squarespace.com`, `images.squarespace-cdn.com` | Project photos, diagrams, favicon |
| Platform assets | `assets.squarespace.com` | Squarespace JS/CSS bundles |
| Fonts | `fonts.googleapis.com`, `fonts.gstatic.com`, Typekit | Typography used on the live site |
| Embedded media | YouTube, etc. | Linked externally; not fully offline |

Snapshots are stored under `snapshot/<YYYY-MM-DD>/` with a `manifest.json` recording page count, asset count, and snapshot date.

## Quick start

```powershell
# From repo root — creates snapshot/<today>/
.\scripts\snapshot.ps1

# Verify against live sitemap
.\scripts\verify-snapshot.ps1
```

## Requirements

- **Python 3** (stdlib only — no pip packages)
- PowerShell 5.1+
- Optional: **HTTrack** for alternative mirror via `.\scripts\snapshot.ps1 -UseHtTrack`

## How it works

`snapshot.py` (via `snapshot.ps1`):

1. Reads `sitemap.xml` for all ~30 portfolio pages and image URLs
2. Crawls each page HTML for linked assets (Squarespace CDN, fonts, platform JS/CSS)
3. Downloads everything into `snapshot/<date>/` with CDN files under `_cdn/`
4. Rewrites HTML links for offline browsing
5. Writes `manifest.json` with file counts, sizes, and any download errors

After mirroring, the script copies the HTTrack output into `snapshot/<date>/`, writes `manifest.json`, and logs any sitemap URLs that were not captured.

## First snapshot (2026-06-05)

| Metric | Value |
|--------|-------|
| Pages (sitemap) | 30 |
| Files downloaded | 2,646 |
| Total size | ~1.7 GB |
| Download errors | 48 (mostly regex false-positives from inline JS, not real pages) |
| Verification | All 30 sitemap pages present locally |

## Storage note

Each full snapshot is **~1.5–2 GB**. Use **Git LFS** before pushing snapshots (see `.gitattributes`). Alternatively keep snapshots on disk / cloud storage and commit only `scripts/` + `manifest.json` summaries.

## Re-snapshot before Squarespace shutdown

Run a fresh snapshot periodically (especially right before canceling Squarespace):

```powershell
.\scripts\snapshot.ps1
git add snapshot/
git commit -m "Snapshot senzhang.me $(Get-Date -Format yyyy-MM-dd)"
git push
```

## Browsing offline

Open `snapshot/<date>/senzhang.me/index.html` in a browser. Internal navigation should work offline; YouTube embeds and any third-party widgets require internet.

## Repository layout

```
senzhang-legacy-website-archive/
├── README.md
├── scripts/
│   ├── snapshot.ps1       # Create a dated mirror
│   └── verify-snapshot.ps1 # Compare snapshot vs live sitemap
└── snapshot/
    └── YYYY-MM-DD/        # Dated snapshots (committed to git)
        ├── manifest.json
        └── senzhang.me/   # Mirrored site root
```

## License / rights

Content is Sen Zhang's personal portfolio. This repo is a private preservation copy, not a public re-hosting.
