# Three-way QA workflow

Use three URLs while closing gaps between the live site and the archived copy.

| Layer | URL | Role |
|-------|-----|------|
| **Live** | https://senzhang.me | Original Squarespace — ground truth for behavior and content |
| **Deployed archive** | https://legacy-personal-website.vercel.app | What is actually published from this repo (last manual deploy) |
| **Local** | http://127.0.0.1:8765/ | Fast iteration — picks up file edits on refresh, no Vercel cost |

## Daily loop

1. **Start local server** (one terminal, leave it running):
   ```powershell
   cd C:\Users\szhang\github\Personal\senzhang-legacy-website-archive
   .\scripts\serve.ps1
   ```
   `serve.ps1` stops stale `serve.py` processes on port 8765 before starting (avoids `ERR_EMPTY_RESPONSE` from zombie listeners).

2. **Open the same page in three tabs** (example: Museum of Verbs):
   ```powershell
   .\scripts\qa-urls.ps1 -Page museum-of-verbs
   ```
   Prints Live, Vercel, and Local URLs for any page stem.

3. **You report gaps** (e.g. broken thumbs, missing blur, wrong video). Compare:
   - Live vs **Vercel** → what the last deploy is missing (archive truth on the web)
   - Live vs **Local** → whether a fix in the repo works before deploy

4. **Agent applies fix** under `snapshot/2026-06-05/` (HTML/CSS/scripts). **No server restart.** Hard-refresh Local (`Ctrl+Shift+R`) to verify.

5. **git push** = backup/sync only. **Does not update Vercel prod.**

6. **When you sign off** on the full gap list:
   ```powershell
   .\scripts\deploy-vercel.ps1 -Prod
   ```
   One ~1.7 GB upload; then Vercel should match Local.

## Cache modes (Phase 2 vs after sign-off)

| Mode | When | HTML / pages | `_cdn` / `_media` | Cost |
|------|------|--------------|-------------------|------|
| **QA** (default now) | Active gap-fixing | `no-cache` (always fresh) | `immutable` + `?v=<git-sha>` on each deploy | Higher edge revalidation |
| **Final** | Archive frozen after Task 2 | `immutable` 1y | `immutable` 1y | Lower bandwidth / CDN cost |

Templates: `vercel.qa.json`, `vercel.final.json` (active file: `vercel.json`).

**Phase 2 deploy** (while still fixing):
```powershell
.\scripts\deploy-vercel.ps1 -Prod
# same as -CacheMode QA
```

**After sign-off** (switch once, commit, deploy):
```powershell
.\scripts\set-vercel-cache-mode.ps1 -Mode Final
git add vercel.json
git commit -m "Switch Vercel to immutable cache after archive sign-off."
.\scripts\deploy-vercel.ps1 -Prod -CacheMode Final
git push
```

To go back to QA mode during fixes:
```powershell
.\scripts\set-vercel-cache-mode.ps1 -Mode QA
```

Verify deploy build: https://legacy-personal-website.vercel.app/archive-version.json

## What local picks up automatically

| Change | Restart server? |
|--------|-----------------|
| Edit HTML under `snapshot/` | No — refresh browser |
| Run a fix script (`fix-lazy-images.py`, etc.) | No — refresh browser |
| New snapshot folder / switch date | Yes — restart with `-Date YYYY-MM-DD` |
| Port broken / empty response | Yes — `Ctrl+C` then `.\scripts\serve.ps1` (auto-cleans stale PIDs) |

## Page URL cheat sheet

| Live path | Local / Vercel file |
|-----------|---------------------|
| `/` | `index.html` |
| `/menu` | `menu.html` |
| `/museum-of-verbs` | `museum-of-verbs.html` |
| `/works` | `works.html` |

Local and Vercel use the same filenames; Live uses Squarespace paths without `.html`.

## Roles summary

- **Live** — what we are preserving.
- **Vercel** — ultimate deployed archive truth until the next `-Prod` deploy.
- **Local** — cheap proof that fixes work before spending a deploy.
