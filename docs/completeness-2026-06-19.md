# Legacy archive completeness report — 2026-06-19

Task 1 verification for [senzhang-legacy-website-archive](..) snapshot `2026-06-05`.

## Automated results

| Check | Result |
|-------|--------|
| `verify-snapshot.ps1` | **30/30** sitemap pages present |
| `audit-completeness.py` | **PASS** (local HTML assets + zero YouTube embed refs) |
| Local HTML missing assets | **0** |
| YouTube embed refs in local HTML | **0** (videos served from `_media/`) |
| Live HTML CDN drift | **23** (Squarespace bundle hashes updated on live site since snapshot — informational only) |
| Legacy inflated counter | **661** page-occurrence mismatches (see README audit notes — not real gaps) |

## Offline video manifest

| Video ID | Local file | Patched pages |
|----------|------------|---------------|
| `mYPQl6m7kMY` | `_media/cover-background.mp4` | `index.html`, `cover-page.html`, `menu.html` |
| `fAl5EJuQpUM` | `_media/fAl5EJuQpUM.mp4` | `menu.html` |
| `4sQc0d3HRck` | `_media/4sQc0d3HRck.mp4` | `museum-of-verbs.html`, `works.html` |
| `3pFCHJNHKEU` | `_media/3pFCHJNHKEU.mp4` | `bank-of-15mins-fame.html` |

## Manifest orphan entries (non-blocking)

Six `url_to_local` keys point to files not on disk. None are referenced in local HTML:

- Five `static1.squarespace.com` plan JPGs return **404** on live CDN (dead URLs from original crawl).
- One `.../scripts/` directory URL (not a file; combo `site.js` exists separately).

No user-visible impact expected.

## Production deploy

**https://legacy-personal-website.vercel.app** — updated only via manual `.\scripts\deploy-vercel.ps1 -Prod` (not on every git push; saves upload cost).

Latest snapshot fixes (blur, hydration, offline video) are in git `main`; redeploy when you sign off Task 1.

Deployment inspect (after a deploy): `vercel inspect legacy-personal-website-n0rome6fr-zsen-dump-yard.vercel.app`

---

## Your side-by-side review (action required)

Open both in separate tabs:

| | URL |
|--|-----|
| **Live Squarespace** | https://senzhang.me |
| **Legacy archive** | https://legacy-personal-website.vercel.app |

Suggested walkthrough:

1. Homepage / cover video
2. `about-me` + resume PDF link
3. `works` or project index
4. `menu` (2 videos)
5. `museum-of-verbs`, `bank-of-15mins-fame`
6. 2–3 additional projects you care about

Send a list of **missing / incorrect** items (page URL, what’s wrong, screenshot optional). We will triage each as:

- **Fix now** — repair script, re-download, re-patch
- **Accept** — intentional offline limitation
- **Defer** — document only

Task 1 sign-off and Task 2 (new personal site) start after your review.

---

## Domain migration (post sign-off)

| Item | Plan |
|------|------|
| `senzhang.me` DNS | Point to Vercel when new personal site is ready (registrar transfer TBD in Task 2) |
| Squarespace website | Set **Private** after DNS cutover; cancel at **website renewal** (prepaid annual) |
| Domain renewal | `senzhang.me` at Squarespace Domains through **Feb 3, 2027** |
| Long-term archive | This git repo + Vercel legacy deploy (not Squarespace after cancel) |
