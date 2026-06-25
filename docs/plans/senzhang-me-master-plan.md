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
- Latest commit on `main`: `a9a2791`

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

## S2.5 sign-off (blocks P2)

| Tab | URL |
|-----|-----|
| A (legacy reference) | https://legacy-personal-website.vercel.app |
| B/C (v1 prod) | https://senzhang-personal-website-v1.vercel.app |

**Your checklist** (side-by-side vs legacy):

- [ ] `/` cover + video
- [ ] `/menu` hub tiles
- [ ] `/academic` masonry (order + highlights)
- [ ] `/professional`, `/code`, `/speaking`
- [ ] `/block-field`, `/about-me` (resume + featured portfolio)
- [ ] `/speaking/acd-austin-2026`
- [ ] `/dashboard` → 404 on prod (local only)
- [ ] Sign off #1683

After sign-off: note date in `docs/plans/recruiter-content-floor-matrix.md` → **P2** curation via dashboard.

## P2 (after S2.5)

- Hide polish-tier projects via dashboard `visible: false`
- Tune highlights + resume flags
- Optional: real cover for `acd-austin-2026`, replace placeholder JPG
- `vercel.final.json` / DNS cutover (#1680) — not yet
