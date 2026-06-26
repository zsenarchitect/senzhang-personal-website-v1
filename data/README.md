# Portfolio configuration (source of truth)

**Canonical file:** `projects.json` — tracked in git long-term. Edit via:

- Local dashboard: http://127.0.0.1:8765/dashboard (auto-saves here)
- Direct edit + `py -3 scripts/apply-portfolio-config.py`
- Merge v0 MDX metadata: `py -3 scripts/sync-project-meta-from-v0.py`

## Schema (`version: 2`)

| Field | Scope | Purpose |
|-------|--------|---------|
| `projects.<slug>.visible` | per project | Show in section masonry grids |
| `projects.<slug>.highlight` | per project | Two-column stagger pin in grid |
| `projects.<slug>.includeInResume` | per project | Featured portfolio block on `/about-me` |
| `projects.<slug>.category` | per project | `academic` \| `professional` \| `code` \| `speaking` |
| `projects.<slug>.subtitle` | per project | One-line description / meta line |
| `projects.<slug>.cover` | per project | e.g. `projects/bilibili-hq/cover.jpg` |
| `projects.<slug>.abstract` | per project | Optional hero abstract |
| `projects.<slug>.date`, `role`, `location`, `event` | per project | Category-specific meta line |
| `projects.<slug>.stack`, `embed` | per project | Code projects only |
| `sectionOrder.<category>` | per section | Masonry order (dashboard drag-sort) |

JSON Schema: `project.schema.json`. New-project checklist: `projects/_template.md`.

**Page layout:** all MDX-ported pages use `scripts/project_page.py` (marker, title, meta, abstract, cover, body, embed).

New slugs discovered from section scripts are merged in with defaults from `registry.defaults.json` (conservative: hidden until curated).

Academic masonry thumbnails and tiles are parsed from `snapshot/<date>/works.html` (full legacy grid), **not** from the derived `/academic` masonry page.

## Apply config → snapshot

```powershell
py -3 scripts\sync-project-meta-from-v0.py   # optional: pull MDX frontmatter
py -3 scripts\port-v0-content.py             # rebuild pro/code/speaking HTML from MDX
py -3 scripts\apply-portfolio-config.py      # rebuild grids + about-me from registry
```

**Commit workflow:** after curation, commit `data/projects.json` **and** regenerated `snapshot/` HTML together.

Milestone prod deploy runs `apply-portfolio-config.py` automatically; prod always reflects the committed `projects.json` in the deploy tree.

## Not stored here

- `thumbnail` on dashboard GET is derived from tile pool (stripped on POST)
- Offline URL patches, cache stamps, and lightbox fixes are deploy-time only (not config)
