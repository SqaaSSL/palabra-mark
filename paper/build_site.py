"""Publishes the paper on the site: site/paper/index.html (reading version), the PDF and the figures.  python3 build_site.py [output folder]"""
import markdown, os, re, shutil, sys
here = os.path.dirname(os.path.abspath(__file__)); out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "..", "site", "paper")       # the site lives in the private repository next door; os.makedirs(os.path.join(out, "figures"), exist_ok=True)
md = open(os.path.join(here, "palabra-mark.md"), encoding="utf8").read()
title = re.search(r"^# (.+)$", md, re.M).group(1); md = md[md.index("## Abstract"):]
body = markdown.markdown(md, extensions=["tables", "fenced_code"])
body = re.sub(r"(\[\d+\] [^\n<]+)\n", r"\1<br>\n", body)
body = re.sub(r"<p><strong>((?:Table|Figure) \d+\.[^<]*)</strong>([^<]*)</p>", r'<p class="cap"><strong>\1</strong>\2</p>', body)
body = body.replace("<table>", '<div class="tw"><table>').replace("</table>", "</table></div>")
shutil.copy(os.path.join(here, "palabra-mark-latex.pdf"), os.path.join(out, "palabra-mark.pdf"))
for f in os.listdir(os.path.join(here, "figures")): shutil.copy(os.path.join(here, "figures", f), os.path.join(out, "figures", f))
page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Palabra Mark · Paper</title>
<meta name="description" content="{title}">
<meta name="citation_title" content="{title}">
<meta name="citation_author" content="Ernesto Cohnen de la Cámara"><meta name="citation_author" content="Francisco Novella Fletcher">
<meta name="citation_author" content="José Miguel Ávila Gómez"><meta name="citation_author" content="Carlos Tomás Ferrer">
<meta name="citation_publication_date" content="2026/11/22"><meta name="citation_pdf_url" content="https://palabra.ae/paper/palabra-mark.pdf">
<meta property="og:title" content="Palabra Mark · Paper"><meta property="og:description" content="{title}"><meta property="og:image" content="https://palabra.ae/og.png">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,800&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&display=swap" rel="stylesheet">
<style>
:root{{--cobalt:#2A2FD0;--ink:#090A20;--paper:#ECEEF5;--white:#F6F7FE;--ice:#AEB4FF;--dim:#8C92C4;--line:#ffffff1c;--display:"Bricolage Grotesque","Helvetica Neue",Arial,sans-serif;--speech:"Newsreader",Georgia,serif}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--ink);color:var(--white);font-family:var(--display);-webkit-font-smoothing:antialiased;overflow-x:clip}}
.wrap{{max-width:84rem;margin:0 auto;padding:0 max(20px,env(safe-area-inset-left,0px)) 0 max(20px,env(safe-area-inset-right,0px))}}a{{color:inherit}}
.top{{display:flex;justify-content:space-between;align-items:center;padding:26px 0}}.top .mark{{font-weight:800;font-size:1.5rem;letter-spacing:-.03em;text-decoration:none}}
.top nav{{display:flex;gap:1.4rem;align-items:center;font-size:.98rem}}.top nav a{{text-decoration:none;color:var(--paper)}}.top nav a[aria-current]{{color:var(--ice)}}
.top nav .pill{{border:1px solid var(--line);padding:10px 18px;border-radius:99px}}.top nav a{{white-space:nowrap}}@media(max-width:560px){{.top nav .hide,.top nav .pill{{display:none}}}}
.head{{padding:clamp(28px,5vw,64px) 0 clamp(30px,4vw,52px);max-width:62rem}}
.head .label{{font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:var(--dim)}}
.head h1{{font-size:clamp(1.9rem,4.6vw,3.6rem);line-height:1.03;letter-spacing:-.035em;font-weight:800;margin:.35em 0 .5em}}
.head .who{{font-size:1.05rem;color:var(--paper);line-height:1.5}}.head .who small{{display:block;color:var(--dim);font-size:.9rem;margin-top:.3em}}
.head .go{{display:flex;flex-wrap:wrap;gap:12px;margin-top:26px}}.head .go a{{text-decoration:none;font-weight:600;padding:.7em 1.3em;border-radius:99px;border:1px solid var(--line)}}
.head .go a.main{{background:var(--white);color:var(--ink);border-color:var(--white)}}
article{{background:var(--paper);color:#12143A;border-radius:26px 26px 0 0;padding:clamp(26px,6vw,80px) clamp(18px,6vw,80px) 80px;font:1.06rem/1.62 var(--speech)}}
article>*{{max-width:44rem;margin-left:auto;margin-right:auto}}
article h2{{font:800 1.55rem/1.15 var(--display);letter-spacing:-.02em;margin-top:2.4em;margin-bottom:.5em;color:var(--cobalt)}}article h2:first-child{{margin-top:0}}
article h3{{font:600 1.12rem/1.25 var(--display);margin-top:1.9em;margin-bottom:.4em}}article p{{margin-top:0;margin-bottom:.9em}}
article .tw{{max-width:52rem;overflow-x:auto;margin-bottom:1.6em}}article table{{border-collapse:collapse;width:100%;font:.84rem/1.35 var(--display);border-top:1.5px solid #12143A;border-bottom:1.5px solid #12143A}}
article th{{border-bottom:1px solid #12143A;font-weight:600}}article th,article td{{padding:.4em .7em;text-align:left;vertical-align:top}}article td:not(:first-child){{font-variant-numeric:tabular-nums}}
article .cap{{font:.86rem/1.4 var(--display);margin-bottom:.4em;margin-top:1.6em}}article pre{{font:.8rem/1.5 ui-monospace,Menlo,monospace;background:#12143A0d;border-radius:10px;padding:14px 16px;white-space:pre-wrap;overflow-wrap:anywhere}}
article code{{font:.86em ui-monospace,Menlo,monospace}}article img{{max-width:min(100%,52rem);display:block;margin:1.4em auto .5em;border-radius:8px}}article em{{color:#4D527C}}
article li{{margin-bottom:.4em}}article ul,article ol{{padding-left:1.4em}}
footer{{background:var(--paper);color:#4D527C;font-size:.85rem;padding:0 clamp(18px,6vw,80px) 44px}}footer p{{max-width:44rem;margin:0 auto;border-top:1px solid #12143A22;padding-top:22px}}
</style>
</head>
<body>
<div class="wrap">
  <header class="top"><a class="mark" href="/">Palabra</a>
    <nav><a class="txt hide" href="/showcase/">Showcase</a><a class="txt hide" href="/developers/">Developers</a><a class="txt" href="/paper/" aria-current="page">Paper</a><a class="pill" href="/app/">Get API keys</a></nav></header>
  <div class="head">
    <h1>{title}</h1>
    <p class="who">Ernesto Cohnen de la Cámara, Francisco Novella Fletcher, José Miguel Ávila Gómez, Carlos Tomás Ferrer<small>SqaaS (Squad as a Service SL), Madrid · ixigo · contact@sqaas.io · 22 November 2026</small></p>
    <div class="go"><a class="main" href="/paper/palabra-mark.pdf">Download the PDF</a><a href="/showcase/">Try it live</a></div>
  </div>
</div>
<article>
{body}
</article>
<footer><p>Palabra is a project of <a href="https://sqaas.io" rel="noopener">SqaaS</a>. © 2026 Squad as a Service SL · <a href="https://sqaas.io/privacy" rel="noopener">Privacy</a> · <a href="https://sqaas.io/terms" rel="noopener">Terms</a></p></footer>
</body>
</html>
"""
open(os.path.join(out, "index.html"), "w", encoding="utf8").write(page); print("site/paper written,", len(page) // 1024, "kB")
