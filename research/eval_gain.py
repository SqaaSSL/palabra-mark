"""DEV speakers: mark strength versus speech quality, with and without the trained detector filter."""
import json
from multiprocessing import Pool
from common import *
from pesq import pesq

K = tuple(map(tuple, json.load(open("results/kernel.json"))["kernel"]))
CH = ["G.711", "AMR-12.2", "AMR-4.75", "Opus-12", "G.723.1-6.3"]
TS = (2, 3, 5, 8)
def utts():
    d = librispeech(); dev, _ = split()
    return [d[s][-1] for s in dev] + [d[s][-2] for s in dev if len(d[s]) > 5]      # not used for filter training

def run(a):
    gain, usek = a; cfg = Config(gain=gain, kernel=K if usek else ()); out = {c: [] for c in CH}; q = []; wr = []
    for i, p in enumerate(utts()):
        x = clip8(p); code = call_code(b"e", "a", "b", str(i)); y, _ = embed(x, code, cfg); q.append(pesq(FS, x, y, "wb"))
        for c in CH:
            D = Detector(through(y, c), cfg); t, z = D.curve(code); out[c].append([z[np.searchsorted(t, T) - 1] for T in TS])
            if c == "G.711": wr.append(max(D.best(call_code(b"e", "x", "y", str(k))) for k in range(30)))
    return dict(gain=gain, trained=usek, pesq=float(np.mean(q)), pesq_min=float(np.min(q)), wrong=float(max(wr)),
                z={c: np.mean(v, 0).tolist() for c, v in out.items()})

if __name__ == "__main__":
    with Pool(8) as p: res = p.map(run, [(g, k) for g in (2.0, 3.0, 4.0, 5.0) for k in (False, True)])
    json.dump(res, open("results/eval_gain.json", "w"), indent=1)
    print("gain filter   PESQ mean/min | mean z after 2/3/5/8 s, per line | highest wrong-code z")
    for r in res:
        print(f"{r['gain']:3.0f}dB {'trained' if r['trained'] else 'plain  '} {r['pesq']:.2f}/{r['pesq_min']:.2f} | " +
              " | ".join(f"{c[:8]} " + "/".join(f"{v:4.1f}" for v in r['z'][c]) for c in CH) + f" | {r['wrong']:.1f}")
