# Portfolio configuration (source of truth)

**Canonical file:** `projects.json` — tracked in git long-term. Edit via:

- Local dashboard: http://127.0.0.1:8765/dashboard (auto-saves here)
- Direct edit + `py -3 scripts/apply-portfolio-config.py`

## Schema (`version: 1`)

| Field | Scope | Purpose |
|-------|--------|---------|
| `projects.<slug>.visible` | per project | Show in section masonry grids |
| `projects.<slug>.highlight` | per project | Two-column stagger pin in grid |
| `projects.<slug>.includeInResume` | per project | Featured portfolio block on `/about-me` |
| `projects.<slug>.category` | per project | `academic` \| `professional` \| `code` \| `speaking` |
| `sectionOrder.<category>` | per section | Masonry order (dashboard drag-sort) |

New slugs discovered from section scripts are merged in with defaults from `registry.defaults.json` (conservative: hidden until curated).

## Apply config → snapshot

```powershell
py -3 scripts\apply-portfolio-config.py
```

Rebuilds section index pages, menu hub, and about-me featured portfolio from this file.

**Commit workflow:** after curation, commit `data/projects.json` **and** regenerated `snapshot/` HTML together.

Milestone prod deploy runs `apply-portfolio-config.py` automatically; prod always reflects the committed `projects.json` in the deploy tree.

## Not stored here

- `thumbnail` on dashboard GET is derived from tile pool (stripped on POST)
- Offline URL patches, cache stamps, and lightbox fixes are deploy-time only (not config)
