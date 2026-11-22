"""Builds training data for a learned detector front-end: marked speech sent through real codecs.
Speakers come from train-clean-5, which shares no speaker with the tuning or held-out sets."""
import glob, sys
from multiprocessing import Pool
from common import *
from palabra_mark.core import stft, tile_db, features, pattern, NFFT, HOP

CFG = Config(); SECS = 6.0; ROWS = int(SECS / (CFG.tsec * 2)); NF = ROWS * 2 * CFG.tt; NBIN = CFG.nbands * CFG.bw
SINGLE = ["G.711", "G.726-32", "AMR-12.2", "AMR-7.95", "AMR-5.9", "AMR-4.75", "Opus-24", "Opus-16", "Opus-12", "Opus-8", "Opus-6", "iLBC-15.2", "G.723.1-6.3"]

def spec_in(P, f0):
    """Network input: log power of the phone band, frames x bins, relative to the recording's peak, scaled to about [-3, 0]."""
    S = 10 * np.log10(P[f0:f0 + NF, CFG.bin0:CFG.bin0 + NBIN] + 1e-12)
    if S.shape[0] < NF: S = np.vstack([S, np.full((NF - S.shape[0], NBIN), -200.0)])
    return S
def base_votes(P, f0, ref):
    f, a = features(tile_db(P, f0, ROWS * 2, CFG), CFG, ref)
    n = max(a.sum(), 1); mu = (a * f).sum() / n; sd = np.sqrt((a * (f - mu) ** 2).sum() / n) + 1e-9
    return np.clip((f - mu) / sd, -CFG.clip, CFG.clip) * a
def peak_ref(P): return 10 * np.log10(P[:, CFG.bin0:CFG.bin0 + NBIN].reshape(P.shape[0], CFG.nbands, CFG.bw).sum(2).max() * CFG.tt + 1e-12)

def job(a):
    i, path = a; rng = np.random.default_rng(i); out = []
    x = load(path)[: int(SECS * FS) + FS // 2]; x = x / (np.abs(x).max() + 1e-9) * rng.uniform(0.3, 0.8)
    code = rng.bytes(32); y, _ = embed(x, code, CFG); s = pattern(code, ROWS, CFG)
    for _ in range(3):
        chain = [SINGLE[rng.integers(len(SINGLE))]]
        if rng.random() < 0.25: chain.append(SINGLE[rng.integers(len(SINGLE))])
        try: r = bridge(y, chain, rng.uniform(15, 35) if rng.random() < 0.3 else None, seed=int(rng.integers(1 << 30)))
        except Exception: continue
        D = Detector(r, CFG, max_dur=SECS); f0 = int(D.starts[int(np.argmax(D.z(code)[:, -1]))]) + int(rng.integers(-1, 2))
        P = np.abs(stft(r)) ** 2; ref = peak_ref(P)
        out.append(((np.clip(spec_in(P, f0) - ref, -70, 5) / 20).astype(np.float16), base_votes(P, f0, ref).astype(np.float16), s.astype(np.int8)))
    return out

if __name__ == "__main__":
    paths = [p for p in sorted(glob.glob(os.path.join(ROOT, "data/LibriSpeech/train-clean-5/*/*/*.flac"))) if os.path.getsize(p) > SECS * 22000]
    with Pool(16) as p: res = [e for o in p.map(job, list(enumerate(paths)), chunksize=4) for e in o]
    np.savez("results/ml_train.npz", S=np.stack([e[0] for e in res]), B=np.stack([e[1] for e in res]), T=np.stack([e[2] for e in res]))
    print(len(paths), "utterances ->", len(res), "examples;", "input", res[0][0].shape, "votes", res[0][2].shape)
