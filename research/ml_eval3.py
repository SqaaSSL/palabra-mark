"""Step 2: scores results/ml_test3.npz with the streaming detector. Needs only numpy, torch and ml_model.py.
Usage: python ml_eval3.py weights.pt [more weights ...] [passes=1|2] [out=results/ml_eval3.json]

The net runs once over each call (passes=1: every second 8 ms frame; passes=2: also the frames between, which
halves the largest timing error from 8 ms to 0). Every start in the first 1.2 s is a hypothesis; the score of a
hypothesis after r rows uses audio up to the end of row r plus the net's look-ahead, and the times reported
count that look-ahead. "analytic" is the same search on the analytic votes alone."""
import sys, json, time, numpy as np, torch
from ml_model import VoteNet3
arg = dict(a.split("=") for a in sys.argv[1:] if "=" in a); W = [a for a in sys.argv[1:] if "=" not in a]
PASSES = int(arg.get("passes", 1)); OUT = arg.get("out", "results/ml_eval3.json"); TAU = 7.0; ROWT = 0.064; LO, QSTEP = -3.5, 3.75 / 255
dev = "cuda" if torch.cuda.is_available() else "cpu"
d = np.load(arg.get("data", "results/ml_test3.npz")); G = d["grid"]; LINES = [str(x) for x in d["lines"]]; kinds = d["kind"]; secs = d["secs"]
S, B, CODE, WRONG = d["S"], d["B"], d["code"], d["wrong"]; n, nl, T, _ = S.shape; STARTS = np.arange(4, 154)      # frames, as Detector
def dense(net, look, s, b):
    """Votes at every frame for the row that ended there: V[t]. Frames not on a pass's grid are left empty (nan)."""
    V = torch.full((len(s), T + 16, 8), float("nan"), device=dev)
    for q in range(PASSES):
        with torch.no_grad(), torch.autocast("cuda", enabled=dev == "cuda"): v = net(s[:, q::2], b[:, q::2]).float()
        m = v.shape[1] - look; V[:, q + 2 * torch.arange(m, device=dev)] = v[:, look:] * (b[:, q::2][:, :m] != 0)
    return V
def score(V, rows, pats):
    """Best score over starts after each row, for each pattern: (patterns, rows). Starts off the grid are skipped."""
    idx = torch.as_tensor(STARTS[:, None] + 7 + 8 * np.arange(rows)[None], device=dev); idx = idx.clamp(max=V.shape[0] - 1)
    v = V[idx]; ok = ~torch.isnan(v[:, 0, 0]); v = torch.nan_to_num(v[ok])                                      # (starts, rows, 8)
    num = torch.cumsum(torch.einsum("hrc,prc->phr", v, pats[:, :rows]), 2); den = torch.sqrt(torch.cumsum((v ** 2).sum(2), 1) + 1e-9)
    return (num / den).max(1).values
def on_grid(z, rows, look):
    t = (np.arange(rows) + 1) * ROWT + look * 0.016
    return [float(z[min(rows - 1, max(0, np.searchsorted(t, g + 1e-9) - 1))]) if (t[0] <= g + 1e-9 and g <= t[-1] + 1e-9) else None for g in G]
models = {"analytic": (None, 0)}
for w in W:
    c = torch.load(w, map_location=dev); net = VoteNet3(c["ch"], c["blocks"], c["look"]).to(dev); net.load_state_dict(c["state"]); net.eval(); models[w.split("/")[-1][:-3]] = (net, c["look"])
out = {k: [] for k in models}; t0 = time.time(); r1 = int(1.0 / ROWT)
for i in range(n):
    rows = int(min(8.0, secs[i]) / ROWT); s = torch.from_numpy(S[i]).to(dev).float() * QSTEP + LO; b = torch.from_numpy(B[i].astype(np.float32)).to(dev)
    pats = torch.from_numpy(np.concatenate([CODE[i][None], WRONG[i]]).astype(np.float32)).to(dev)
    for k, (net, look) in models.items():
        if net is None:
            V = torch.full((nl, T + 16, 8), float("nan"), device=dev)
            for q in range(PASSES): V[:, q:T:2] = b[:, q::2]
        else: V = dense(net, look, s, b)
        rec = {}
        for j, ln in enumerate(LINES):
            z = score(V[j], rows, pats).cpu().numpy(); rec[ln] = dict(z=on_grid(z[0], rows, look), null=[float(x) for x in z[1:, r1 - 1:].max(1)])
        out[k].append(rec)
    if i % 20 == 0: print(i, f"{time.time() - t0:.0f}s", flush=True)
json.dump(dict(grid=G.tolist(), lines=LINES, kind=kinds.tolist(), passes=PASSES, look={k: v[1] for k, v in models.items()}, records=out), open(OUT, "w"))
def tv(zs):
    o = []
    for z in zs:
        z = np.array([-9 if v is None else v for v in z]); h = np.nonzero(z >= TAU)[0]; o.append(G[h[0]] if len(h) else np.nan)
    return np.array(o)
f = lambda t: "/".join(f"{100 * np.mean(t <= x):3.0f}" for x in (2, 3, 5)) + f" {np.nanmedian(t) if np.mean(np.isnan(t)) < .5 else float('nan'):.2f}s"
for kind in ("human", "agent"):
    I = [i for i in range(n) if kinds[i] == kind]; print(f"\n{kind} (n={len(I)}), passes={PASSES}: % verified by 2/3/5 s, median time   " + "   ".join(models))
    for ln in LINES: print(f"  {ln:32} " + "   ".join(f(tv([out[k][i][ln]["z"] for i in I])) for k in models))
for k in models:
    v = np.array([x for r in out[k] for ln in LINES for x in r[ln]["null"]]); print(f"wrong codes, {k}: {len(v):,} trials, highest {v.max():.2f}, >=6: {(v >= 6).sum()}, >=7: {(v >= 7).sum()}")
