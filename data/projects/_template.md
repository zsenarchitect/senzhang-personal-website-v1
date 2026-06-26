# New project template (metadata)

Copy fields into `data/projects.json` under `projects.<slug>`, then add body via v0 MDX or `py -3 scripts/port-v0-content.py`.

```json
{
  "slug": "my-project",
  "title": "My Project",
  "category": "academic",
  "subtitle": "One-line description",
  "cover": "projects/my-project/cover.jpg",
  "date": "2026",
  "studio": "Optional studio line",
  "partner": "Optional partner",
  "role": "Designer",
  "location": "New York, NY",
  "event": "Conference Name",
  "stack": ["Python", "Next.js"],
  "embed": "",
  "abstract": "Short abstract paragraph (optional; else first MDX paragraph).",
  "visible": false,
  "highlight": false,
  "includeInResume": false
}
```

## Page layout (all categories)

Every generated project page uses the same block order (`scripts/project_page.py`):

1. Hidden marker `<!-- project-page-v1 slug=... category=... -->`
2. Centered **title** + **meta line** (category-specific fields)
3. **Stack chips** (code only)
4. **Abstract** (optional)
5. **Cover image**
6. **Body** (markdown images + paragraphs)
7. **Embed iframe** (code only, optional)

## Assets

Place files under:

```
snapshot/2026-06-05/_media/projects/<slug>/cover.jpg
snapshot/2026-06-05/_media/projects/<slug>/02.jpg
snapshot/2026-06-05/_media/speaking/<slug>/cover.jpg   # speaking convention
```

## Commands

```powershell
py -3 scripts\sync-project-meta-from-v0.py   # merge v0 MDX frontmatter into projects.json
py -3 scripts\port-v0-content.py           # rebuild code/speaking/pro pages from MDX
py -3 scripts\apply-portfolio-config.py      # rebuild grids from registry
```
