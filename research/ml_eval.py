"""Held-out evaluation of the learned detector front-end against the analytic detector. Writes results/ml_eval.json."""
import json, time, torch
from common import *
from eval_final import items, FINAL, LINES, GRID
from ml_data import spec_in, base_votes, peak_ref, CFG
from ml_model import VoteNet
from palabra_mark.core import stft, pattern, NFFT, HOP

KEY = ["G.711", "AMR-12.2", "AMR-7.95", "AMR-5.9", "AMR-4.75", "Opus-12", "Opus-8", "Opus-6", "G.723.1-6.3", "AMR-12.2 > G.711 > Opus-16"]
dev = "mps" if torch.backends.mps.is_available() else "cpu"
net = VoteNet().to(dev); net.load_state_dict(torch.load("results/votenet.pt", map_location=dev)); net.eval()
ROWT = CFG.tsec * 2

def learned_votes(r, rows):
    P = np.abs(stft(r)) ** 2; ref = peak_ref(P); starts = np.arange(0, int(1.2 * FS / HOP)) + NFFT // HOP
    import ml_data; ml_data.ROWS = rows; ml_data.NF = rows * 2 * CFG.tt
    S = np.stack([np.clip(ml_data.spec_in(P, f0) - ref, -70, 5) / 20 for f0 in starts]).astype(np.float32)
    B = np.stack([ml_data.base_votes(P, f0, ref) for f0 in starts]).astype(np.float32)
    out = []
    with torch.no_grad():
        for i in range(0, len(starts), 25):
            b = torch.from_numpy(B[i:i + 25]).to(dev); v = net(torch.from_numpy(S[i:i + 25]).to(dev), b) * (b != 0)
            out.append(v.cpu().numpy())
    return np.concatenate(out), B

def curves(V, code, rows):
    s = pattern(code, rows, CFG); return np.cumsum((V * s).sum(2), 1) / np.sqrt(np.cumsum((V ** 2).sum(2), 1) + 1e-9)
def on_grid(z, rows):
    t = (np.arange(rows) + 1) * ROWT
    return [float(z[min(rows - 1, max(0, np.searchsorted(t, g + 1e-9) - 1))]) if g <= t[-1] + 1e-9 else None for g in GRID]

if __name__ == "__main__":
    out = []; t0 = time.time()
    for i, (kind, spk, path) in enumerate(items()):
        x = clip8(path) if kind == "human" else (lambda v: v / (np.abs(v).max() + 1e-9) * 0.7)(load(path))
        secs = len(x) / FS; rows = int(min(8.0, secs) / ROWT); code = call_code(b"final", "+999555000427", "+999555000010", f"{i}")
        y, _ = embed(x, code, FINAL); rng = np.random.default_rng(5000 + i); rec = dict(kind=kind, lines={})
        r1 = max(1, int(1.0 / ROWT))
        for name in KEY:
            chain, noise = LINES[name]; r = bridge(y, chain, noise); V, B = learned_votes(r, rows)
            wrong = [rng.bytes(32) for _ in range(200)]
            rec["lines"][name] = dict(
                learned=on_grid(curves(V, code, rows).max(0), rows), analytic=on_grid(curves(B, code, rows).max(0), rows),
                null_learned=[float(curves(V, w, rows)[:, r1 - 1:].max()) for w in wrong],
                null_analytic=[float(curves(B, w, rows)[:, r1 - 1:].max()) for w in wrong])
        out.append(rec)
        if i % 10 == 0: print(i, f"{time.time()-t0:.0f}s", flush=True)
    json.dump(dict(grid=GRID.tolist(), lines=KEY, records=out), open("results/ml_eval.json", "w"))
    G = GRID; TAU = 7.0
    def tv(zs): 
        o = []
        for z in zs:
            z = np.array([-9 if v is None else v for v in z]); h = np.nonzero(z >= TAU)[0]; o.append(G[h[0]] if len(h) else np.nan)
        return np.array(o)
    for kind in ("human", "agent"):
        rs = [r for r in out if r["kind"] == kind]; print(f"\n{kind} (n={len(rs)}): verified by 2 s / 3 s / 5 s, median time    analytic  ->  learned")
        for ln in KEY:
            a = tv([r["lines"][ln]["analytic"] for r in rs]); l = tv([r["lines"][ln]["learned"] for r in rs])
            f = lambda t: " / ".join(f"{100*np.mean(t<=T):3.0f}%" for T in (2, 3, 5)) + f", {np.nanmedian(t) if np.mean(np.isnan(t))<.5 else float('nan'):.2f}s"
            print(f"  {ln:28} {f(a)}   ->   {f(l)}")
    for k in ("null_analytic", "null_learned"):
        v = np.array([z for r in out for ln in KEY for z in r["lines"][ln][k]]); print(f"{k}: {len(v):,} trials, highest {v.max():.2f}, >=6: {(v>=6).sum()}, >=7: {(v>=7).sum()}, mean {v.mean():.2f}")
