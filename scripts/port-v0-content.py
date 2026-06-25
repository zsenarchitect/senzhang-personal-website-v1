#!/usr/bin/env python3
from __future__ import annotations
import html, re, shutil, subprocess, sys
from pathlib import Path

V0 = Path(r"C:\Users\szhang\github\Personal\senzhang-personal-website-v0-failed-attempt")
V1 = Path(r"C:\Users\szhang\github\Personal\senzhang-personal-website-v1")
SNAP = V1 / "snapshot" / "2026-06-05"
TPL = SNAP / "liberty-museum.html"
MEDIA = SNAP / "_media"
PRO = ["bilibili-hq", "bytedance-hq", "ftz-shanghai", "hudson-yards"]
CODE = ["ideafactory","realm","fat2fit","toni","timebank","enneadtab-ecosystem","renderpolisher","bimrunner","revit-games"]
SPEAK = ["acd-austin-2026","aec-hackathon-2025","autodesk-university-2024","aec-hackathon-2023","digital-built-week-2023"]
IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

def parse_mdx(path):
    t = path.read_text(encoding="utf-8")
    e = t.index("---", 3)
    fr, body = t[3:e].strip(), t[e+3:].strip()
    meta, lk = {}, None
    for line in fr.splitlines():
        if not line.strip(): continue
        if line.startswith("  - ") and lk:
            meta.setdefault(lk, []).append(line.strip()[2:].strip()); continue
        if ":" in line:
            k, v = line.split(":", 1); k, v = k.strip(), v.strip().strip("'\"")
            if v == "": lk, meta[k] = k, []
            else: lk, meta[k] = None, v
    return meta, body

def media(url): return "_media/" + url.lstrip("/")

def copy_asset(url):
    src = V0 / "public" / url.lstrip("/")
    if not src.is_file():
        print("WARN", src); return None
    dst = MEDIA / url.lstrip("/")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return media(url)

def esc(x): return html.escape(x, quote=True)

def tb(inner):
    return '<div class="row sqs-row"><div class="col sqs-col-12 span-12"><div class="sqs-block html-block sqs-block-html" data-block-type="2"><div class="sqs-block-content"><div class="sqs-html-content" data-sqsp-text-block-content>%s</div></div></div></div></div>' % inner

def ib(src, alt):
    cap = ('<figcaption class="image-caption-wrapper"><div class="image-caption"><p>%s</p></div></figcaption>' % esc(alt)) if alt else ""
    return '<div class="row sqs-row"><div class="col sqs-col-12 span-12"><div class="sqs-block image-block sqs-block-image" data-block-type="5"><div class="sqs-block-content"><figure class="sqs-block-image-figure intrinsic"><img src="%s" alt="%s" loading="lazy" style="display:block;width:100%%;height:auto"/>%s</figure></div></div></div></div>' % (esc(src), esc(alt), cap)

def body_blocks(body):
    out = []
    for chunk in re.split(r"\n\s*\n", body.strip()):
        chunk = chunk.strip()
        if not chunk: continue
        m = IMG.fullmatch(chunk)
        if m:
            p = copy_asset(m.group(2))
            if p: out.append(ib(p, m.group(1)))
            continue
        if chunk.startswith("#"):
            n = len(chunk) - len(chunk.lstrip("#")); tag = "h%d" % min(n+1, 4)
            out.append(tb("<%s>%s</%s>" % (tag, esc(chunk.lstrip("#").strip()), tag))); continue
        para = LINK.sub(r'<a href="\2">\1</a>', chunk)
        if "<a " not in para: para = esc(para)
        out.append(tb("<p>%s</p>" % para))
    return "".join(out)

def tpl_parts():
    t = TPL.read_text(encoding="utf-8")
    s = t.index('<div class="main-content" data-content-field="main-content">')
    ls = t.index('<div class="sqs-layout sqs-grid-12', s)
    le = t.index(">", ls) + 1
    lc = t.index("</div>\n      </div>\n\n      \n\n      </section>", s)
    return t[:le], t[lc:]

def head(shell, title, fn):
    full = "%s &mdash; Sen Zhang" % title
    plain = "%s - Sen Zhang" % title
    shell = re.sub(r"<title>.*?</title>", "<title>%s</title>" % full, shell, 1)
    reps = [
        (r'<meta property="og:title" content="[^"]*"', '<meta property="og:title" content="%s"' % esc(title)),
        (r'<meta name="twitter:title" content="[^"]*"', '<meta name="twitter:title" content="%s"' % esc(plain)),
        (r'<link rel="canonical" href="[^"]*"', '<link rel="canonical" href="%s"' % fn),
        (r'<meta property="og:url" content="[^"]*"', '<meta property="og:url" content="%s"' % fn),
        (r'<meta name="twitter:url" content="[^"]*"', '<meta name="twitter:url" content="%s"' % fn),
        (r'<meta itemprop="name" content="[^"]*"', '<meta itemprop="name" content="%s"' % esc(plain)),
        (r'<meta itemprop="url" content="[^"]*"', '<meta itemprop="url" content="%s"' % fn),
    ]
    for a,b in reps: shell = re.sub(a, b, shell, 1)
    return shell

def write_page(path, title, inner):
    pre, suf = tpl_parts()
    path.write_text(head(pre, title, path.name) + inner + suf, encoding="utf-8")
    print("wrote", path.relative_to(V1))

def pro_page(slug):
    meta, body = parse_mdx(V0 / "src/content/architecture" / (slug + ".mdx"))
    title = meta.get("title", slug)
    line = " | ".join(x for x in [meta.get("subtitle",""), meta.get("role",""), meta.get("location",""), meta.get("date","")] if x)
    h = tb('<h1 class="text-align-center">%s</h1><p class="text-align-center">%s</p>' % (esc(title), esc(line)))
    ab, rest = "", body
    if rest and not rest.lstrip().startswith("!"):
        ps = rest.split("\n\n", 1)
        ab = tb("<h3>abstract:</h3><p>%s</p>" % esc(ps[0].strip()))
        rest = ps[1] if len(ps) > 1 else ""
    if meta.get("cover"): copy_asset(meta["cover"])
    write_page(SNAP / (slug + ".html"), title, h + ab + body_blocks(rest))

def code_page(slug):
    meta, body = parse_mdx(V0 / "src/content/code" / (slug + ".mdx"))
    title, sub = meta.get("title", slug), meta.get("subtitle", "")
    stack = meta.get("stack", [])
    if isinstance(stack, str): stack = [stack]
    st = ""
    if stack:
        st = tb("<p class=\"text-align-center\">%s</p>" % " ".join('<span style="display:inline-block;margin:2px 4px;padding:2px 8px;border:1px solid #ccc;font-size:12px">%s</span>' % esc(s) for s in stack))
    h = tb('<h1 class="text-align-center">%s</h1><p class="text-align-center">%s</p>' % (esc(title), esc(sub))) + st
    if meta.get("cover"): copy_asset(meta["cover"])
    blocks = h + body_blocks(body)
    if meta.get("embed"):
        e = copy_asset(meta["embed"])
        if e: blocks += tb('<iframe src="%s" title="%s" style="width:100%%;min-height:640px;border:1px solid #ddd" loading="lazy"></iframe>' % (esc(e), esc(title)))
    d = SNAP / "code"; d.mkdir(parents=True, exist_ok=True)
    write_page(d / (slug + ".html"), title, blocks)

def speak_page(slug):
    meta, body = parse_mdx(V0 / "src/content/speaking" / (slug + ".mdx"))
    title = meta.get("title", slug)
    line = " | ".join(x for x in [meta.get("event",""), meta.get("location",""), meta.get("date","")] if x)
    h = tb('<h1 class="text-align-center">%s</h1><p class="text-align-center">%s</p>' % (esc(title), esc(line)))
    cov = ""
    if meta.get("cover"):
        copy_asset(meta["cover"])
        cov = ib(media(meta["cover"]), title)
    d = SNAP / "speaking"; d.mkdir(parents=True, exist_ok=True)
    write_page(d / (slug + ".html"), title, h + cov + body_blocks(body))

def port_resume():
    shutil.copy2(V0 / "public/Sen Zhang Resume.pdf", MEDIA / "Sen-Zhang-Resume.pdf")
    subprocess.check_call([sys.executable, str(V1 / "scripts" / "port-about-resume.py")], cwd=str(V1))
    (V1 / "docs/resume-source.md").parent.mkdir(parents=True, exist_ok=True)
    (V1 / "docs/resume-source.md").write_text(
        "# Resume source\n\n"
        "Canonical: v0 `src/data/resume.ts` in `senzhang-personal-website-v0-failed-attempt`\n\n"
        "PDF: `snapshot/2026-06-05/_media/Sen-Zhang-Resume.pdf` "
        "(copied from v0 `public/Sen Zhang Resume.pdf`)\n\n"
        "Regenerate about-me body from resume.ts:\n\n"
        "```powershell\npy -3 scripts\\port-about-resume.py\n```\n\n"
        "`port-v0-content.py` calls this automatically when porting resume.\n",
        encoding="utf-8",
    )

def nav(href, label, ind=False):
    pad = "            " if ind else "          "
    return '%s<li class="page-collection">\n%s  <a href="%s">%s</a>\n%s</li>\n' % (pad, pad, href, esc(label), pad)

def folder(title, items, mobile):
    if mobile:
        return '        <li class="mobile-folder">\n          <a>%s</a>\n          <ul>\n%s          </ul>\n        </li>\n' % (esc(title), "".join(nav(h,l,True) for h,l in items))
    inner = "".join('                  <li class="page-collection">\n                    <a href="%s">%s</a>\n                  </li>\n\n                \n                \n              ' % (h, esc(l)) for h,l in items)
    return '      <li class="folder-collection folder">\n\n        \n\n          <a>%s</a>\n          <div class="subnav">\n            <ul>\n              \n                \n%s            </ul>\n          </div>\n\n        \n\n      </li>\n' % (esc(title), inner)

def update_menu():
    p = SNAP / "menu.html"; t = p.read_text(encoding="utf-8")
    pro = [("/ftz-shanghai","FTZ Free Trade Zone"),("/bilibili-hq","Bilibili HQ"),("/bytedance-hq","ByteDance HQ"),("/hudson-yards","40 Hudson Yards")]
    code = [("/code","All Code Projects")]+[("/code/"+s, l) for s,l in [
        ("ideafactory","ideaFactory"),("realm","REALM"),("fat2fit","Fat2Fit"),("toni","Toni"),("timebank","TimeBank"),
        ("enneadtab-ecosystem","EnneadTab Ecosystem"),("renderpolisher","RenderPolisher"),("bimrunner","BimRunner"),("revit-games","Revit Games")]]
    spk = [("/speaking","All Talks")]+[("/speaking/"+s, l) for s,l in [
        ("acd-austin-2026","The Design of Design"),("aec-hackathon-2025","Pull Request Control for Revit"),("autodesk-university-2024","Revit As A Game Engine"),
        ("aec-hackathon-2023","Educational Tool for Built Environment Innovation"),("digital-built-week-2023","Promoting Computational Design to Non-Programmers")]]
    if "bilibili-hq" not in t and "/bilibili-hq" not in t:
        t = t.replace('                <a href="app-ghost-hunter.html">APP: Ghost Hunter</a>', '                <a href="app-ghost-hunter.html">APP: Ghost Hunter</a>\n              \n\n            \n\n            </li>\n\n          \n\n' + "".join(nav(h,l,True) for h,l in pro) + '            <li class="page-collection">\n\n              \n                ', 1)
        t = t.replace('                    <a href="app-ghost-hunter.html">APP: Ghost Hunter</a>\n                  </li>', '                    <a href="app-ghost-hunter.html">APP: Ghost Hunter</a>\n                  </li>\n                \n                \n              \n                \n' + "".join('                  <li class="page-collection">\n                    <a href="%s">%s</a>\n                  </li>\n\n                \n                \n              ' % (h, esc(l)) for h,l in pro), 1)
    if 'href="/code/ideafactory"' not in t and 'href="code/ideafactory.html"' not in t:
        t = t.replace('              <a href="about-me.html">About</a>', folder("Code", code, True) + folder("Speaking", spk, True) + '              <a href="about-me.html">About</a>', 1)
        t = t.replace('            <a href="about-me.html">About</a>', folder("Code", code, False) + folder("Speaking", spk, False) + '            <a href="about-me.html">About</a>', 1)
    p.write_text(t, encoding="utf-8")

if __name__ == "__main__":
    MEDIA.mkdir(parents=True, exist_ok=True)
    port_resume()
    for s in PRO: pro_page(s)
    for s in CODE: code_page(s)
    for s in SPEAK: speak_page(s)
    update_menu()
    subprocess.check_call([sys.executable, str(V1 / "scripts" / "restructure-menu-sections.py")], cwd=str(V1))
    print("done")