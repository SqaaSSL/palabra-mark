"""Final evaluation on HELD-OUT speakers and on synthetic agent voices. Writes results/final.json."""
import glob, json, time
from multiprocessing import Pool
from common import *
from pesq import pesq

FINAL = Config()                                                    # frozen design
V0 = Config(mode="pair", tt=4, bw=6, nbands=16, gain=2.0, margin=0.0)   # the first proof of concept, for comparison
LINES = {n: ([n], None) for n in ["clean", "G.711", "G.726-32", "AMR-12.2", "AMR-7.95", "AMR-5.9", "AMR-4.75",
                                  "Opus-24", "Opus-16", "Opus-12", "Opus-8", "Opus-6", "iLBC-15.2", "G.723.1-6.3"]}
LINES["AMR-12.2 > G.711 > Opus-16"] = (["AMR-12.2", "G.711", "Opus-16"], None)
LINES["G.711 > AMR-7.95 + noise 20dB"] = (["G.711", "AMR-7.95"], 20)
V0_LINES = ["G.711", "AMR-12.2", "AMR-4.75", "Opus-12", "G.723.1-6.3"]
NWRONG, GRID = 200, np.arange(0.5, 8.01, 0.25)

def items():
    d = librispeech(); _, test = split()
    out = [("human", s, p) for s in test for p in d[s]]
    out += [("agent", os.path.basename(p), p) for p in sorted(glob.glob(os.path.join(ROOT, "../poc/voices/*")))]
    return out

def curve_on_grid(D, code):
    t, z = D.curve(code)
    return [float(z[min(len(z) - 1, max(0, np.searchsorted(t, g + 1e-9) - 1))]) if g <= t[-1] + 1e-9 else None for g in GRID]

def job(a):
    i, (kind, spk, path) = a
    x = clip8(path) if kind == "human" else (lambda v: v / (np.abs(v).max() + 1e-9) * 0.7)(load(path))
    secs = len(x) / FS; code = call_code(b"final", "+999555000427", "+999555000010", f"{i}")
    rng = np.random.default_rng(1000 + i); rec = dict(kind=kind, spk=spk, secs=secs, lines={}, v0={})
    y, _ = embed(x, code, FINAL)
    rec["pesq_wb"] = float(pesq(FS, x, y, "wb"))
    seg = slice(0, len(x)); rec["snr_db"] = float(10 * np.log10(np.sum(x ** 2) / np.sum((y - x) ** 2)))
    for name, (chain, noise) in LINES.items():
        r = bridge(y, chain, noise); D = Detector(r, FINAL, max_dur=min(8.0, secs))
        r1 = max(1, int(1.0 / (FINAL.tsec * FINAL.tstep)))             # null is taken as the worst case from 1 s onwards
        null = [float(D.z(rng.bytes(32))[:, r1 - 1:].max()) for _ in range(NWRONG)]
        rec["lines"][name] = dict(z=curve_on_grid(D, code), null=null)
        if name in ("G.711", "AMR-12.2", "Opus-12"):                   # the right code on audio that was never marked
            rec["lines"][name]["unmarked"] = float(Detector(bridge(x, chain, noise), FINAL, max_dur=min(8.0, secs)).z(code)[:, r1 - 1:].max())
    y0, _ = embed(x, code, V0); rec["v0_pesq_wb"] = float(pesq(FS, x, y0, "wb"))
    for name in V0_LINES:
        rec["v0"][name] = curve_on_grid(Detector(through(y0, name), V0, max_dur=min(8.0, secs)), code)
    return rec

if __name__ == "__main__":
    its = list(enumerate(items())); t0 = time.time()
    with Pool(16) as p: out = p.map(job, its, chunksize=1)
    json.dump(dict(grid=GRID.tolist(), lines=list(LINES), cfg=FINAL.__dict__ | {"version": "v1"}, records=out), open("results/final.json", "w"))
    print(len(out), "calls,", sum(r["kind"] == "human" for r in out), "human,", sum(r["kind"] == "agent" for r in out), f"agent; {time.time()-t0:.0f} s")
