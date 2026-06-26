# senzhang.me master plan (v1 static)

**Active repo:** senzhang-personal-website-v1
**Preview:** https://senzhang-personal-website-v1.vercel.app
**Vercel team:** zsen-idea-house (personal; NOT ennead-projects)
**Keystone todo:** #1683

## Deploy policy

| When | How |
|------|-----|
| Day-to-day dev / S2.5 review | `py -3 scripts\serve.py` (local only) |
| Portfolio curation | http://127.0.0.1:8765/dashboard (auto-save; not on Vercel) |
| Preview deploy (rare) | `.\scripts\deploy-vercel.ps1` (no -Prod) |
| **Milestone prod** | `.\scripts\deploy-vercel.ps1 -Prod -Milestone <label>` |

Prod milestones: `P1-port`, `S2.5`, `P2`, `DNS`, `cache-final` (#1680).

Do not prod-deploy on every commit.

## P1 status (done)

- Resume, PRO, code, speaking, nav fix, `/code` + `/speaking` indexes
- Section masonry grids (academic / professional / code / speaking)
- `data/projects.json` registry + local dashboard (visibility, order, highlights, resume flags, thumbnails)
- Slug fixes: `block-field` (not `zen-house-1`), EnneadTab → single `enneadtab-ecosystem`
- Austin 2026 talk: `acd-austin-2026` (Advancing Computational Design Conference)
- Latest commit on `main`: `36ab9d5` (masonry stagger; prod still `a9a2791` until P2 milestone)

## S2.5 prod deploy (2026-06-21)

- Milestone: `.\scripts\deploy-vercel.ps1 -Prod -Milestone S2.5`
- Production alias: https://senzhang-personal-website-v1.vercel.app
- Deployment: `4thMmSbRP6f7auMvuWeJCbVn2SMs` (build_id `a9a2791`)
- Fix: `port-about-resume.py` idempotent when about-me layout already current (unblocks deploy pipeline)

**Automated prod smoke (2026-06-21):**

| Route | Status |
|-------|--------|
| `/academic`, `/professional`, `/code`, `/speaking` | 200 |
| `/block-field`, `/code/enneadtab-ecosystem` | 200 |
| `/speaking/acd-austin-2026`, `/about-me` | 200 |
| `/dashboard` | 404 (local only) |

## S2.5 sign-off — **done 2026-06-26** (#1683)

| Tab | URL |
|-----|-----|
| A (legacy reference) | https://legacy-personal-website.vercel.app |
| B/C (v1 prod) | https://senzhang-personal-website-v1.vercel.app |

**Checklist** (side-by-side vs legacy) — all signed off:

- [x] `/` cover + video
- [x] `/menu` hub tiles
- [x] `/academic` masonry (order + highlights)
- [x] `/professional`, `/code`, `/speaking`
- [x] `/block-field`, `/about-me` (resume + featured portfolio)
- [x] `/speaking/acd-austin-2026`
- [x] `/dashboard` → 404 on prod (local only)
- [x] Sign off #1683 — **"signoff ok"**

Sign-off date also recorded in `docs/plans/recruiter-content-floor-matrix.md`.

## P2 (unblocked)

**Status:** S2.5 signed off; curation work can proceed via local dashboard. Prod deploy when ready:

```powershell
.\scripts\deploy-vercel.ps1 -Prod -Milestone P2
```

**Bundle for P2 prod milestone** (commits/features on `main` not yet on prod `a9a2791`):

| Item | Detail |
|------|--------|
| Masonry stagger | `36ab9d5` — highlighted pins span two grid columns (`pin-highlight-left` / `pin-highlight-right`) |
| Registry curation | `data/projects.json` — P2 hide candidates hidden; P0/P1 re-shown per recruiter matrix; resume flags tuned |
| `acd-austin-2026` cover | Typographic cover via `scripts/gen-speaking-cover.py` (was AU 2024 placeholder) |
| Script fix | `restructure-menu-sections.py` highlight count no longer double-counts stagger classes |
| **Not in P2** | `vercel.final.json` / DNS cutover (#1680) — separate milestone |
