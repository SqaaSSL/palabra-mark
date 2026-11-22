"""Renders palabra-mark.md to HTML in the look of a LaTeX article. Print the HTML to PDF from a browser (A4)."""
import markdown, re, os
here = os.path.dirname(os.path.abspath(__file__))
body = markdown.markdown(open(os.path.join(here, "palabra-mark.md")).read(), extensions=["tables", "fenced_code"])
body = re.sub(r"(\[\d+\] [^\n<]+)\n", r"\1<br>\n", body)
body = re.sub(r"<h2>Abstract</h2>(.*?)(?=<h2>)", r'<div class="abstract"><h2>Abstract</h2>\1</div>', body, flags=re.S)   # set the abstract apart
body = re.sub(r"<p><strong>((?:Table|Figure) \d+\.[^<]*)</strong>([^<]*)</p>", r'<p class="cap"><strong>\1</strong>\2</p>', body)
body = body.replace("<h2>References</h2>", '<h2>References</h2><div class="refs">') + "</div>"
css = """@page{size:A4;margin:25mm 27mm 24mm}
body{font:10pt/1.42 'Latin Modern Roman','CMU Serif','STIX Two Text','Times New Roman',Times,serif;color:#000;max-width:42rem;margin:0 auto;text-align:justify;hyphens:auto}
h1{font-size:17pt;line-height:1.2;font-weight:400;text-align:center;margin:0 0 1.1em;hyphens:none}
.authors{text-align:center;font-size:11.5pt;margin-bottom:.5em;hyphens:none}.affil{text-align:center;font-size:9.5pt;line-height:1.5}
.date{text-align:center;font-size:10pt;margin:.9em 0 1.8em}sup{font-size:.7em;line-height:0}
.abstract{margin:0 2.6em 1.6em;font-size:9.3pt}.abstract h2{text-align:center;font-size:10pt;margin:0 0 .5em}
h2{font-size:12pt;font-weight:700;margin:1.5em 0 .5em;text-align:left;hyphens:none}h3{font-size:10.5pt;font-weight:700;margin:1.2em 0 .4em;text-align:left;hyphens:none}
p{margin:0 0 .65em}ul,ol{margin:.2em 0 .7em;padding-left:1.6em}li{margin-bottom:.25em}a{color:inherit;text-decoration:none}
table{border-collapse:collapse;margin:.3em auto 1.2em;font-size:9pt;line-height:1.3;text-align:left;hyphens:none;border-top:1.2px solid #000;border-bottom:1.2px solid #000}
th{font-weight:700;border-bottom:.7px solid #000}th,td{padding:.28em .7em;vertical-align:top}td:not(:first-child),th:not(:first-child){font-variant-numeric:tabular-nums}
.cap{text-align:center;font-size:9.3pt;margin:1em 2em .3em;hyphens:none}
pre{font:8.3pt/1.4 'Latin Modern Mono',Menlo,monospace;margin:.5em 0 .9em 1.5em;white-space:pre-wrap;text-align:left;hyphens:none}code{font:.88em 'Latin Modern Mono',Menlo,monospace;hyphens:none}
img{max-width:88%;display:block;margin:1em auto .3em}em{font-style:italic}table,img,pre{break-inside:avoid}h2,h3,.cap{break-after:avoid}
.refs{font-size:9pt;text-align:left;hyphens:none}.refs p{margin:0 0 .35em;padding-left:2.1em;text-indent:-2.1em}"""
open(os.path.join(here, "palabra-mark.html"), "w").write(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Palabra Mark</title><style>{css}</style></head><body>{body}</body></html>')
