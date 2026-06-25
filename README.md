> **ACTIVE senzhang.me line (v1).** Static HTML bootstrapped from legacy archive 2026-06-05 snapshot.
> Preview: https://senzhang-personal-website-v1.vercel.app
> Master plan: docs/plans/senzhang-me-master-plan.md | Keystone todo: #1683
> **FROZEN REFERENCE (2026-06-21).** Do **not** edit `snapshot/` or re-scrape live Squarespace. Reference-only for [senzhang-personal-website](https://github.com/zsenarchitect/senzhang-personal-website) migration — see `docs/plans/2026-06-21-recruiter-hiring-portfolio-plan.md` in that repo. **`snapshot.ps1` / live crawl:** emergency preservation only; routine work uses committed snapshot **2026-06-05** and https://legacy-personal-website.vercel.app. **GitHub repo archived** — unarchive briefly only for an explicit signed-off change (e.g. todo **#1680** Vercel cache Final after #1101 cutover).

# senzhang-legacy-website-archive

A **1:1 offline snapshot** of [senzhang.me](https://senzhang.me) â€” a Squarespace portfolio site â€” preserved so the full legacy website remains available after Squarespace is discontinued.

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
# Browse the archived site locally (opens browser)
.\scripts\serve.ps1

# Create a new snapshot from live senzhang.me
.\scripts\snapshot.ps1

# Verify against live sitemap
.\scripts\verify-snapshot.ps1
```

Local preview URL: **http://127.0.0.1:8765/index.html** (serves latest `snapshot/<date>/`).

## Requirements

- **Python 3** (stdlib only â€” no pip packages)
- PowerShell 5.1+
- Optional: **HTTrack** for alternative mirror via `.\scripts\snapshot.ps1 -UseHtTrack`

## How it works

`snapshot.py` (via `snapshot.ps1`):

1. Reads `sitemap.xml` for all ~30 portfolio pages and image URLs
2. Crawls each page HTML for linked assets (Squarespace CDN, fonts, platform JS/CSS)
3. Downloads everything into `snapshot/<date>/` with CDN files under `_cdn/`
4. Rewrites HTML links for offline browsing
5. Writes `manifest.json` with file counts, sizes, crawl settings, and any download errors

### Safer crawling (configurable)

Politeness is controlled by `scripts/crawl-config.json` (default **safe** profile):

| Profile | Page pause | Asset pause | Retries | Notes |
|---------|------------|-------------|---------|-------|
| **safe** (default) | ~1.25s + jitter | ~0.85s + jitter | 4 | Sequential, min 0.5s between requests |
| **normal** | ~0.5s + jitter | ~0.25s + jitter | 3 | Moderate |
| **fast** | ~0.2s + jitter | ~0.15s + jitter | 2 | Old behavior; use only if you own the site |

Features: exponential backoff on 429/5xx, honors `Retry-After`, descriptive User-Agent, no parallel downloads.

```powershell
# Default safe crawl
.\scripts\snapshot.ps1

# Faster re-run on your own site
.\scripts\snapshot.ps1 -Profile normal

# Custom delays
py -3 scripts\snapshot.py --profile safe --page-delay 2 --asset-delay 1.5

# Custom config file
.\scripts\snapshot.ps1 -Config .\my-crawl-config.json
```

Repair and audit scripts use the same config (`repair-html.ps1 -Profile safe`, `audit-completeness.py --profile safe`).

### Offline fixes (fonts + cover video)

```powershell
.\scripts\fix-offline-fonts.ps1    # Google TTFs + Typekit woff2 -> local _cdn/
.\scripts\fix-cover-video.ps1      # YouTube cover -> _media/cover-background.mp4
.\scripts\apply-cover-effects.py   # Match Squarespace blur/filter + playback speed offline
.\scripts\fix-offline-videos.ps1   # Project YouTube embeds -> _media/*.mp4
.\scripts\fix-hydration-dom.py     # Move offline videos out of React-managed wrappers
.\scripts\fix-missing-assets.py    # Download manifest CDN files missing on disk
```

Requires `yt-dlp` for cover video (`py -3 -m pip install yt-dlp`).

### Live deployment (Vercel)

Static site deploys from `snapshot/2026-06-05/` via `vercel.json`.

#### Production priority (P0 reference site)

**https://legacy-personal-website.vercel.app** is the S2.5 Tab A reference for migration sign-off. It must stay fully functional (images, JS, CSS, `_media` mp4, navigation).

| Rule | Why |
|------|-----|
| **Never git-push deploy** | Git-triggered builds can upload Git LFS pointer stubs (~130 bytes) instead of real binaries |
| **Always CLI deploy** | `.\scripts\deploy-vercel.ps1 -Prod` uploads the local smudged tree (~1.7 GB) |
| **LFS before deploy** | `git lfs pull` then `.\scripts\verify-cdn-assets.ps1` (must pass) |
| **Verify after deploy** | `py -3 scripts\verify-prod-assets.py` — CDN, `_media` mp4, key pages |
| **Git auto-deploy off** | `vercel.json` sets `"git": { "deploymentEnabled": false }` — prod changes only via CLI |

**Three-way QA** (see `docs/qa-workflow.md`):

| Layer | URL |
|-------|-----|
| Live (Squarespace) | https://senzhang.me |
| Deployed archive | https://legacy-personal-website.vercel.app |
| Local fixes | http://127.0.0.1:8765/ (refresh after edits â€” no Vercel cost) |

```powershell
.\scripts\serve.ps1                              # local server (auto-cleans stale port 8765)
.\scripts\qa-urls.ps1 -Page museum-of-verbs      # same page, three URLs
```

**Policy (cost):** `git push` does **not** update production. Redeploy only when you explicitly sign off â€” each prod deploy uploads ~1.7 GB. Fix and verify on **Local** while you send gap lists; use **Vercel** as deployed archive truth until the next `-Prod`.

When ready to publish snapshot changes to the web:

```powershell
.\scripts\deploy-vercel.ps1 -Prod          # Phase 2: QA cache (HTML no-cache)
```

After archive sign-off (lower CDN cost, immutable everything):

```powershell
.\scripts\set-vercel-cache-mode.ps1 -Mode Final
.\scripts\deploy-vercel.ps1 -Prod -CacheMode Final
```

See `docs/qa-workflow.md` and `vercel.qa.json` / `vercel.final.json`.

**Production (last manual deploy):** https://legacy-personal-website.vercel.app

### Broken images / unstyled pages on Vercel

Snapshot `_cdn/` and `_media/` binaries are stored in **Git LFS**. If Vercel deploys LFS **pointer stubs** (~130 bytes) instead of real files, pages return HTTP 200 but images/CSS/JS fail to render (common after a Git-triggered deploy without LFS enabled).

**Symptoms:** blank or unstyled pages; Network tab shows `_cdn/...jpg` at ~130 bytes starting with `version https://git-lfs.github.com/spec/v1`.

**Fix (preferred):** redeploy from a machine with smudged LFS files:

```powershell
git lfs pull
.\scripts\verify-cdn-assets.ps1          # must pass before deploy
.\scripts\deploy-vercel.ps1 -Prod        # CLI upload (~1.7 GB); uploads real binaries
py -3 scripts\verify-prod-assets.py      # post-deploy smoke test
```

**Git-triggered deploys:** `vercel.qa.json` / `vercel.final.json` include `git lfs pull` for documentation, but **auto-deploy is disabled** (`git.deploymentEnabled: false`). Use CLI deploy only.

Typekit / Google Fonts console errors on the archive are expected offline limitations; they do not block images.

## Risk register (2026-06-21)

Ranked gaps in the **same class** as LFS pointer deploys, cache drift, and broken asset URLs.

| Priority | Gap | Mitigation |
|----------|-----|------------|
| **P0** | Git-triggered Vercel deploy uploads LFS pointer stubs (~130 B) | `git.deploymentEnabled: false`; **CLI-only** `deploy-vercel.ps1 -Prod` after `git lfs pull` + `verify-cdn-assets.ps1` |
| **P0** | Emergency prod broken (unstyled / no images) | `verify-prod-assets.py` after every prod deploy; redeploy from smudged tree |
| **P1** | `_media` cover video not probed pre-deploy | `cover-background.mp4` in `verify-cdn-assets.ps1` + `verify-prod-assets.py` |
| **P1** | GitHub repo **archived** blocks push without unarchive | Unarchive briefly, push, re-archive; CLI deploy does not need git push |
| **P1** | Live `definitions.sqspcdn.com` URLs in HTML (spacer/video/code blocks) | Still load from Squarespace CDN at runtime; mirror locally before Squarespace cancel (#19) |
| **P1** | `vercel.json` drifts from `vercel.qa.json` / `vercel.final.json` | `deploy-vercel.ps1` copies template; `set-vercel-cache-mode.ps1` for permanent switch; commit after #1680 Final |
| **P1** | ~1.7 GB CLI upload every prod deploy | Deploy only on sign-off; iterate on `serve.ps1` local; Final cache mode after cutover |
| **P2** | `stamp-cache-version.py` skips inline `style="background:url(_cdn/...)"` | Low impact (QA no-cache HTML); extend regex if needed |
| **P2** | Duplicate snapshot pages (`zen-house` / `zen-house-1`, etc.) | cleanUrls serves both; harmless |
| **P2** | Live HTML CDN hash drift (23 bundles) | Informational; snapshot is frozen reference |
| **P2** | No service worker | None present — no stale SW risk |
| **P2** | `preconnect` to live `images.squarespace-cdn.com` | Harmless DNS hint; assets served from `_cdn/` |

## First snapshot (2026-06-05)

| Metric | Value |
|--------|-------|
| Pages (sitemap) | 30 |
| Files downloaded | 2,646 |
| Total size | ~1.7 GB |
| Download errors | 48 (mostly regex false-positives from inline JS, not real pages) |
| Verification | All 30 sitemap pages present locally |

## Storage note

Each full snapshot is **~1.5â€“2 GB**. Use **Git LFS** before pushing snapshots (see `.gitattributes`). Alternatively keep snapshots on disk / cloud storage and commit only `scripts/` + `manifest.json` summaries.

## Re-snapshot before Squarespace shutdown

Run a fresh snapshot periodically (especially right before canceling Squarespace):

```powershell
.\scripts\snapshot.ps1
git add snapshot/
git commit -m "Snapshot senzhang.me $(Get-Date -Format yyyy-MM-dd)"
git push
```

## Browsing offline

```powershell
.\scripts\serve.ps1
```

Opens **http://127.0.0.1:8765/index.html** (latest snapshot). Internal navigation works fully offline, including embedded videos in `_media/`.

If pages look blank or broken after a snapshot, run `.\scripts\repair-html.ps1` then restart the server.

**Cursor skill:** `.cursor/skills/senzhang-legacy-serve/SKILL.md` â€” agents use this to start the local preview.

## Repository layout

```
senzhang-legacy-website-archive/
â”œâ”€â”€ README.md
â”œâ”€â”€ .cursor/skills/senzhang-legacy-serve/
â”œâ”€â”€ scripts/
â”‚   â”œâ”€â”€ serve.ps1           # Local preview server
â”‚   â”œâ”€â”€ snapshot.ps1        # Create a dated mirror
â”‚   â”œâ”€â”€ crawl-config.json   # Default polite crawl settings (safe profile)
â”‚   â”œâ”€â”€ crawl_config.py     # Shared fetch/retry/delay logic
â”‚   â”œâ”€â”€ repair-html.ps1     # Re-fetch HTML + sync CDN assets
â”‚   â”œâ”€â”€ fix-offline-fonts.ps1
â”‚   â”œâ”€â”€ fix-cover-video.ps1
â”‚   â”œâ”€â”€ fix-offline-videos.ps1
â”‚   â”œâ”€â”€ fix-missing-assets.py
â”‚   â”œâ”€â”€ fix-lazy-images.py  # Slideshow thumbs: data-src -> src
â”‚   â”œâ”€â”€ audit-completeness.py
â”‚   â”œâ”€â”€ qa-urls.ps1         # Live / Vercel / Local URLs for one page
â”‚   â”œâ”€â”€ deploy-vercel.ps1   # Deploy snapshot to Vercel
â”‚   â””â”€â”€ verify-snapshot.ps1 # Compare snapshot vs live sitemap
â””â”€â”€ snapshot/
    â””â”€â”€ YYYY-MM-DD/         # Dated snapshots (committed to git)
        â”œâ”€â”€ manifest.json
        â”œâ”€â”€ index.html      # Homepage
        â””â”€â”€ _cdn/           # Mirrored CDN assets
```

## License / rights

Content is Sen Zhang's personal portfolio. This repo is a private preservation copy, not a public re-hosting.

