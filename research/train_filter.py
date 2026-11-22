"""Learns the detector's filter on DEV speakers: a small linear filter over neighbouring tiles that best
recovers the written pattern after a phone codec. Saved to results/kernel.json."""
import json
from multiprocessing import Pool
from common import *
from palabra_mark.core import stft, tile_db, tile_gains, pattern, NFFT, HOP

CFG = Config(mode="quad", tt=6, bw=6, nbands=16, gain=2.0)
CH = ["G.711", "AMR-12.2", "AMR-7.95", "AMR-4.75", "Opus-16", "Opus-12", "G.723.1-6.3", "iLBC-15.2"]
KT, KF = 5, 5

def job(args):
    i, p, ch = args
    x = clip8(p); code = call_code(b"train", ch, p, str(i)); y, _ = embed(x, code, CFG)
    r = through(y, ch); D = Detector(r, CFG)
    f0 = D.starts[int(np.argmax(D.z(code)[:, -1]))]                    # where the mark starts in the received audio
    ntiles = D.rows * CFG.tstep
    L = tile_db(np.abs(stft(r)) ** 2, f0, ntiles, CFG)
    T = tile_gains(pattern(code, D.rows, CFG), CFG) / CFG.gain        # +/-1 per tile
    floor = L.max() - CFG.floor; Lc = np.maximum(L, floor); Lc = Lc - Lc.mean()
    pad = np.pad(Lc, ((KT // 2, KT // 2), (KF // 2, KF // 2)), mode="edge")
    X = np.stack([pad[a:a + L.shape[0], b:b + L.shape[1]] for a in range(KT) for b in range(KF)], -1)
    m = L > floor
    return X[m], T[m]

if __name__ == "__main__":
    d = librispeech(); dev, _ = split()
    jobs = [(i, p, ch) for i, p in enumerate(q for s in dev for q in d[s][:4]) for ch in CH]
    with Pool(16) as pool: out = pool.map(job, jobs)
    X = np.concatenate([o[0] for o in out]); T = np.concatenate([o[1] for o in out])
    w = np.linalg.solve(X.T @ X + 1e-3 * len(X) * np.eye(X.shape[1]), X.T @ T)
    K = w.reshape(KT, KF); K = K / np.abs(K).max()
    json.dump({"kernel": K.tolist(), "cfg": dict(mode=CFG.mode, tt=CFG.tt, bw=CFG.bw, nbands=CFG.nbands), "n": int(len(X)), "channels": CH},
              open("results/kernel.json", "w"), indent=1)
    np.set_printoptions(precision=2, suppress=True, linewidth=150)
    print("trained on", len(X), "tiles from", len(jobs), "marked calls;  rows = time (-2..+2 tiles), cols = frequency (-2..+2 tiles)"); print(K)
