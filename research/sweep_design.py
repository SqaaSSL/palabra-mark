"""Design sweep on the DEV speakers only: which tile shape and vote type survives phone codecs best?"""
import itertools, json
from multiprocessing import Pool
from common import *
from pesq import pesq

CH = ["G.711", "AMR-12.2", "AMR-4.75", "Opus-12", "G.723.1-6.3"]
def utts():
    d = librispeech(); dev, _ = split()
    return [d[s][0] for s in dev]

def run(args):
    mode, tt, bw = args
    nb = (96 // bw) // 2 * 2
    cfg = Config(mode=mode, tt=tt, bw=bw, nbands=nb)
    z5 = {c: [] for c in CH}; z8 = {c: [] for c in CH}; q = []; wr = []
    for i, p in enumerate(utts()):
        x = clip8(p); code = call_code(b"dev", "a", "b", str(i)); y, _ = embed(x, code, cfg)
        q.append(pesq(FS, x, y, "wb"))
        for c in CH:
            D = Detector(through(y, c), cfg); t, z = D.curve(code)
            z5[c].append(z[np.searchsorted(t, 5.0) - 1]); z8[c].append(z[-1])
            if c == "G.711": wr.append(max(D.best(call_code(b"dev", "x", "y", str(k))) for k in range(30)))
    return dict(mode=mode, tt=tt, bw=bw, pesq=float(np.mean(q)), wrong=float(np.max(wr)),
                z5={c: float(np.mean(v)) for c, v in z5.items()}, z8={c: float(np.mean(v)) for c, v in z8.items()})

if __name__ == "__main__":
    grid = list(itertools.product(["pair", "tpair", "quad"], [4, 6, 8, 12], [4, 6, 8, 12]))
    with Pool(16) as p: res = p.map(run, grid)
    json.dump(res, open("results/sweep_design.json", "w"), indent=1)
    res.sort(key=lambda r: -np.mean(list(r["z8"].values())))
    print(f"{'mode':5} {'ms':>4} {'Hz':>4} {'PESQ':>5} | " + " ".join(f"{c:>11}" for c in CH) + " |  mean  (z after 8 s; z after 5 s in brackets)   wrongmax")
    for r in res:
        print(f"{r['mode']:5} {r['tt']*8:>4} {r['bw']*31:>4} {r['pesq']:5.2f} | " + " ".join(f"{r['z8'][c]:5.1f}({r['z5'][c]:4.1f})" for c in CH) +
              f" | {np.mean(list(r['z8'].values())):5.1f}   {r['wrong']:.1f}")
