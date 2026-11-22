"""Training data for the streaming learned detector (VoteNet3). Writes results/ml_train3.npz.

As ml_data2.py (narrowband and wideband codecs, chains of up to three), with two changes:
  - speakers: the 251 of LibriSpeech train-clean-100 plus the 28 of train-clean-5 (none in the tuning or held-out sets);
  - inputs are causal (ml_feat.py) and kept at a 16 ms step: 0.5 s before the mark, the 6 s of mark, 0.13 s after.
    Step i is frame f0 + 1 + 2 (i - PRE), so pattern row r ends at step PRE + 3 + 4 r."""
import glob, sys, time
from multiprocessing import Pool
from common import *
from palabra_mark.core import pattern
from palabra_mark.channels import WIDE
from ml_data import SECS, ROWS, SINGLE
from ml_data2 import line
from ml_feat import feats, quant, CFG

PRE, POST = 32, 8; N = PRE + 4 * ROWS + POST                    # steps per example (412)
LINES_PER_REC = 3

def job(a):
    i, path = a; rng = np.random.default_rng(9000 + i); out = []; bad = []; n = int(SECS * FS) + FS // 2
    full = load(path); o = int(rng.integers(0, max(1, len(full) - n))); x = full[o:o + n]
    x = x / (np.abs(x).max() + 1e-9) * rng.uniform(0.2, 0.9)
    code = rng.bytes(32); y, _ = embed(x, code, CFG); s = pattern(code, ROWS, CFG).astype(np.int8)
    for _ in range(LINES_PER_REC):
        chain, noise = line(rng)
        try: r = bridge(y, chain, noise, seed=int(rng.integers(1 << 30)))
        except Exception: bad.append(">".join(chain)); continue
        D = Detector(r, CFG, max_dur=SECS); f0 = int(D.starts[int(np.argmax(D.z(code)[:, -1]))]) + int(rng.integers(-1, 2))
        S, B = feats(r); fr = f0 + 1 + 2 * (np.arange(N) - PRE); ok = (fr >= 0) & (fr < len(S)); fr = np.clip(fr, 0, len(S) - 1)
        out.append((quant(S[fr]) * ok[:, None].astype(np.uint8), (B[fr] * ok[:, None]).astype(np.float16), s,
                    int(path.split(os.sep)[-3]), any(c in WIDE for c in chain)))
    return out, bad

if __name__ == "__main__":
    paths = [p for d in ("train-clean-100", "train-clean-5") for p in sorted(glob.glob(os.path.join(ROOT, f"data/LibriSpeech/{d}/*/*/*.flac"))) if os.path.getsize(p) > SECS * 22000]
    if len(sys.argv) > 1: paths = paths[:: max(1, len(paths) // int(sys.argv[1]))][: int(sys.argv[1])]
    res = []; bad = {}; t0 = time.time()
    with Pool(14) as p:
        for k, (o, b) in enumerate(p.imap(job, list(enumerate(paths)), chunksize=4)):
            res += o
            for c in b: bad[c] = bad.get(c, 0) + 1
            if k % 2000 == 0: print(k, len(res), f"{time.time() - t0:.0f}s", flush=True)
    print(len(paths), "recordings ->", len(res), "examples,", len({e[3] for e in res}), "speakers;", f"{np.mean([e[4] for e in res]):.0%} through a wideband codec; {time.time() - t0:.0f}s")
    print("lines that failed:", sum(bad.values()), sorted(bad.items(), key=lambda kv: -kv[1])[:8])
    if len(sys.argv) > 1 and 'OUT' not in os.environ: sys.exit()
    np.savez_compressed(os.environ.get("OUT", "results/ml_train3.npz"), S=np.stack([e[0] for e in res]), B=np.stack([e[1] for e in res]), T=np.stack([e[2] for e in res]),
                        spk=np.array([e[3] for e in res]), wide=np.array([e[4] for e in res]))
