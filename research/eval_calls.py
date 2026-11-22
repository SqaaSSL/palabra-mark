"""Palabra on REAL call recordings (audio that already crossed a phone network), then through the bridge again.
Sources: Gridspace-Stanford Harper Valley (agent side, 8 kHz, CC-BY-4.0) and the NCSU Robocall Audio Dataset.
Writes results/calls.json."""
import glob, json, time
from multiprocessing import Pool
from common import *
from pesq import pesq

CFG, TAU, NWRONG = Config(), 7.0, 100
LINES = {"G.711": ["G.711"], "AMR-12.2": ["AMR-12.2"], "Opus-12": ["Opus-12"],
         "AMR-12.2 > G.711 > Opus-16": ["AMR-12.2", "G.711", "Opus-16"], "AMR-4.75": ["AMR-4.75"]}

def busiest(x, secs=8.0):
    """The 8 s stretch with the most speech (call recordings have long silences). Returns clip, active share."""
    hop = FS // 50; n = len(x) // hop
    e = 10 * np.log10(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    act = (e > e.max() - 35).astype(float); w = int(secs * 50)
    if n <= w: return x, float(act.mean())
    c = np.concatenate([[0], np.cumsum(act)]); s = int(np.argmax(c[w:] - c[:-w]))
    s += int(np.argmax(act[s: s + w]))                       # start where the talker starts, as a greeting does
    s = min(s, n - w)
    return x[s * hop: s * hop + int(secs * FS)], float((c[s + w] - c[s]) / w)

def first_pass(D, code):
    t, z = D.curve(code); ok = np.nonzero(z >= TAU)[0]
    return (float(t[ok[0]]) if len(ok) else None), float(z.max())

def job(a):
    i, path = a
    x, active = busiest(load(path)); x = x / (np.abs(x).max() + 1e-9) * 0.7
    code = call_code(b"calls", "+999555000427", "+999555000010", f"{i}"); rng = np.random.default_rng(5000 + i)
    y, _ = embed(x, code, CFG)
    rec = dict(src=path.split(os.sep)[-2], active=active, pesq_wb=float(pesq(FS, x, y, "wb")), lines={})
    for name, chain in LINES.items():
        D = Detector(bridge(y, chain, None), CFG, max_dur=8.0)
        t, zmax = first_pass(D, code)
        rec["lines"][name] = dict(t=t, z=zmax, null=max(float(D.z(rng.bytes(32))[:, 30:].max()) for _ in range(NWRONG)))
    return rec

if __name__ == "__main__":
    files = sorted(glob.glob(os.path.join(ROOT, "data/calls/*/*.wav"))); t0 = time.time()
    with Pool(12) as p: out = p.map(job, list(enumerate(files)), chunksize=1)
    json.dump(out, open(os.path.join(ROOT, "results/calls.json"), "w"))
    for src in ("harper", "robocall"):
        R = [r for r in out if r["src"] == src]
        print(f"\n{src}: {len(R)} calls, speech share {np.mean([r['active'] for r in R]):.0%}, PESQ-WB {np.mean([r['pesq_wb'] for r in R]):.2f}")
        for name in LINES:
            ts = [r["lines"][name]["t"] for r in R]
            f = lambda s: np.mean([t is not None and t <= s for t in ts])
            med = np.median([t if t is not None else 99 for t in ts])
            print(f"  {name:28s} 3s {f(3):4.0%}  5s {f(5):4.0%}  8s {f(8):4.0%}  median {med:4.1f}s  max wrong-code {max(r['lines'][name]['null'] for r in R):.2f}")
    print(f"{time.time()-t0:.0f} s")
