"""The streaming marker against the file embedder: same held-out recordings, lines, detector and pass mark.
The voice is pushed in 20 ms frames. Writes results/marker.json and prints the table."""
import json, sys, time
from multiprocessing import Pool
from common import *
from eval_final import items, curve_on_grid, FINAL, GRID
from palabra_mark import StreamMarker
from pesq import pesq

TAU = 7.0
LINES = {n: [n] for n in ["G.711", "Opus-12", "AMR-12.2", "AMR-WB-12.65", "EVS-13.2", "AMR-4.75"]}
LINES["AMR-12.2 > G.711 > Opus-16"] = ["AMR-12.2", "G.711", "Opus-16"]
def stream(x, code, **kw):
    m = StreamMarker(code, **kw); out = [m.push(x[i:i + 320]) for i in range(0, len(x), 320)]
    return np.concatenate(out + [m.flush()])
MARKERS = {"file": lambda x, c: embed(x, c, FINAL)[0],
           "stream, 80 ms": lambda x, c: stream(x, c),
           "stream, 24 ms": lambda x, c: stream(x, c, lookahead=False, gain=4.0)}

def job(a):
    i, (kind, spk, path) = a
    x = clip8(path) if kind == "human" else (lambda v: v / (np.abs(v).max() + 1e-9) * 0.7)(load(path))
    secs = len(x) / FS; code = call_code(b"final", "+999555000427", "+999555000010", f"{i}")
    rng = np.random.default_rng(3000 + i); rec = dict(kind=kind, secs=secs, m={})
    r1 = max(1, int(1.0 / (FINAL.tsec * FINAL.tstep)))
    for name, mark in MARKERS.items():
        y = mark(x, code); assert len(y) == len(x)
        e = dict(pesq_wb=float(pesq(FS, x, y, "wb")), snr_db=float(10 * np.log10(np.sum(x ** 2) / np.sum((y - x) ** 2))), z={}, null=[])
        for ln, chain in LINES.items():
            D = Detector(bridge(y, chain), FINAL, max_dur=min(8.0, secs)); e["z"][ln] = curve_on_grid(D, code)
            e["null"] += [float(D.z(rng.bytes(32))[:, r1 - 1:].max()) for _ in range(50)]
        rec["m"][name] = e
    return rec

def report(R):
    G = np.array(R["grid"])
    def tv(z):
        hit = np.nonzero(np.array([-9 if v is None else v for v in z]) >= TAU)[0]
        return G[hit[0]] if len(hit) else np.nan
    for kind in ("human", "agent"):
        rs = [r for r in R["records"] if r["kind"] == kind]
        print(f"\n{kind} (n = {len(rs)}): verified within 3 s / 5 s, median time")
        print("| Line | " + " | ".join(MARKERS) + " |\n|---|" + "---|" * len(MARKERS))
        for ln in LINES:
            cells = []
            for m in MARKERS:
                t = np.array([tv(r["m"][m]["z"][ln]) for r in rs]); med = np.nanmedian(t) if np.mean(np.isnan(t)) < 0.5 else np.nan
                cells.append(f"{100 * np.mean(t <= 3):.0f}% / {100 * np.mean(t <= 5):.0f}%, {med:.2f} s")
            print(f"| {ln} | " + " | ".join(cells) + " |")
        print("| PESQ-WB, mean (min) | " + " | ".join(f"{np.mean([r['m'][m]['pesq_wb'] for r in rs]):.2f} ({np.min([r['m'][m]['pesq_wb'] for r in rs]):.2f})" for m in MARKERS) + " |")
        print("| Signal-to-change, dB | " + " | ".join(f"{np.mean([r['m'][m]['snr_db'] for r in rs]):.1f}" for m in MARKERS) + " |")
    for m in MARKERS:
        v = np.array([z for r in R["records"] for z in r["m"][m]["null"]]); print(f"wrong codes, {m}: {len(v):,} trials, highest {v.max():.2f}")

if __name__ == "__main__":
    if "--report" not in sys.argv:
        t0 = time.time()
        with Pool(8) as p: out = p.map(job, list(enumerate(items())), chunksize=1)
        json.dump(dict(grid=GRID.tolist(), lines=list(LINES), records=out), open("results/marker.json", "w")); print(f"{len(out)} calls; {time.time() - t0:.0f} s")
    report(json.load(open("results/marker.json")))
