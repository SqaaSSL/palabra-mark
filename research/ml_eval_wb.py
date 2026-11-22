"""The learned detector of ml_eval.py on the wideband mobile lines of eval_wb.py (AMR-WB and EVS).
The network was trained on narrowband codecs only and is used as it is. Writes results/ml_eval_wb.json."""
import json, time
from common import *
from eval_final import items, FINAL, GRID
from eval_wb import LINES
from ml_eval import learned_votes, curves, on_grid, ROWT

TAU = 7.0
if __name__ == "__main__":
    out = []; t0 = time.time()
    for i, (kind, spk, path) in enumerate(items()):
        x = clip8(path) if kind == "human" else (lambda v: v / (np.abs(v).max() + 1e-9) * 0.7)(load(path))
        secs = len(x) / FS; rows = int(min(8.0, secs) / ROWT); code = call_code(b"final", "+999555000427", "+999555000010", f"{i}")
        y, _ = embed(x, code, FINAL); rng = np.random.default_rng(5000 + i); rec = dict(kind=kind, lines={})
        r1 = max(1, int(1.0 / ROWT))
        for name, (chain, noise) in LINES.items():
            V, B = learned_votes(bridge(y, chain, noise), rows); wrong = [rng.bytes(32) for _ in range(200)]
            rec["lines"][name] = dict(
                learned=on_grid(curves(V, code, rows).max(0), rows), analytic=on_grid(curves(B, code, rows).max(0), rows),
                null_learned=[float(curves(V, w, rows)[:, r1 - 1:].max()) for w in wrong],
                null_analytic=[float(curves(B, w, rows)[:, r1 - 1:].max()) for w in wrong])
        out.append(rec)
        if i % 20 == 0: print(i, f"{time.time() - t0:.0f}s", flush=True)
    json.dump(dict(grid=GRID.tolist(), lines=list(LINES), records=out), open("results/ml_eval_wb.json", "w"))
    def tv(zs):
        o = []
        for z in zs:
            z = np.array([-9 if v is None else v for v in z]); h = np.nonzero(z >= TAU)[0]; o.append(GRID[h[0]] if len(h) else np.nan)
        return np.array(o)
    f = lambda t: " / ".join(f"{100 * np.mean(t <= T):3.0f}%" for T in (2, 3, 5, 99)) + f", {np.nanmedian(t) if np.mean(np.isnan(t)) < .5 else float('nan'):.2f}s"
    for kind in ("human", "agent"):
        rs = [r for r in out if r["kind"] == kind]; print(f"\n{kind} (n={len(rs)}): verified by 2 s / 3 s / 5 s / end, median time    analytic  ->  learned")
        for ln in LINES:
            print(f"  {ln:32} {f(tv([r['lines'][ln]['analytic'] for r in rs]))}   ->   {f(tv([r['lines'][ln]['learned'] for r in rs]))}")
    for k in ("null_analytic", "null_learned"):
        v = np.array([z for r in out for ln in LINES for z in r["lines"][ln][k]]); print(f"{k}: {len(v):,} trials, highest {v.max():.2f}, >=6: {(v >= 6).sum()}, >=7: {(v >= 7).sum()}")
