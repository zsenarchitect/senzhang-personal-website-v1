# senzhang.me master plan (v1 static)

**Active repo:** senzhang-personal-website-v1
**Preview:** https://senzhang-personal-website-v1.vercel.app
**Vercel team:** zsen-idea-house (personal; NOT ennead-projects)
**Keystone todo:** #1683

## Deploy policy

| When | How |
|------|-----|
| Day-to-day dev / S2.5 review | `py -3 scripts\serve.py` (local only) |
| Preview deploy (rare) | `.\scripts\deploy-vercel.ps1` (no -Prod) |
| **Milestone prod** | `.\scripts\deploy-vercel.ps1 -Prod -Milestone <label>` |

Prod milestones: `P1-port`, `S2.5`, `P2`, `DNS`, `cache-final` (#1680).

Do not prod-deploy on every commit.

## P1 status

Resume, PRO, code, speaking, nav fix, /code + /speaking indexes: **done**.
Deferred: about-me body from resume.ts.

## S2.5 sign-off (blocks P2)

Tab A: https://legacy-personal-website.vercel.app
Tab B/C: https://senzhang-personal-website-v1.vercel.app

Sign off on #1683. Then prod deploy: `-Milestone S2.5` if preview URL needs refresh.
