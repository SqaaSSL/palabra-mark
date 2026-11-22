"""Palabra audio-mark proof of concept.

Hides a per-call pattern in the first seconds of a caller's speech by nudging the loudness of small
time/frequency patches up or down by a dB or two. Nothing is added: no tone, no noise. Phone codecs
are built to preserve that coarse spectral shape, which is why this has a chance of surviving a call.

The band a phone line carries (400-3400 Hz) is cut into tiles (32 ms x 190 Hz). Each tile is paired
with its neighbour in frequency. A secret per-call code decides, for every pair, which of the two
should be the louder one. The receiver already knows which code to expect (it looked the call up by
both phone numbers and the time), so it does not read data out of the audio. It only asks: do the
pairs lean the way this code says, far more often than chance? The answer is a z-score.
"""
import hashlib, hmac, subprocess, numpy as np

FS, NFFT, HOP = 16000, 512, 128          # 8 ms hop
TT, BW, BIN0, NBANDS = 4, 6, 13, 16      # tile = 32 ms x 187.5 Hz, band = 406..3400 Hz
WIN = np.hanning(NFFT + 1)[:-1]

def load(path, fs=FS):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(fs), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)

def save(path, x, fs=FS):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(fs), "-ac", "1", "-i", "-", path],
                   input=pcm, check=True)

def stft(x):
    x = np.concatenate([np.zeros(NFFT), x, np.zeros(NFFT)])
    idx = np.arange(0, len(x) - NFFT + 1, HOP)
    return np.fft.rfft(WIN * x[idx[:, None] + np.arange(NFFT)], axis=1)

def istft(X, n):
    out = np.zeros(NFFT * 2 + n + NFFT); norm = np.zeros_like(out)
    frames = np.fft.irfft(X, NFFT, axis=1) * WIN
    for i, f in enumerate(frames):
        out[i * HOP:i * HOP + NFFT] += f; norm[i * HOP:i * HOP + NFFT] += WIN ** 2
    return (out / np.maximum(norm, 1e-9))[NFFT:NFFT + n]

def ntiles(dur): return int(dur / (TT * HOP / FS))

def tiles(P, f0, nt):
    """Log energy (dB) of nt x NBANDS tiles starting at STFT frame f0. P = |X|^2."""
    seg = P[f0:f0 + nt * TT, BIN0:BIN0 + NBANDS * BW]
    if seg.shape[0] < nt * TT: seg = np.vstack([seg, np.zeros((nt * TT - seg.shape[0], seg.shape[1]))])
    return 10 * np.log10(seg.reshape(nt, TT, NBANDS, BW).sum(axis=(1, 3)) + 1e-12)

def call_code(secret, caller, callee, slot):
    """The one-time code for a call: a keyed hash of both numbers and the time slot."""
    return hmac.new(secret, f"{caller}|{callee}|{slot}".encode(), hashlib.sha256).digest()

def pattern(code, nt):
    """+1 / -1 for every tile pair: which of the two tiles this call's code wants louder."""
    rng = np.random.default_rng(int.from_bytes(hashlib.sha256(b"palabra-poc-v1" + code).digest()[:8], "big"))
    return rng.choice([-1.0, 1.0], nt * (NBANDS // 2))

def score(L, s):
    """z-score: how far the pairs lean the way pattern s says, in standard deviations above chance."""
    a, b = L[:, 0::2].ravel(), L[:, 1::2].ravel()
    floor = L.max() - 50
    w = ((a > floor) & (b > floor)).astype(float)                      # ignore silent tiles
    if w.sum() < 30: return -9.0, 0
    d = a - b; mu = np.average(d, weights=w)
    sd = np.sqrt(np.average((d - mu) ** 2, weights=w)) + 1e-9
    return float((w * s * (d - mu)).sum() / (sd * np.sqrt(w.sum()))), int(w.sum())

def onset(x):
    e = np.sqrt(np.convolve(x ** 2, np.ones(320) / 320, "same"))
    return int(np.argmax(e > 0.08 * e.max()))

def embed(x, code, dur=1.5, gain=1.5):
    """Returns marked audio. gain = dB each tile is pushed up or down."""
    nt = ntiles(dur); s = pattern(code, nt).reshape(nt, NBANDS // 2)
    f0 = (onset(x) + NFFT) // HOP
    C = np.zeros((nt, NBANDS)); C[:, 0::2] = s * gain; C[:, 1::2] = -s * gain
    X = stft(x); G = np.zeros(X.shape)
    K = np.kron(C, np.ones((TT, BW)))[:max(0, G.shape[0] - f0)]            # a short clip ends before the mark does
    G[f0:f0 + len(K), BIN0:BIN0 + NBANDS * BW] = K
    k = np.ones(3) / 3                                                 # soften tile edges
    G = np.apply_along_axis(np.convolve, 0, G, k, "same"); G = np.apply_along_axis(np.convolve, 1, G, k, "same")
    return istft(X * 10 ** (G / 20), len(x)), f0 * HOP - NFFT

def detect(y, code, dur=1.5, search=(0.0, 1.2)):
    """Slide over possible start times and return the best z-score for this code."""
    nt = ntiles(dur); s = pattern(code, nt); P = np.abs(stft(y)) ** 2
    best = (-9.0, 0, 0)
    for f0 in range(int(search[0] * FS / HOP) + NFFT // HOP, int(search[1] * FS / HOP) + NFFT // HOP):
        z, n = score(tiles(P, f0, nt), s)
        if z > best[0]: best = (z, f0, n)
    return {"z": best[0], "start_s": (best[1] * HOP - NFFT) / FS, "pairs": best[2]}
