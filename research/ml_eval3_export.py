"""Step 1 of the held-out evaluation of the streaming detector, run where the codecs are: sends every test call down
the 21 lines of ml_eval2.py and saves the causal inputs (ml_feat.py), the true pattern and 200 wrong patterns per call.
Writes results/ml_test3.npz, which ml_eval3.py scores (on a GPU if there is one)."""
import time
from multiprocessing import Pool
from common import *
from palabra_mark.core import pattern
from eval_final import items, FINAL, GRID, LINES as NB
from eval_wb import LINES as WBL
from ml_eval import KEY, ROWT
from ml_feat import feats, quant

LINES = {**{k: NB[k] for k in KEY}, **WBL}; TMAX = 1016; ROWS = 125; NWRONG = 200
def job(a):
    i, (kind, spk, path) = a
    x = clip8(path) if kind == "human" else (lambda v: v / (np.abs(v).max() + 1e-9) * 0.7)(load(path))
    code = call_code(b"final", "+999555000427", "+999555000010", f"{i}"); y, _ = embed(x, code, FINAL); rng = np.random.default_rng(5000 + i)
    S = np.zeros((len(LINES), TMAX, 96), np.uint8); B = np.zeros((len(LINES), TMAX, 8), np.float16)
    for k, (c, nz) in enumerate(LINES.values()):
        s, b = feats(bridge(y, c, nz)); n = min(TMAX, len(s)); S[k, :n] = quant(s[:n]); B[k, :n] = b[:n]
    wrong = np.stack([pattern(rng.bytes(32), ROWS, FINAL) for _ in range(NWRONG)]).astype(np.int8)
    return kind, len(x) / FS, n, S, B, pattern(code, ROWS, FINAL).astype(np.int8), wrong

if __name__ == "__main__":
    t0 = time.time()
    with Pool(12) as p: R = p.map(job, list(enumerate(items())), chunksize=2)
    np.savez_compressed("results/ml_test3.npz", kind=np.array([r[0] for r in R]), secs=np.array([r[1] for r in R]), frames=np.array([r[2] for r in R]),
                        S=np.stack([r[3] for r in R]), B=np.stack([r[4] for r in R]), code=np.stack([r[5] for r in R]), wrong=np.stack([r[6] for r in R]),
                        lines=np.array(list(LINES)), grid=GRID)
    print(len(R), "calls x", len(LINES), f"lines; {time.time() - t0:.0f}s")
