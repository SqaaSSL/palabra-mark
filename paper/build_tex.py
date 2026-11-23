"""Renders palabra-mark.md to LaTeX (palabra-mark.tex), a PDF and the arXiv bundle (palabra-mark-arxiv.zip).
Needs pandoc and tectonic:  brew install pandoc tectonic ;  python3 build_tex.py"""
import os, re, subprocess
here = os.path.dirname(os.path.abspath(__file__)); os.chdir(here)
md = open("palabra-mark.md", encoding="utf8").read()
title = re.search(r"^# (.+)$", md, re.M).group(1)
abstract = re.search(r"## Abstract\n(.*?)\n## 1\.", md, re.S).group(1).strip()
body = md[md.index("## 1."):]
body = re.sub(r"^(#+) \d+(\.\d+)*\.? ", r"\1 ", body, flags=re.M)               # LaTeX numbers the sections itself
body = body.replace("## References", "## References {-}")

def tex_chars(s):                                                              # characters the text font lacks
    sup = {"⁻": "-", "⁷": "7", "⁶": "6", "²": "2"}
    raw = lambda t: "`" + t + "`{=latex}"                                      # raw LaTeX, so pandoc cannot misread the dollars
    s = re.sub("[⁻⁷⁶²]+", lambda m: raw("$^{" + "".join(sup[c] for c in m.group()) + "}$"), s)
    for a, b in {"×": r"$\times$", "τ": r"$\tau$", "→": r"$\rightarrow$", "←": r"$\leftarrow$", "−": "$-$", "ᵢ": "$_i$", "±": r"$\pm$",
                 "≤": r"$\leq$", "≥": r"$\geq$", "μ": r"$\mu$", "Σ": r"$\Sigma$", "∈": r"$\in$"}.items(): s = s.replace(a, raw(b))
    return s.replace("g_max", raw(r"$g_{\max}$"))
parts = re.split(r"(\n(?:    .*\n)+|`[^`\n]+`)", body)                         # (split before any raw LaTeX is added)                         # leave code alone, apart from plain substitutes
plain = {"×": "x", "τ": "tau", "→": "->", "←": "<-", "−": "-", "ᵢ": "_i", "±": "+/-", "≤": "<=", "≥": ">=", "μ": "mu", "Σ": "sum", "∈": "in", "⁻": "^-", "⁷": "7", "⁶": "6", "²": "^2"}
body = "".join(re.sub("[" + "".join(plain) + "]", lambda m: plain[m.group()], p) if i % 2 else tex_chars(p) for i, p in enumerate(parts))

open("_body.md", "w", encoding="utf8").write(body)
tex = subprocess.run(["pandoc", "_body.md", "-f", "markdown-auto_identifiers-implicit_figures", "-t", "latex", "--wrap=none", "--number-sections", "--shift-heading-level-by=-1"], capture_output=True, text=True, check=True).stdout
os.remove("_body.md")
tex = re.sub(r"(?ms)^(\\textbf\{(?:Table|Figure) \d+\..*?)\n\n", r"\\needspace{7\\baselineskip}\\begin{center}\\small \1\\end{center}\n\n", tex)   # captions, kept on the page of what they describe
tex = tex.replace(r"\pandocbounded{\includegraphics", r"\begin{center}\pandocbounded{\includegraphics").replace(".png}}", ".png}}\\end{center}")
tex = tex.replace(r"\begin{verbatim}", r"\begin{Verbatim}[breaklines,fontsize=\footnotesize]").replace(r"\end{verbatim}", r"\end{Verbatim}")
EQ = {  # the formulas are plain text in the markdown; set them as mathematics here
    "code = HMAC": r"\mathrm{code} = \mathrm{HMAC\mbox{-}SHA256}(\mathrm{secret},\ \mathrm{caller} \mid \mathrm{callee} \mid \mathrm{time\ slot})",
    "f = L(t, k)": r"f = L(t, k) - L(t, k+1) - L(t+1, k) + L(t+1, k+1)",
    "g <- clip": r"g \leftarrow \mathrm{clip}\!\left( g + \frac{m - s f}{4},\ 0,\ g_{\max} \right), \quad \mbox{repeated 4 times}",
    "z(T) = sum": r"z(T) = \frac{\sum_i s_i v_i}{\sqrt{\sum_i v_i^2}}",
    "P(false alarm": r"P(\mbox{false alarm per wrong code}) \leq 4650 \cdot \exp(-\tau^2/2) = 1.1 \times 10^{-7} \quad \mbox{at } \tau = 7.",
}
def eq(m):
    hit = [v for k, v in EQ.items() if m.group(1).strip().startswith(k)]
    return "\\[" + hit[0] + "\\]" if hit else m.group(0)
tex = re.sub(r"\\begin\{Verbatim\}\[[^\]]*\]\n(.*?)\n\\end\{Verbatim\}", eq, tex, flags=re.S)
tex = tex.replace(r"\section{References}", r"\section*{References}\small\raggedright")
# cross-references: sections, tables, figures and citations become links inside the PDF, as is usual in arXiv papers
main, cut, refs = tex.partition(r"\section*{References}")
sec = [0, 0]; labels = set()
def heading(m):
    if m.group(1) == "section": sec[0] += 1; sec[1] = 0; n = str(sec[0])
    else: sec[1] += 1; n = f"{sec[0]}-{sec[1]}"
    labels.add("s-" + n); return m.group(0) + "\\label{s-" + n + "}"
main = re.sub(r"^\\(section|subsection)\{.*\}$", heading, main, flags=re.M)
def caption(m):
    k = ("t-" if m.group(2) == "Table" else "f-") + m.group(3); labels.add(k)
    return "\\phantomsection\\label{" + k + "}" + m.group(1) + m.group(2)[0] + "\0" + m.group(2)[1:] + " " + m.group(3) + "."      # the NUL keeps a caption from linking to itself
main = re.sub(r"(\\textbf\{|\\emph\{)(Table|Figure) (\d+)\.", caption, main)
NUM = r"\d+(?:\.\d+)*"
def mentions(word, prefix):
    one = lambda n: "\\hyperref[%s]{%s}" % (prefix + n.group().replace(".", "-"), n.group()) if prefix + n.group().replace(".", "-") in labels else n.group()
    return lambda m: m.group(1) + re.sub(NUM, one, m.group(2))
for word, prefix in (("Section", "s-"), ("Table", "t-"), ("Figure", "f-")):
    main = re.sub(r"\b(%ss? )(%s(?:(?:, | and | to )%s)*)" % (word, NUM, NUM), mentions(word, prefix), main)
main = main.replace("\0", "")
main = re.sub(r"\{\[\}(\d+(?:, \d+)*)\{\]\}", lambda m: "{[}" + re.sub(r"\d+", lambda n: "\\hyperlink{ref-%s}{%s}" % (n.group(), n.group()), m.group(1)) + "{]}", main)
refs = re.sub(r"^\{\[\}(\d+)\{\]\} ", lambda m: "\\hypertarget{ref-%s}{{[}%s{]}} " % (m.group(1), m.group(1)), refs, flags=re.M)
tex = main + cut + refs
abs_tex = subprocess.run(["pandoc", "-f", "markdown", "-t", "latex"], input=tex_chars(abstract), capture_output=True, text=True, check=True).stdout
doc = r"""\documentclass[10pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{fontspec,amsmath,amssymb,graphicx,longtable,booktabs,array,calc,microtype,xurl,fvextra,needspace}
\usepackage{xcolor}\definecolor{linkblue}{RGB}{28,36,150}
\usepackage[colorlinks=true,allcolors=linkblue]{hyperref}
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\makeatletter\newsavebox\pandoc@box
\newcommand*\pandocbounded[1]{\sbox\pandoc@box{#1}\Gscale@div\@tempa{\textheight}{\dimexpr\ht\pandoc@box+\dp\pandoc@box\relax}\Gscale@div\@tempb{\linewidth}{\wd\pandoc@box}\ifdim\@tempb\p@<\@tempa\p@\let\@tempa\@tempb\fi\ifdim\@tempa\p@<\p@\scalebox{\@tempa}{\usebox\pandoc@box}\else\usebox{\pandoc@box}\fi}
\makeatother
\setlength{\parindent}{0pt}\setlength{\parskip}{0.55em}\setlength{\emergencystretch}{3em}
\setlength{\LTpre}{0.2em}\setlength{\LTpost}{0.8em}\renewcommand{\arraystretch}{1.15}
\AtBeginEnvironment{longtable}{\small}
\title{TITLE}
\author{Ernesto Cohnen de la Cámara$^{1,2}$ \quad Francisco Novella Fletcher$^{1}$ \\[0.3em] José Miguel Ávila Gómez$^{1}$ \quad Carlos Tomás Ferrer$^{1}$ \\[0.8em]
{\normalsize $^{1}$SqaaS (Squad as a Service SL), Madrid, Spain \quad $^{2}$ixigo} \\[0.2em] {\normalsize Correspondence: \texttt{contact@sqaas.io}}}
\date{22 November 2026}
\begin{document}
\maketitle
\begin{abstract}
ABSTRACT
\end{abstract}
BODY
\end{document}
""".replace("TITLE", title).replace("ABSTRACT", abs_tex).replace("BODY", tex)
open("palabra-mark.tex", "w", encoding="utf8").write(doc)
os.makedirs("tex-build", exist_ok=True)
r = subprocess.run(["tectonic", "--outdir", "tex-build", "palabra-mark.tex"], capture_output=True, text=True)
print("\n".join(l for l in (r.stdout + r.stderr).splitlines() if re.search(r"error|Missing character|Overfull \\hbox \((\d{3,}|[5-9]\d)", l))[:3000])
print("exit", r.returncode)
if r.returncode == 0: os.replace("tex-build/palabra-mark.pdf", "palabra-mark-latex.pdf"); os.rmdir("tex-build")

# arXiv bundle: the source, the figures it uses, and a 00README.json that selects XeLaTeX (the source needs fontspec)
import json, zipfile
figs = sorted(set(re.findall(r"includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", doc)))
readme = {"process": {"compiler": "xelatex"}, "sources": [{"filename": "palabra-mark.tex", "usage": "toplevel"}]}
with zipfile.ZipFile("palabra-mark-arxiv.zip", "w", zipfile.ZIP_DEFLATED) as z:
    z.write("palabra-mark.tex"); z.writestr("00README.json", json.dumps(readme, indent=2))
    for f in figs: z.write(f)
print("arXiv bundle:", ["palabra-mark.tex", "00README.json"] + figs)
