"""Held-out evaluation of the second learned detector (VoteNet2, ml_train2.py) on the narrowband lines of ml_eval.py
and the wideband lines of eval_wb.py, next to the analytic detector and the first learned detector (whose results are read from ml_eval.json and ml_eval_wb.json).
Usage: python ml_eval2.py [weights=results/votenet2.pt]. Writes results/ml_eval2.json."""
import json, sys, time, torch
from multiprocessing import Pool
from common import *
from eval_final import items, FINAL, GRID, LINES as NB
from eval_wb import LINES as WBL
import ml_eval
from ml_eval import learned_votes, curves, on_grid, ROWT, KEY, dev
from ml_model import VoteNet, VoteNet2

LINES = {**{k: NB[k] for k in KEY}, **WBL}; TAU = 7.0
def received(a):
    i, (kind, spk, path) = a
    x = clip8(path) if kind == "human" else (lambda v: v / (np.abs(v).max() + 1e-9) * 0.7)(load(path))
    code = call_code(b"final", "+999555000427", "+999555000010", f"{i}"); y, _ = embed(x, code, FINAL)
    return kind, len(x) / FS, code, {n: bridge(y, c, nz) for n, (c, nz) in LINES.items()}

if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "results/votenet2.pt"
    new = VoteNet2().to(dev); new.load_state_dict(torch.load(w, map_location=dev)); new.eval(); ml_eval.net = new
    out = []; t0 = time.time()
    with Pool(12) as p:
        for i, (kind, secs, code, recs) in enumerate(p.imap(received, list(enumerate(items())))):
            rows = int(min(8.0, secs) / ROWT); rng = np.random.default_rng(5000 + i); rec = dict(kind=kind, lines={}); r1 = max(1, int(1.0 / ROWT))
            for name, r in recs.items():
                V2, B = learned_votes(r, rows)
                wrong = [rng.bytes(32) for _ in range(200)]; e = {}
                for k, V in (("analytic", B), ("learned2", V2)):
                    e[k] = on_grid(curves(V, code, rows).max(0), rows); e["null_" + k] = [float(curves(V, x, rows)[:, r1 - 1:].max()) for x in wrong]
                rec["lines"][name] = e
            out.append(rec)
            if i % 10 == 0: print(i, f"{time.time() - t0:.0f}s", flush=True)
    json.dump(dict(grid=GRID.tolist(), lines=list(LINES), weights=w, records=out), open("results/ml_eval2.json", "w"))
    def tv(zs):
        o = []
        for z in zs:
            z = np.array([-9 if v is None else v for v in z]); h = np.nonzero(z >= TAU)[0]; o.append(GRID[h[0]] if len(h) else np.nan)
        return np.array(o)
    f = lambda t: " / ".join(f"{100 * np.mean(t <= T):3.0f}%" for T in (2, 3, 5)) + f", {np.nanmedian(t) if np.mean(np.isnan(t)) < .5 else float('nan'):.2f}s"
    rs1 = [dict(kind=a["kind"], lines={**a["lines"], **b["lines"]}) for a, b in zip(json.load(open("results/ml_eval.json"))["records"], json.load(open("results/ml_eval_wb.json"))["records"])]   # first learned detector: already measured
    for kind in ("human", "agent"):
        rs = [r for r in out if r["kind"] == kind]; print(f"\n{kind} (n={len(rs)}): verified by 2 s / 3 s / 5 s, median time    analytic  ->  learned  ->  learned 2")
        for ln in LINES:
            col = [[r["lines"][ln]["analytic"] for r in rs], [r["lines"][ln]["learned"] for r in rs1 if r["kind"] == kind], [r["lines"][ln]["learned2"] for r in rs]]
            print(f"  {ln:32} " + "   ->   ".join(f(tv(c)) for c in col))
    for k in ("null_analytic", "null_learned2"):
        v = np.array([z for r in out for ln in LINES for z in r["lines"][ln][k]]); print(f"{k}: {len(v):,} trials, highest {v.max():.2f}, >=6: {(v >= 6).sum()}, >=7: {(v >= 7).sum()}, mean {v.mean():.2f}")
