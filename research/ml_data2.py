"""Training data for the second learned detector: as ml_data.py, plus the wideband mobile codecs (AMR-WB, EVS),
chains of up to three codecs, several codes per recording and more examples. Writes results/ml_train2.npz.

The spectrogram is stored in 8 bits (steps of 0.3 dB) to keep the file small enough to send to a rented GPU;
ml_train2.py undoes this and adds noise of one step. Recordings are split by speaker, so validation speakers
are never trained on. Speakers come from train-clean-5, which shares none with the tuning or held-out sets."""
import glob, sys, time
from multiprocessing import Pool
from common import *
from palabra_mark.core import stft, pattern
from palabra_mark.channels import WIDE
from ml_data import spec_in, base_votes, peak_ref, CFG, SECS, ROWS, SINGLE

NARROW = SINGLE; WB = list(WIDE)
CODES, LINES_PER_CODE = 3, 4                       # per recording: 3 codes, each sent down 4 lines
LO, STEP = -3.5, 3.75 / 255                        # 8-bit scale of the network input (which lies in [-3.5, 0.25])

def line(rng):
    """A random line: one codec, or a chain of two or three. Wideband codecs are the first or last hop, as on real calls."""
    pick = lambda: NARROW[rng.integers(len(NARROW))] if rng.random() < 0.6 else WB[rng.integers(len(WB))]
    u = rng.random(); chain = [pick()]
    if u < 0.35: chain.append("G.711" if rng.random() < 0.4 else NARROW[rng.integers(len(NARROW))])
    if u < 0.12: chain.append(pick())
    return chain, (rng.uniform(15, 35) if rng.random() < 0.3 else None)

def job(a):
    i, path = a; rng = np.random.default_rng(7000 + i); out = []; n = int(SECS * FS) + FS // 2
    full = load(path)
    for _ in range(CODES):
        o = int(rng.integers(0, max(1, len(full) - n))); x = full[o:o + n]
        x = x / (np.abs(x).max() + 1e-9) * rng.uniform(0.2, 0.9)
        code = rng.bytes(32); y, _ = embed(x, code, CFG); s = pattern(code, ROWS, CFG)
        for _ in range(LINES_PER_CODE):
            chain, noise = line(rng)
            try: r = bridge(y, chain, noise, seed=int(rng.integers(1 << 30)))
            except Exception: continue
            D = Detector(r, CFG, max_dur=SECS); f0 = int(D.starts[int(np.argmax(D.z(code)[:, -1]))]) + int(rng.integers(-1, 2))
            P = np.abs(stft(r)) ** 2; ref = peak_ref(P)
            S = np.clip(spec_in(P, f0) - ref, -70, 5) / 20
            out.append((np.round((S - LO) / STEP).astype(np.uint8), base_votes(P, f0, ref).astype(np.float16), s.astype(np.int8),
                        int(path.split(os.sep)[-3]), any(c in WIDE for c in chain)))
    return out

if __name__ == "__main__":
    paths = [p for p in sorted(glob.glob(os.path.join(ROOT, "data/LibriSpeech/train-clean-5/*/*/*.flac"))) if os.path.getsize(p) > SECS * 22000]
    if len(sys.argv) > 1: paths = paths[: int(sys.argv[1])]
    res = []; t0 = time.time()
    with Pool(16) as p:
        for k, o in enumerate(p.imap(job, list(enumerate(paths)), chunksize=2)):
            res += o
            if k % 100 == 0: print(k, len(res), f"{time.time() - t0:.0f}s", flush=True)
    if len(sys.argv) > 1: print(len(res), "examples from", len(paths), f"recordings in {time.time() - t0:.0f}s"); sys.exit()
    np.savez_compressed("results/ml_train2.npz", S=np.stack([e[0] for e in res]), B=np.stack([e[1] for e in res]), T=np.stack([e[2] for e in res]),
                        spk=np.array([e[3] for e in res]), wide=np.array([e[4] for e in res]), lo=LO, step=STEP)
    print(len(paths), "recordings ->", len(res), "examples;", f"{np.mean([e[4] for e in res]):.0%} through a wideband codec; {time.time() - t0:.0f}s")
