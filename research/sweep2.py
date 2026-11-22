"""DEV speakers: smaller tiles, stronger marks, and informed embedding, at matched speech quality."""
import json
from multiprocessing import Pool
from common import *
from pesq import pesq

CH = ["G.711", "AMR-12.2", "AMR-4.75", "Opus-12", "G.723.1-6.3"]; TS = (2, 3, 5, 8)
def utts():
    d = librispeech(); dev, _ = split()
    return [d[s][-1] for s in dev] + [d[s][-2] for s in dev if len(d[s]) > 5]
def run(kw):
    cfg = Config(**kw); out = {c: [] for c in CH}; q = []; wr = []
    for i, p in enumerate(utts()):
        x = clip8(p); code = call_code(b"e", "a", "b", str(i)); y, _ = embed(x, code, cfg); q.append(pesq(FS, x, y, "wb"))
        for c in CH:
            D = Detector(through(y, c), cfg); t, z = D.curve(code); out[c].append([z[np.searchsorted(t, T) - 1] for T in TS])
            if c == "G.711": wr.append(max(D.best(call_code(b"e", "x", "y", str(k))) for k in range(30)))
    return dict(kw=kw, pesq=float(np.mean(q)), pesq_min=float(np.min(q)), wrong=float(max(wr)), z={c: np.mean(v, 0).tolist() for c, v in out.items()})
if __name__ == "__main__":
    grid = []
    for tt, bw in [(6, 6), (4, 6), (4, 4), (6, 4), (3, 4)]:
        nb = (96 // bw) // 2 * 2
        for g in (3.0, 4.0): grid.append(dict(tt=tt, bw=bw, nbands=nb, gain=g))
        for m in (6.0, 10.0, 14.0): grid.append(dict(tt=tt, bw=bw, nbands=nb, margin=m, gmax=5.0))
    with Pool(16) as p: res = p.map(run, grid)
    json.dump(res, open("results/sweep2.json", "w"), indent=1)
    print(f"{'tile':>10} {'embedding':>14} {'PESQ':>10} | mean z after 2/3/5/8 s per line | mean z@3s | wrong")
    for r in res:
        k = r["kw"]; e = f"informed {k['margin']:.0f}dB" if "margin" in k else f"fixed {k['gain']:.0f}dB"
        print(f"{k['tt']*8:3}msx{k['bw']*31:3}Hz {e:>14} {r['pesq']:.2f}/{r['pesq_min']:.2f} | " +
              " | ".join(f"{c[:8]} " + "/".join(f"{v:4.1f}" for v in r['z'][c]) for c in CH) + f" | {np.mean([r['z'][c][1] for c in CH]):4.1f} | {r['wrong']:.1f}")
