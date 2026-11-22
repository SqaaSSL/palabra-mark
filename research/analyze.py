"""Turns results/final.json into the tables and figures of the paper."""
import json, os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from math import erfc, sqrt

R = json.load(open("results/final.json")); G = np.array(R["grid"]); recs = R["records"]; LINES = R["lines"]
TAU = 7.0; OUT = "../paper/figures"; os.makedirs(OUT, exist_ok=True)
COB, INK, ICE, RED = "#2A2FD0", "#12143A", "#8F98FF", "#C4372C"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 160, "font.family": "Helvetica"})

def zmat(rs, line, key="lines"):
    return np.array([[np.nan if v is None else v for v in (r[key][line]["z"] if key == "lines" else r[key][line])] for r in rs])
def t_verify(Z):
    """First time the running maximum of z crosses TAU (nan if never)."""
    out = []
    for z in Z:
        hit = np.nonzero(np.nan_to_num(z, nan=-9) >= TAU)[0]; out.append(G[hit[0]] if len(hit) else np.nan)
    return np.array(out)
def rate_by(tv, T): return float(np.mean(tv <= T))            # nan compares False: never verified counts as a miss

md = []
for kind, label in (("human", "Human speech, held-out speakers"), ("agent", "Synthetic agent voices")):
    rs = [r for r in recs if r["kind"] == kind]
    md.append(f"\n**{label}** (n = {len(rs)} calls; mark quality PESQ-WB mean {np.mean([r['pesq_wb'] for r in rs]):.2f}, min {np.min([r['pesq_wb'] for r in rs]):.2f})\n")
    md.append("| Line | verified by 1 s | 2 s | 3 s | 5 s | end | median time to verify | median z at 3 s |"); md.append("|---|---|---|---|---|---|---|---|")
    for ln in LINES:
        Z = zmat(rs, ln); tv = t_verify(Z); i3 = np.searchsorted(G, 3.0)
        med = np.nanmedian(tv) if np.mean(np.isnan(tv)) < 0.5 else float("nan")
        md.append(f"| {ln} | " + " | ".join(f"{100*rate_by(tv, T):.0f}%" for T in (1, 2, 3, 5, 99)) +
                  f" | {'%.2f s' % med if med == med else 'not reached'} | {np.nanmedian(Z[:, i3]):.1f} |")
# false alarms
null = np.array([v for r in recs for ln in LINES for v in r["lines"][ln]["null"]])
unm = np.array([r["lines"][ln]["unmarked"] for r in recs for ln in LINES if "unmarked" in r["lines"][ln]])
mu, sd = null.mean(), null.std()
LOOKS = 150 * len(G)                                  # candidate starts x decision times
bound = LOOKS * np.exp(-TAU ** 2 / 2)                 # Hoeffding bound for a sum of keyed +/-1 votes, union over looks
md.append(f"\n**False alarms.** {len(null):,} wrong-code trials (worst case over start offsets and all listening times from 1 s): highest z = {null.max():.2f}, "
          f"mean {mu:.2f}, s.d. {sd:.2f}; trials at or above {TAU:.0f}: {(null >= TAU).sum()}. Right code on unmarked audio ({len(unm)} trials): highest z = {unm.max():.2f}. "
          f"Trials at or above 6: {(null >= 6).sum()}; at or above 5.5: {(null >= 5.5).sum()}. "
          f"Guaranteed bound on the false-alarm probability per wrong code at z = {TAU:.0f}: {LOOKS} looks x exp(-z^2/2) = {bound:.1e}.")
for kind in ("human", "agent"):
    rs = [r for r in recs if r["kind"] == kind]
    md.append(f"\n{kind}: share verified within 3 s at pass mark 6 instead of 7: " + ", ".join(
        f"{ln} {100*np.mean([ (lambda z: (np.nonzero(np.nan_to_num(z, nan=-9)[:np.searchsorted(G,3.0)+1] >= 6)[0].size>0))(z) for z in zmat(rs, ln)]):.0f}%" for ln in ("AMR-12.2","AMR-4.75","Opus-12","Opus-6","G.723.1-6.3")))
# v0 comparison
rsH = [r for r in recs if r["kind"] == "human"]
md.append("\n**First proof of concept versus final engine** (human speech; share verified within 3 s / 5 s)\n"); md.append("| Line | first PoC | final engine |"); md.append("|---|---|---|")
for ln in recs[0]["v0"]:
    a = t_verify(zmat(rsH, ln, "v0")); b = t_verify(zmat(rsH, ln))
    md.append(f"| {ln} | {100*rate_by(a,3):.0f}% / {100*rate_by(a,5):.0f}% | {100*rate_by(b,3):.0f}% / {100*rate_by(b,5):.0f}% |")
md.append(f"\nPESQ-WB of the mark: first PoC {np.mean([r['v0_pesq_wb'] for r in rsH]):.2f}, final {np.mean([r['pesq_wb'] for r in rsH]):.2f}. "
          f"SNR of the final mark: {np.mean([r['snr_db'] for r in recs]):.1f} dB.")
open("results/tables.md", "w").write("\n".join(md)); print("\n".join(md))

# ---- figures
SHOW = ["G.711", "AMR-12.2", "Opus-12", "AMR-4.75", "G.723.1-6.3", "Opus-6"]
cols = [COB, "#5B63E6", ICE, "#E08A2B", RED, "#888"]
fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.6), sharey=True)
for a, kind, ttl in zip(ax, ("human", "agent"), ("Human speech (held-out speakers)", "Synthetic agent voices")):
    rs = [r for r in recs if r["kind"] == kind]
    for ln, c in zip(SHOW, cols):
        Z = zmat(rs, ln); ok = np.mean(~np.isnan(Z), 0) > 0.5
        a.plot(G[ok], np.nanmedian(Z, 0)[ok], color=c, lw=2, label=ln)
        a.fill_between(G[ok], np.nanpercentile(Z, 25, 0)[ok], np.nanpercentile(Z, 75, 0)[ok], color=c, alpha=.10, lw=0)
    a.axhline(TAU, color=INK, ls="--", lw=1); a.text(7.9, TAU + .3, "pass", ha="right", fontsize=9)
    a.set_title(ttl, loc="left", fontsize=10); a.set_xlabel("seconds of speech heard"); a.set_xlim(0.5, 8)
ax[0].set_ylabel("match score z (median, quartiles)"); ax[0].legend(frameon=False, fontsize=8, ncol=2, loc="upper left")
fig.tight_layout(); fig.savefig(f"{OUT}/fig1_score_over_time.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(6.2, 4.6))
M = np.array([[rate_by(t_verify(zmat(rsH, ln)), T) for T in (1, 2, 3, 5, 8)] for ln in LINES])
im = ax.imshow(M, cmap="Blues", vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(5)); ax.set_xticklabels(["1 s", "2 s", "3 s", "5 s", "8 s"]); ax.set_yticks(range(len(LINES))); ax.set_yticklabels(LINES, fontsize=8)
for i in range(M.shape[0]):
    for j in range(M.shape[1]): ax.text(j, i, f"{100*M[i,j]:.0f}", ha="center", va="center", fontsize=8, color="white" if M[i, j] > .55 else INK)
ax.set_title("Calls verified by time (%, human speech)", loc="left", fontsize=10); ax.spines[:].set_visible(False)
fig.tight_layout(); fig.savefig(f"{OUT}/fig2_verified_by_time.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(6.2, 3.4))
i3 = np.searchsorted(G, 3.0)
true3 = np.concatenate([zmat(recs, ln)[:, i3] for ln in ("G.711", "AMR-12.2", "Opus-12")]); true3 = true3[~np.isnan(true3)]
ax.hist(null, bins=80, density=True, color="#999", alpha=.8, label=f"wrong code, worst case ({len(null):,})")
ax.hist(true3, bins=40, density=True, color=COB, alpha=.8, label="right code after 3 s (G.711, AMR-12.2, Opus-12)")
ax.axvline(TAU, color=INK, ls="--", lw=1); ax.set_xlabel("match score z"); ax.set_yticks([]); ax.spines["left"].set_visible(False)
ax.legend(frameon=False, fontsize=8); fig.tight_layout(); fig.savefig(f"{OUT}/fig3_null_vs_marked.png"); plt.close(fig)

S = json.load(open("results/sweep2.json")); fig, ax = plt.subplots(figsize=(6.2, 3.6))
for r in S:
    k = r["kw"]; inf = "margin" in k; z3 = np.mean([v[1] for v in r["z"].values()])
    ax.scatter(r["pesq"], z3, s=40, color=COB if inf else "#aaa", marker="o" if inf else "s", zorder=3)
ax.scatter([], [], color=COB, label="informed embedding"); ax.scatter([], [], color="#aaa", marker="s", label="fixed strength")
ax.set_xlabel("speech quality of the marked audio (PESQ-WB, 4.64 = identical)"); ax.set_ylabel("mean z after 3 s, five codecs")
ax.invert_xaxis(); ax.legend(frameon=False, fontsize=8); ax.set_title("Design sweep on the tuning speakers", loc="left", fontsize=10)
fig.tight_layout(); fig.savefig(f"{OUT}/fig4_quality_vs_robustness.png"); plt.close(fig)
print("figures written to", OUT)
