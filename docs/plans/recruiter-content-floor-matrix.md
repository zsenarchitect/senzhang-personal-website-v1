# Recruiter content floor matrix â€” legacy archive â†’ new site

**Epic:** senzhang-todo **#1683** | **Sprint:** S1 | **Generated:** 2026-06-21  
**Sources:** [legacy manifest](https://github.com/zsenarchitect/senzhang-legacy-website-archive) snapshot 2026-06-05, [migration-check-all-2026-06-21.md](../../DEBUG/migration-check-all-2026-06-21.md)

## P1 visibility policy (all visible until S2.5 sign-off)

During Phase 1, **every architecture page is public** â€” grid, sidebar, and static routes show the full corpus. No `published: false` on architecture MDX. Recruiter curation / hiding is **Phase 2 only** (after P2-A spec approved).

| Phase | Grid / sidebar | Frontmatter hiding | S2.5 scope |
|-------|----------------|-------------------|------------|
| **P1 (now)** | `getAllArchitectureProjects()` â€” all ~31 slugs | **Forbidden** on architecture | Full legacy parity sign-off |
| **P2 (after sign-off)** | Filtered via `getListedArchitectureProjects()` + P2-A0 | `published: false` allowed per spec | Curated public subset |

## Asset policy

| Rule | Detail |
|------|--------|
| **Location** | `public/projects/<slug>/` â€” images, WebP variants, videos |
| **Git tracking** | All assets must be committed; P1 parity impossible without them |
| **Status (2026-06-21)** | **602 files** tracked in git under `public/projects/` (matches on-disk count) |
| **Hidden != delete** | `published: false` (P2 only) drops a slug from grid/sidebar; MDX + `public/projects/<slug>/` stay in repo and routes must still render |
| **Size target** | Ship **~100-250 MB** of per-project media in git, **not** the full ~1.7 GB legacy snapshot (vendor JS/CSS, `_cdn/` duplicates). Current tracked corpus: **~465 MB** (602 files) — acceptable for P1; trim duplicates over time |
| **Local clone fix** | If images 404 on localhost: `git pull origin main` then `git checkout HEAD -- public/projects/` (regular git blobs, not LFS) |
| **Covers** | PRO + grid covers optimized via `npm run optimize:covers` (#48 done) |

## Tier legend

| Tier | Meaning for S2.5 sign-off |
|------|---------------------------|
| **P0** | Must be reachable, visible in grid/sidebar, and not embarrassing |
| **P1** | Should fix content quality before sign-off; still **visible** â€” no hiding |
| **P2** | Polish / layout â€” visible during P1; hide candidates deferred to Phase 2 curation |
| **N/A** | Consolidated alias or nav-only; no separate route |

## Site-level routes

| Archive URL | New route | Tier | Migrate status | Notes |
|-------------|-----------|------|----------------|-------|
| `senzhang.me/` (cover-page) | `/` | **P0** | manual | Video + landing; browser sign-off |
| `senzhang.me/about-me` | `/about` | **P0** | manual | Resume + PDF download (#70) |
| â€” | `/code` | **P0** | partial | Grid + flagship links (#33); 11 code MDX |
| â€” | `/speaking` | **P0** | manual | 4 talk MDX |
| `senzhang.me/menu` | â€” | N/A | â€” | Squarespace nav shell; no content page |

## Architecture â€” archive sitemap (30 URLs â†’ 31 MDX slugs)

Squarespace duplicates consolidated to canonical new slugs. **All rows visible in P1 grid/sidebar.**

| Archive slug | New slug / route | Tier | Overall | P1 issue |
|--------------|------------------|------|---------|----------|
| cover-page | `/` | P0 | manual | â€” |
| about-me | `/about` | P0 | manual | â€” |
| menu | N/A | N/A | â€” | â€” |
| gravity-rises | `gravity-rises` | P1 | READY | â€” |
| forumfold | `forumfold` | P1 | READY | â€” |
| museum-of-verbs | `museum-of-verbs` | P2 | READY | P2 hide candidate |
| negative-memory | `negative-memory` | P2 | READY | P2 hide candidate |
| zen-house | `zen-house` | P1 | PARTIAL | paragraph loss |
| zen-house-1 | `zen-house` | N/A | PARTIAL | alias â†’ zen-house |
| bank-of-15mins-fame | `bank-of-15mins-fame` | P1 | READY | â€” |
| post-carbon-city | `post-carbon-city` | P2 | PARTIAL | full-width imgs |
| university-island | `university-island` | P2 | READY | P2 hide candidate |
| new-museum-in-motion | `new-museum-in-motion` | P2 | READY | â€” |
| liberty-museum | `liberty-museum` | P2 | READY | â€” |
| mushroom-chair | `mushroom-chair` | P2 | READY | P2 hide candidate |
| black-hole-horizon | `black-hole-horizon` | P1 | PARTIAL | attribution OK |
| black-hole-horizon-1 | `black-hole-horizon` | N/A | PARTIAL | alias |
| walk-on-the-edge | `walk-on-the-edge` | P0 | NEEDS-WORK | empty cover (#32/#53) â€” **visible**, fix content not hide |
| vertical-campus | `vertical-campus` | P1 | PARTIAL | paragraph loss |
| app-ghost-hunter | `app-ghost-hunter` | P2 | PARTIAL | paragraph loss |
| app-ghost-hunter-1 | `beijing-untouched` | P2 | READY | renamed slug |
| nyc-taxi-20 | `nyc-taxi-20` | P2 | PARTIAL | â€” |
| takenaka-pavillion | `takenaka-pavilion` | P2 | READY | typo fixed |
| bmx-bike | `bmx-bike` | P2 | PARTIAL | â€” |
| bubble-bar | `bubble-bar` | P2 | READY | â€” |
| silence-of-the-mask | `silence-of-the-mask` | P2 | READY | â€” |
| seed-on-mars | `seed-on-mars` | P2 | READY | â€” |
| a-measurement-of-isolation | `a-measurement-of-isolation` | P2 | READY | â€” |
| tokyo-antilibrary | `tokyo-antilibrary` | P2 | READY | â€” |
| hashtag-brunch | `hashtag-brunch` | P2 | READY | â€” |
| **PRO (not in sitemap)** | | | | |
| â€” | `bilibili-hq` | **P0** | PRO | visible |
| â€” | `bytedance-hq` | **P0** | PRO | visible |
| â€” | `ftz-shanghai` | **P0** | PRO | visible |
| â€” | `hudson-yards` | **P0** | PRO | visible |
| **New site only** | | | | |
| â€” | `block-field` | P2 | READY | no archive sitemap entry |
| â€” | `ticket-booth-for-nose` | P1 | READY | â€” |

## Code section (not in archive sitemap)

| Slug | Tier | P1 issue |
|------|------|----------|
| `enneadtab-ecosystem` | **P0** | embed OK â€” confirmed |
| `bimrunner` | **P0** | **done** â€” `internal: true` + availability note |
| `enneadtab-revit` | **P0** | **done** â€” `internal: true` + availability note |
| `enneadtab-rhino` | P1 | **done** â€” `internal: true` + availability note |
| `revit-games` | P1 | **done** â€” `internal: true` + availability note |
| `renderpolisher` | P2 | #33 |
| `enneadtabwiki` | P2 | #33 |
| `realm`, `fat2fit`, `ideafactory`, `timebank`, `toni` | P2 | #33 optional |

## P0 summary (S2 target)

| Todo | Action |
|------|--------|
| **#32 / #53** | `walk-on-the-edge`: visible on grid/sidebar â€” fix empty cover + stub content (do **not** hide in P1) |
| **#33** | Flagship code: **done interim** â€” ecosystem embed; bimrunner/revit/rhino/revit-games show internal note; add public liveUrls when available |
| **#48** | **Done 2026-06-21:** PRO grid covers compressed â€” bilibili **24.8â†’23 KB** (400w WebP), bytedance **16.1â†’14 KB**, ftz **11.2â†’16 KB**, hudson-yards **0.9 MBâ†’33 KB** (unchanged source). All 30 architecture grid covers: **~58 MB â†’ ~350 KB** at 400w via `srcset`. Detail PRO inline images also optimized. `npm run optimize:covers` |
| **#70** | **Spot-check OK** â€” `resume.ts` quantified (500+ tools, 60 users, 63k events, copyright). PDF exists (~89 KB); regen pipeline still Windows-broken â€” rough parity at S2.5 |
| **Routes** | `/`, `/about`, `/architecture` (**all** projects visible), `/code`, `/speaking` |

## Static export slug column

All architecture/code/speaking slugs above are pre-rendered via `generateStaticParams` (no `published` filter during P1 â€” **P2-A0** adds filtering after sign-off).

## Sign-off (S2.5 â€” Sen)

| Date | Decision | Exceptions |
|------|----------|------------|
| **2026-06-26** | **Signed off** (#1683 — "signoff ok") | None |

**Checklist:** side-by-side [legacy archive](https://legacy-personal-website.vercel.app) vs v1 prod â€” `/`, `/about`, `/architecture` (**full grid**), `/code`, `/speaking`, spot-check all tiers. **P2 curation** (hide polish-tier, tune highlights) now unblocked via local dashboard.
