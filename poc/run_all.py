"""Runs the mark test over every file in voices/ and prints one summary table.
Usage: python3 run_all.py"""
import glob, os, sys, numpy as np
from multiprocessing import Pool
from wm import *
from channels import CODECS, through, tandem

LINES = [(n, [n], None) for n in CODECS] + [
    ("Opus 12k -> G.711 -> G.726 32k", ["Opus 12k (VoIP)", "G.711 mu-law (landline)", "G.726 32k"], None),
    ("G.711 + noise (20 dB SNR)", ["G.711 mu-law (landline)"], 20)]
DURS, GAIN, NCODES, NWRONG, PASS = (1.5, 3.0, 5.0), 2.0, 3, 60, 6.0

def one(src):
    x = load(src); rng = np.random.default_rng(abs(hash(src)) % 2**32)
    codes = [call_code(b"demo-secret", "+999555000427", "+999555000010", f"{src}{i}") for i in range(NCODES)]
    res = {}; ctrl = {}
    for dur in DURS:
        marked = [embed(x, c, dur, GAIN)[0] for c in codes]
        for name, chain, noise in LINES:
            res[(name, dur)] = [detect(tandem(y, chain, noise), c, dur)["z"] for y, c in zip(marked, codes)]
        r = through(marked[0], "G.711 mu-law (landline)")
        ctrl[dur] = max([detect(r, rng.bytes(32), dur)["z"] for _ in range(NWRONG)] +
                        [detect(through(x, "G.711 mu-law (landline)"), c, dur)["z"] for c in codes])
    return os.path.basename(src), len(x) / FS, res, ctrl

if __name__ == "__main__":
    srcs = sorted(glob.glob("voices/*"))
    with Pool(min(8, len(srcs))) as p: out = p.map(one, srcs)
    n = len(out) * NCODES
    print(f"{len(out)} voices x {NCODES} call codes = {n} marked calls per cell. Mark strength +/-{GAIN} dB. Pass = z >= {PASS}.\n")
    print(f"{'line':32}" + "".join(f"{f'{d} s':>22}" for d in DURS)); print(f"{'':32}" + "".join(f"{'passed (median z)':>22}" for _ in DURS))
    for name, _, _ in LINES:
        row = ""
        for d in DURS:
            zs = np.concatenate([o[2][(name, d)] for o in out]); row += f"{f'{int((zs >= PASS).sum())}/{n} ({np.median(zs):.1f})':>22}"
        print(f"{name:32}{row}")
    print(f"{'CONTROL highest z (must be < 6)':32}" + "".join(f"{max(o[3][d] for o in out):>22.1f}" for d in DURS))
    print("\nPer voice on a landline (G.711), lowest z of its codes:")
    for nm, secs, res, _ in out:
        print(f"  {nm:22} {secs:4.1f} s " + "".join(f"{min(res[('G.711 mu-law (landline)', d)]):>8.1f}" for d in DURS))
