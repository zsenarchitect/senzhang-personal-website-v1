---
name: senzhang-legacy-serve
description: >-
  Serve the archived senzhang.me legacy website locally from this repo's
  snapshot folder. Use when the user wants to preview, browse, or open the
  offline archive, start the local dev server, view the legacy portfolio site,
  or says "show me the website", "serve locally", "start website", or
  "preview senzhang.me archive".
---
# Serve senzhang.me legacy archive locally

## Quick start

From repo root (`senzhang-legacy-website-archive`):

```powershell
.\scripts\serve.ps1
```

Opens **http://127.0.0.1:8765/index.html** in the default browser.

## Options

```powershell
.\scripts\serve.ps1 -Date 2026-06-05    # specific snapshot
.\scripts\serve.ps1 -Port 9000          # custom port
.\scripts\serve.ps1 -NoOpen              # server only, no browser
```

Squarespace analytics POSTs (`/api/census/*`) are stubbed as `200 {}` so the terminal does not spam `501 Unsupported method ('POST')`.

```powershell
py -3 scripts\serve.py --quiet-api      # hide stubbed /api/ log lines
```

Direct Python:

```powershell
py -3 scripts\serve.py --date 2026-06-05 --port 8765
```

## Agent workflow

1. Confirm `snapshot/<date>/index.html` exists (run `git lfs pull` if HTML is missing after clone).
2. Start server **in background**:
   ```powershell
   py -3 scripts\serve.py --no-open
   ```
3. Open `http://127.0.0.1:8765/index.html` in the browser (MCP browser or `open_resource`).
4. Tell the user the URL and snapshot date being served.

## Vercel production

Do **not** run `deploy-vercel.ps1 -Prod` unless the user explicitly asks to publish. `git push` is enough for backup/sync; prod deploy uploads ~1.7 GB. Use local `serve.ps1` for QA.

## Snapshot selection

- Default: **latest** dated folder under `snapshot/` (sorted by folder name).
- Entry page: `index.html` (homepage mirror).
- Project pages: `cover-page.html`, `gravity-rises.html`, etc.

## Blank or broken page?

Re-fetch HTML from live site and sync new CDN assets (safe to re-run):

```powershell
.\scripts\repair-html.ps1
```

Then restart `serve.ps1` and hard-refresh the browser.

## Limitations

- YouTube embeds and some third-party widgets need internet.
- Squarespace JS may log console errors offline; pages and images should still render.
- Stop server with Ctrl+C in the terminal running `serve.ps1`.

## Related scripts

| Script | Purpose |
|--------|---------|
| `scripts/snapshot.ps1` | Create a new dated mirror from live senzhang.me |
| `scripts/verify-snapshot.ps1` | Check snapshot vs live sitemap |
