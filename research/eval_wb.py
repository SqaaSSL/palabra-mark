"""Wideband mobile lines (AMR-WB and EVS, as on VoLTE): same held-out recordings, frozen design and pass mark as
eval_final.py. Writes results/wideband.json and prints the table. Build the codecs first: sh setup_codecs.sh"""
import json, sys, time
from multiprocessing import Pool
from common import *
from eval_final import items, curve_on_grid, FINAL, GRID, NWRONG
from palabra_mark.channels import WIDE

TAU = 7.0
LINES = {n: ([n], None) for n in WIDE}
LINES["EVS-13.2 > G.711 > Opus-16"] = (["EVS-13.2", "G.711", "Opus-16"], None)        # mobile caller, landline trunk, web agent
LINES["AMR-WB-12.65 > G.711 > AMR-12.2"] = (["AMR-WB-12.65", "G.711", "AMR-12.2"], None)   # wideband mobile to narrowband mobile
UNMARKED = ("AMR-WB-12.65", "EVS-13.2")

def job(a):
    i, (kind, spk, path) = a
    x = clip8(path) if kind == "human" else (lambda v: v / (np.abs(v).max() + 1e-9) * 0.7)(load(path))
    secs = len(x) / FS; code = call_code(b"final", "+999555000427", "+999555000010", f"{i}")
    rng = np.random.default_rng(1000 + i); rec = dict(kind=kind, spk=spk, secs=secs, lines={})
    y, _ = embed(x, code, FINAL)
    r1 = max(1, int(1.0 / (FINAL.tsec * FINAL.tstep)))
    for name, (chain, noise) in LINES.items():
        D = Detector(bridge(y, chain, noise), FINAL, max_dur=min(8.0, secs))
        rec["lines"][name] = dict(z=curve_on_grid(D, code), null=[float(D.z(rng.bytes(32))[:, r1 - 1:].max()) for _ in range(NWRONG)])
        if name in UNMARKED:
            rec["lines"][name]["unmarked"] = float(Detector(bridge(x, chain, noise), FINAL, max_dur=min(8.0, secs)).z(code)[:, r1 - 1:].max())
    return rec

def report(R):
    G = np.array(R["grid"])
    def tv(z):
        hit = np.nonzero(np.array([-9 if v is None else v for v in z]) >= TAU)[0]
        return G[hit[0]] if len(hit) else np.nan
    for kind in ("human", "agent"):
        rs = [r for r in R["records"] if r["kind"] == kind]
        print(f"\n{kind} (n = {len(rs)})\n| Line | 1 s | 2 s | 3 s | 5 s | 8 s | Median time to verify |\n|---|---|---|---|---|---|---|")
        for ln in R["lines"]:
            t = np.array([tv(r["lines"][ln]["z"]) for r in rs]); med = np.nanmedian(t) if np.mean(np.isnan(t)) < 0.5 else np.nan
            print(f"| {ln} | " + " | ".join(f"{100 * np.mean(t <= T):.0f}%" for T in (1, 2, 3, 5, 99)) + f" | {'%.2f s' % med if med == med else 'not reached'} |")
    null = np.array([v for r in R["records"] for ln in R["lines"] for v in r["lines"][ln]["null"]])
    unm = [r["lines"][ln]["unmarked"] for r in R["records"] for ln in UNMARKED]
    print(f"\nwrong codes: {len(null):,} trials, highest z {null.max():.2f}, at or above {TAU:.0f}: {(null >= TAU).sum()}; "
          f"right code on unmarked audio: {len(unm)} trials, highest z {max(unm):.2f}")

if __name__ == "__main__":
    if "--report" not in sys.argv:
        its = list(enumerate(items())); t0 = time.time()
        with Pool(8) as p: out = p.map(job, its, chunksize=1)
        json.dump(dict(grid=GRID.tolist(), lines=list(LINES), records=out), open("results/wideband.json", "w"))
        print(len(out), f"calls; {time.time() - t0:.0f} s")
    report(json.load(open("results/wideband.json")))
