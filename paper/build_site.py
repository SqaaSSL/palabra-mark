"""Publishes the paper on the site: site/paper/index.html (reading version), the PDF and the figures.  python3 build_site.py [output folder]"""
import markdown, os, re, shutil, sys
here = os.path.dirname(os.path.abspath(__file__)); out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "..", "site", "paper")       # the site lives in the private repository next door; os.makedirs(os.path.join(out, "figures"), exist_ok=True)
md = open(os.path.join(here, "palabra-mark.md"), encoding="utf8").read()
title = re.search(r"^# (.+)$", md, re.M).group(1); md = md[md.index("## Abstract"):]
body = markdown.markdown(md, extensions=["tables", "fenced_code"])
body = re.sub(r"(\[\d+\] [^\n<]+)\n", r"\1<br>\n", body)
body = re.sub(r"<p><strong>((?:Table|Figure) \d+\.[^<]*)</strong>([^<]*)</p>", r'<p class="cap"><strong>\1</strong>\2</p>', body)
def anchor(m):                                                               # "6.9 Live phone calls" gets the id s-6-9
    num = re.match(r"(\d+(?:\.\d+)*)", m.group(2)); return f'<h{m.group(1)} id="s-{num.group(1).replace(".", "-")}">{m.group(2)}</h{m.group(1)}>' if num else m.group(0)
body = re.sub(r"<h([23])>(.*?)</h\1>", anchor, body)
body = body.replace("<h2>Abstract</h2>", '<h2 id="abstract">Abstract</h2>').replace("<h2>References</h2>", '<h2 id="references">References</h2>')
short = lambda n: re.sub(r"^(\d+)\. ", lambda m: m.group(1) + " · ", n)
def crossref(body):
    """Makes every "Section 6.13", "Table 14", "Figure 5" and "[24]" in the text a link to what it names."""
    head, sep, refs = body.partition('<h2 id="references">')
    head = re.sub(r'<p class="cap"><strong>Table (\d+)\.', r'<p class="cap" id="t-\1"><strong>Table \1.', head)
    head = re.sub(r'<p><em>Figure (\d+)\.', r'<p class="cap" id="f-\1"><em>Figure \1.', head)
    refs = re.sub(r'<p>\[(\d+)\] ', r'<p id="ref-\1">[\1] ', refs)
    ids = set(re.findall(r'id="([^"]+)"', head + refs)); NUM = r"\d+(?:\.\d+)*"
    def nums(prefix, cls):
        def one(n): i = prefix + n.group().replace(".", "-"); return f'<a class="{cls}" href="#{i}">{n.group()}</a>' if i in ids else n.group()
        return lambda m: m.group(1) + re.sub(NUM, one, m.group(2))
    def text(s):
        for word, prefix in (("Section", "s-"), ("Table", "t-"), ("Figure", "f-")):
            s = re.sub(r"\b(%ss? )(%s(?:(?:, | and | to )%s)*)" % (word, NUM, NUM), nums(prefix, "x"), s)
        return re.sub(r"(\[)(\d+(?:, \d+)*)(?=\])", nums("ref-", "c"), s)
    out, skip, prev = [], 0, ""
    for part in re.split(r"(<[^>]+>)", head):
        if part.startswith("<"):
            name = re.match(r"</?(\w+)", part).group(1)
            if name in ("pre", "code", "h2", "h3", "a"): skip += -1 if part[1] == "/" else 1
            prev = part; out.append(part); continue
        own = re.match(r"(Table|Figure) \d+\. ", part) if prev in ("<strong>", "<em>") else None     # a caption does not link to itself
        out.append(part if skip else (own.group(0) + text(part[own.end():]) if own else text(part))); prev = ""
    return "".join(out) + sep + refs
body = crossref(body)
toc = "".join('<a href="#' + i + '">' + short(n) + "</a>" for i, n in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body))
shutil.copy(os.path.join(here, "palabra-mark-latex.pdf"), os.path.join(out, "palabra-mark.pdf"))
for f in os.listdir(os.path.join(here, "figures")): shutil.copy(os.path.join(here, "figures", f), os.path.join(out, "figures", f))
GLYPH = '<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><rect width="9" height="9"/><rect x="11" y="11" width="9" height="9"/><rect x="11" width="9" height="9" opacity=".38"/><rect y="11" width="9" height="9" opacity=".38"/></svg>'
LINKS = [("/showcase/", "Showcase"), ("/developers/", "Developers"), ("/paper/", "Paper")]
page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Paper · Palabra</title>
<meta name="description" content="{title}">
<meta name="citation_title" content="{title}">
<meta name="citation_author" content="Ernesto Cohnen de la Cámara"><meta name="citation_author" content="Francisco Novella Fletcher">
<meta name="citation_author" content="José Miguel Ávila Gómez"><meta name="citation_author" content="Carlos Tomás Ferrer">
<meta name="citation_publication_date" content="2026/11/22"><meta name="citation_pdf_url" content="https://palabra.ae/paper/palabra-mark.pdf">
<meta property="og:title" content="Paper · Palabra"><meta property="og:description" content="{title}"><meta property="og:image" content="https://palabra.ae/og.png">
<meta name="theme-color" content="#2A2FD0">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..800&family=Martian+Mono:wght@400;500&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&display=swap">
<link rel="stylesheet" href="/assets/palabra.css">
<style>
/* the paper: the site's shell around a long read set in the reading serif */
.top h1{{font-weight:800;font-size:clamp(1.9rem,4.2vw,3.5rem);line-height:1;letter-spacing:-.045em;max-width:24ch;text-wrap:balance}}
.who{{margin-top:1.4rem;max-width:46rem}}.who small{{display:block;color:var(--soft);margin-top:.3rem;font-size:.92rem}}
.longread{{font-family:var(--speech);font-size:1.12rem;line-height:1.62;gap:0}}
.longread>*{{margin-bottom:1rem}}
.longread h2,.longread h3,.longread table,.longread .cap,.longread pre,.longread code{{font-family:var(--display)}}
.longread h2{{margin-bottom:1.1rem}}.longread h3{{margin-top:1.6rem;margin-bottom:.5rem}}
.longread p,.longread li{{color:oklch(0.25 0.05 278)}}
.longread table{{font-size:.84rem;line-height:1.35;border-top:2px solid var(--ink);margin-bottom:1.8rem}}
.longread th{{font-family:var(--display);font-size:.84rem;letter-spacing:0;text-transform:none;font-weight:700;color:var(--ink);border-bottom:1px solid var(--ink)}}
.longread td{{font-variant-numeric:tabular-nums}}
.longread .cap{{font-size:.9rem;line-height:1.4;margin-top:1.4rem;margin-bottom:.5rem;color:var(--ink)}}
.longread pre{{font-family:var(--mono);font-size:.78rem;line-height:1.6;background:oklch(0.91 0.02 275);padding:1rem 1.1rem;white-space:pre-wrap;overflow-wrap:anywhere}}
.longread pre code{{background:none;padding:0;font-family:inherit}}
.longread img{{margin:1.2rem 0 .4rem;border:1px solid var(--rule)}}
.longread em{{color:var(--soft)}}
.longread a{{font-weight:400}}
.longread a.x{{color:inherit;text-decoration:underline;text-decoration-color:var(--ridge);text-decoration-thickness:1.5px;text-underline-offset:.2em}}
.longread a.x:hover{{color:var(--cobalt)}}
.longread a.c{{color:var(--cobalt);text-decoration:none;font-family:var(--display);font-size:.9em}}
.longread a.c:hover{{text-decoration:underline}}
.longread p:target{{background:oklch(0.9 0.05 275);box-shadow:0 0 0 .4rem oklch(0.9 0.05 275)}}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="head paper">
  <div class="wrap">
    <a class="brand" href="/" aria-label="Palabra, home">{GLYPH}palabra</a>
    <nav class="nav" aria-label="Main">
      {"".join(f'<a class="opt" href="{h}"' + (' aria-current="page"' if h == "/paper/" else "") + f'>{n}</a>' for h, n in LINKS)}
      <details class="menu"><summary>Menu</summary><div>{"".join(f'<a href="{h}">{n}</a>' for h, n in LINKS)}<a href="/#talk">Talk to us</a></div></details>
      <a class="btn sm" href="/app/"><svg class="ic" aria-hidden="true"><use href="/assets/icons.svg#key"/></svg>Get API keys</a>
    </nav>
  </div>
</header>
<main id="main">
  <div class="wrap top">
    <h1>{title}</h1>
    <p class="who">Ernesto Cohnen de la Cámara, Francisco Novella Fletcher, José Miguel Ávila Gómez, Carlos Tomás Ferrer<small>SqaaS (Squad as a Service SL), Madrid · ixigo · contact@sqaas.io · 22 November 2026</small></p>
    <div class="acts"><a class="btn" href="/paper/palabra-mark.pdf"><svg class="ic" aria-hidden="true"><use href="/assets/icons.svg#download"/></svg>Download the PDF</a><a class="btn line" href="/showcase/"><svg class="ic" aria-hidden="true"><use href="/assets/icons.svg#scope"/></svg>Try it live</a></div>
  </div>
  <div class="wrap doc" style="border-top:1px solid var(--rule)">
    <nav class="toc" aria-label="Sections"><p class="label">Sections</p>{toc}</nav>
    <article class="prose longread">
{body}
    </article>
  </div>
</main>
<footer class="foot">
  <div class="wrap">
    <div class="cols">
      <div><a class="brand" href="/" aria-label="Palabra, home"><svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><rect width="9" height="9"/><rect x="11" y="11" width="9" height="9"/><rect x="11" width="9" height="9" opacity=".38"/><rect y="11" width="9" height="9" opacity=".38"/></svg>palabra</a><p class="tag">Verified identity for AI voice-agent calls.</p>
        <a class="by" href="https://sqaas.io" rel="noopener"><span>A project of</span><img src="/assets/sqaas.svg" alt="SqaaS" width="96" height="32" loading="lazy"></a></div>
      <div><h2>Product</h2><ul><li><a href="/showcase/"><svg class="ic" aria-hidden="true"><use href="/assets/icons.svg#scope"/></svg>Showcase</a></li><li><a href="/developers/"><svg class="ic" aria-hidden="true"><use href="/assets/icons.svg#code"/></svg>Developers</a></li><li><a href="/agents/"><svg class="ic" aria-hidden="true"><use href="/assets/icons.svg#agent"/></svg>For AI agents</a></li><li><a href="/app/"><svg class="ic" aria-hidden="true"><use href="/assets/icons.svg#console"/></svg>Console</a></li></ul></div>
      <div><h2>Research</h2><ul><li><a href="/paper/"><svg class="ic" aria-hidden="true"><use href="/assets/icons.svg#doc"/></svg>Paper</a></li><li><a href="/paper/palabra-mark.pdf"><svg class="ic" aria-hidden="true"><use href="/assets/icons.svg#download"/></svg>PDF</a></li><li><a href="/#measured"><svg class="ic" aria-hidden="true"><use href="/assets/icons.svg#chart"/></svg>Measurements</a></li></ul></div>
      <div><h2>Company</h2><ul><li><a href="/#talk"><svg class="ic" aria-hidden="true"><use href="/assets/icons.svg#chat"/></svg>Talk to us</a></li><li><a href="mailto:contact@sqaas.io"><svg class="ic" aria-hidden="true"><use href="/assets/icons.svg#mail"/></svg>contact@sqaas.io</a></li><li><a href="https://www.linkedin.com/company/sqaas" rel="noopener"><svg class="ic" aria-hidden="true"><use href="/assets/icons.svg#linkedin"/></svg>LinkedIn</a></li></ul></div>
    </div>
    <p class="fine"><span>© <span data-year>2026</span> Squad as a Service, S.L. · Madrid, Spain</span><span class="legal"><a href="/privacy/"><svg class="ic" aria-hidden="true"><use href="/assets/icons.svg#eye"/></svg>Privacy</a><a href="/terms/"><svg class="ic" aria-hidden="true"><use href="/assets/icons.svg#scale"/></svg>Terms</a></span></p>
  </div>
</footer>
<script src="/assets/palabra.js" defer></script>
<script>document.addEventListener("DOMContentLoaded",function(){{Palabra.spy(document.querySelector(".toc"))}})</script>
</body>
</html>
"""
open(os.path.join(out, "index.html"), "w", encoding="utf8").write(page); print("site/paper written,", len(page) // 1024, "kB")
