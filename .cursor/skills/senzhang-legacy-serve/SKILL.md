---
name: senzhang-legacy-serve
description: >-
  Serve the archived senzhang.me legacy website locally from this repo's
  snapshot folder. Use when the user wants to preview, browse, or open the
  offline archive, start the local dev server, view the legacy portfolio site,
  A/B compare live vs Vercel vs local fixes, or says "show me the website",
  "serve locally", "start website", or "preview senzhang.me archive".
---
# Serve senzhang.me legacy archive locally

## Three-way QA (user workflow)

| Layer | URL | Purpose |
|-------|-----|---------|
| Live | https://senzhang.me | Squarespace original |
| Deployed | https://legacy-personal-website.vercel.app | Archive truth on the web (last prod deploy) |
| Local | http://127.0.0.1:8765/ | Verify fixes cheaply before `-Prod` deploy |

Full loop: `docs/qa-workflow.md`. Print URLs for a page: `.\scripts\qa-urls.ps1 -Page museum-of-verbs`.

**After fixing snapshot files:** user hard-refreshes Local only. Do **not** redeploy Vercel unless the user explicitly asks.

## Quick start

From repo root (`senzhang-legacy-website-archive`):

```powershell
.\scripts\serve.ps1
```

Opens **http://127.0.0.1:8765/index.html** in the default browser. Stale `serve.py` on port 8765 is stopped first (prevents `ERR_EMPTY_RESPONSE`).

## Options

```powershell
.\scripts\serve.ps1 -Date 2026-06-05    # specific snapshot
.\scripts\serve.ps1 -Port 9000          # custom port
.\scripts\serve.ps1 -NoOpen              # server only, no browser
.\scripts\serve.ps1 -NoCleanStale        # do not kill existing serve.py on port
```

Squarespace analytics POSTs (`/api/census/*`) are stubbed as `200 {}` so the terminal does not spam `501 Unsupported method ('POST')`.

```powershell
py -3 scripts\serve.py --quiet-api      # hide stubbed /api/ log lines
```

Direct Python:

```powershell
py -3 scripts\serve.py --date 2026-06-05 --port 8765 --no-open
```

## Agent workflow

1. Confirm `snapshot/<date>/index.html` exists (run `git lfs pull` if HTML is missing after clone).
2. Apply fixes under `snapshot/2026-06-05/` (scripts or HTML). **No server restart** — user refreshes browser.
3. If local server is down or returns empty response, start in background:
   ```powershell
   .\scripts\serve.ps1 -NoOpen
   ```
   Prefer `serve.ps1` over raw `serve.py` so stale PIDs on 8765 are cleaned.
4. Tell the user to hard-refresh Local and keep comparing Live + Vercel for remaining gaps.
5. `git push` for backup only. **Never** run `deploy-vercel.ps1 -Prod` unless the user explicitly requests prod publish.

## Vercel production

Do **not** run `deploy-vercel.ps1 -Prod` unless the user explicitly asks to publish. `git push` is backup/sync; prod deploy uploads ~1.7 GB. Use local `serve.ps1` for all fix verification.

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
| `scripts/qa-urls.ps1` | Print Live / Vercel / Local URLs for one page |
| `scripts/serve.ps1` | Local preview (cleans stale listeners) |
| `scripts/snapshot.ps1` | Create a new dated mirror from live senzhang.me |
| `scripts/verify-snapshot.ps1` | Check snapshot vs live sitemap |
| `scripts/deploy-vercel.ps1 -Prod` | Publish to Vercel (user request only) |
