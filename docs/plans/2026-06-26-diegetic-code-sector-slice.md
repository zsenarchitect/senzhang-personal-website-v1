# Diegetic code-sector vertical slice (#1739)

**Epic:** #1742 diegetic multi-sector UIUX  
**Child:** #1739 CRT/VCR code section  
**Related technique:** #1839 retro-digital compositing (#1834 hard edges + #1838 negative overlay on pin titles)

## Scope (this slice)

First end-to-end proof on the **Code** section only:

- CRT monitor bezel + scanlines + light static on `#page`
- Phosphor-green readable typography (real DOM, not baked video)
- Subtle RGB-split on masonry pin hover
- `mix-blend-mode: difference` on pin titles (pairs with #1838)
- `image-rendering: crisp-edges` on thumbnails (pairs with #1834)
- **Plain view** toggle (recruiter fast path)
- `prefers-reduced-motion` disables glitch/static animation

## Not in this slice

- POV transition videos (architecture -> code)
- Newspaper / certificate / paper sectors
- Site-wide nav diegetic treatment

## Assets

| File | Role |
|------|------|
| `snapshot/2026-06-05/_sz/diegetic/code-sector.css` | CRT skin |
| `snapshot/2026-06-05/_sz/diegetic/code-sector.js` | Plain-view toggle + SVG RGB filter |
| `scripts/apply-diegetic-code-sector.py` | Idempotent inject into `code/*.html` |

## Apply

```powershell
py -3 scripts\apply-diegetic-code-sector.py
py -3 scripts\serve.py
# Open http://127.0.0.1:8765/code
```

Runs automatically in `scripts/deploy-vercel.ps1` before cache stamp.

## Review checklist

- [ ] `/code` readable at a glance (recruiter skim)
- [ ] Plain view restores legacy white field
- [ ] Reduced motion: no distracting flicker
- [ ] Project detail pages under `/code/*` still usable
- [ ] Performance: no layout jank on masonry scroll
