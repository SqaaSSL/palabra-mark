"""Palabra mark: a keyed, zero-bit audio mark for phone speech.

The mark nudges the loudness of time/frequency tiles of the voice by a fraction of a dB to a few dB,
in a pattern derived from a per-call secret code. The detector knows which code to expect and asks
only whether the audio leans that way; the answer is a z-score that grows as the caller keeps talking.
"""
from dataclasses import dataclass, field
import hashlib, hmac, subprocess
import numpy as np
from scipy.ndimage import uniform_filter, correlate

FS, NFFT, HOP = 16000, 512, 128                      # 8 ms hop
WIN = np.hanning(NFFT + 1)[:-1]

@dataclass(frozen=True)
class Config:
    mode: str = "quad"        # "pair": neighbour bands; "tpair": neighbour frames; "quad": 2x2 checkerboard
    tt: int = 4               # tile length in hops (8 ms each)
    bw: int = 6               # tile width in FFT bins (31.25 Hz each)
    bin0: int = 13            # first bin (406 Hz)
    nbands: int = 16          # tiles across frequency
    gain: float = 2.0         # dB each tile is pushed up or down
    margin: float = 10.0      # informed embedding: push each vote only until it wins by this many dB (0 = fixed gain)
    gmax: float = 5.0         # informed embedding: largest change allowed per tile, dB
    clip: float = 2.5         # detector limits each vote to +/- clip standard deviations
    floor: float = 50.0       # tiles this many dB below the loudest are ignored
    kernel: tuple = ()        # optional trained detector filter over neighbouring tiles (time x frequency)
    version: bytes = b"palabra-mark-v1"

    @property
    def tsec(self): return self.tt * HOP / FS
    @property
    def ncols(self): return self.nbands // 2 if self.mode in ("pair", "quad") else self.nbands
    @property
    def tstep(self): return 1 if self.mode == "pair" else 2          # tiles consumed per pattern row

# ---------- audio io ----------
def load(path, fs=FS):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(fs), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)

def save(path, x, fs=FS):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(fs), "-ac", "1", "-i", "-", str(path)],
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

# ---------- code and pattern ----------
def call_code(secret: bytes, caller: str, callee: str, slot: str) -> bytes:
    """One-time code for a call: keyed hash of both numbers and the time slot."""
    return hmac.new(secret, f"{caller}|{callee}|{slot}".encode(), hashlib.sha256).digest()

def pattern(code: bytes, rows: int, cfg: Config):
    """+1/-1 per (pattern row, feature column), from a keyed stream. Row r never depends on rows > r."""
    out = np.empty((rows, cfg.ncols)); need = rows * cfg.ncols; bits = []; ctr = 0
    while len(bits) * 8 < need:
        bits.append(hashlib.sha256(cfg.version + code + ctr.to_bytes(4, "big")).digest()); ctr += 1
    b = np.unpackbits(np.frombuffer(b"".join(bits), dtype=np.uint8))[:need]
    return (b.astype(float) * 2 - 1).reshape(rows, cfg.ncols)

def tile_gains(s, cfg: Config, g=None):
    """Per-tile gain in dB (rows*tstep x nbands) that writes pattern s. g may be an array, one strength per vote."""
    g = cfg.gain if g is None else g
    if cfg.mode == "pair":
        C = np.zeros((s.shape[0], cfg.nbands)); C[:, 0::2] = g * s; C[:, 1::2] = -g * s
    elif cfg.mode == "tpair":
        C = np.zeros((s.shape[0] * 2, cfg.nbands)); C[0::2] = g * s; C[1::2] = -g * s
    else:
        C = np.zeros((s.shape[0] * 2, cfg.nbands))
        C[0::2, 0::2] = g * s; C[0::2, 1::2] = -g * s; C[1::2, 0::2] = -g * s; C[1::2, 1::2] = g * s
    return C

# ---------- features ----------
def tile_db(P, f0, ntiles, cfg: Config):
    """Log energy (dB) of ntiles x nbands tiles starting at STFT frame f0. P = |X|^2."""
    seg = P[f0:f0 + ntiles * cfg.tt, cfg.bin0:cfg.bin0 + cfg.nbands * cfg.bw]
    if seg.shape[0] < ntiles * cfg.tt:
        seg = np.vstack([seg, np.zeros((ntiles * cfg.tt - seg.shape[0], seg.shape[1]))])
    return 10 * np.log10(seg.reshape(ntiles, cfg.tt, cfg.nbands, cfg.bw).sum(axis=(1, 3)) + 1e-12)

def features(L, cfg: Config, ref=None):
    """Votes f (rows x ncols) and 0/1 activity mask. A vote is positive when the tiles lean the '+1' way."""
    floor = (L.max() if ref is None else ref) - cfg.floor
    A = L > floor
    if cfg.mode == "pair":
        f = L[:, 0::2] - L[:, 1::2]; a = A[:, 0::2] & A[:, 1::2]
    elif cfg.mode == "tpair":
        f = L[0::2] - L[1::2]; a = A[0::2] & A[1::2]
    else:
        f = L[0::2, 0::2] - L[0::2, 1::2] - L[1::2, 0::2] + L[1::2, 1::2]
        a = A[0::2, 0::2] & A[0::2, 1::2] & A[1::2, 0::2] & A[1::2, 1::2]
    return f, a.astype(float)

def onset(x):
    e = np.sqrt(np.convolve(x ** 2, np.ones(320) / 320, "same"))
    return int(np.argmax(e > 0.08 * e.max()))

# ---------- embed ----------
def embed(x, code: bytes, cfg: Config = Config(), start=None, dur=None):
    """Mark x from `start` (samples; default: first speech) for `dur` seconds (default: to the end)."""
    start = onset(x) if start is None else start
    f0 = (start + NFFT) // HOP
    X = stft(x)
    ntiles = (X.shape[0] - f0) // cfg.tt if dur is None else int(round(dur / cfg.tsec))
    ntiles -= ntiles % cfg.tstep
    s = pattern(code, ntiles // cfg.tstep, cfg)
    def apply(g):
        K = np.kron(tile_gains(s, cfg, g), np.ones((cfg.tt, cfg.bw)))[:max(0, X.shape[0] - f0)]
        G = np.zeros(X.shape); G[f0:f0 + len(K), cfg.bin0:cfg.bin0 + cfg.nbands * cfg.bw] = K
        return X * 10 ** (uniform_filter(G, size=3, mode="nearest") / 20)   # soften tile edges
    if cfg.margin <= 0: return istft(apply(None), len(x)), start
    # Informed embedding: the embedder can see how the voice already leans, so it spends change only where needed.
    nvote = {"pair": 2, "tpair": 2, "quad": 4}[cfg.mode]
    g = np.zeros_like(s); Y = X
    for _ in range(4):
        f, a = features(tile_db(np.abs(stft(istft(Y, len(x)))) ** 2, f0, ntiles, cfg), cfg)
        g = np.clip(g + a * (cfg.margin - s * f) / nvote, 0, cfg.gmax)
        Y = apply(g)
    return istft(Y, len(x)), start

# ---------- detect ----------
class Detector:
    """Precomputes the votes of a recording for every candidate start, then scores any code cheaply.

    z(code) is returned for every candidate start and every listening time, so the same object answers
    both "is this the call?" and "how long did it take to be sure?"."""
    def __init__(self, y, cfg: Config = Config(), max_dur=8.0, search=(0.0, 1.2)):
        self.cfg = cfg
        P = np.abs(stft(y)) ** 2
        self.rows = int(max_dur / cfg.tsec) // cfg.tstep
        ntiles = self.rows * cfg.tstep
        self.starts = np.arange(int(search[0] * FS / HOP), int(search[1] * FS / HOP)) + NFFT // HOP
        ref = 10 * np.log10(P[:, cfg.bin0:cfg.bin0 + cfg.nbands * cfg.bw].reshape(P.shape[0], cfg.nbands, cfg.bw).sum(2).max() * cfg.tt + 1e-12)
        V = np.empty((len(self.starts), self.rows, cfg.ncols)); W = np.empty_like(V)
        bw = np.ones(cfg.ncols); K = np.asarray(cfg.kernel) if len(cfg.kernel) else None
        for i, f0 in enumerate(self.starts):
            L = tile_db(P, f0, ntiles, cfg)
            f, a = features(L, cfg, ref)
            if K is not None:                                          # trained filter: sharpen the pattern, cancel the voice
                Lc = np.maximum(L, ref - cfg.floor)
                f, _ = features(correlate(Lc - Lc.mean(), K, mode="nearest"), cfg, ref=np.inf)
            n = a.sum()
            mu = (a * f).sum() / max(n, 1); sd = np.sqrt((a * (f - mu) ** 2).sum() / max(n, 1)) + 1e-9
            V[i] = np.clip((f - mu) / sd, -cfg.clip, cfg.clip) * a * bw; W[i] = a * bw
        self.V, self.W = V, W
        # variance of the sum of votes, cumulated over rows (clipping shrinks it below 1 per vote)
        self.cumvar = np.cumsum((V ** 2).sum(2), axis=1)

    def z(self, code: bytes):
        """z[start, row]: score after listening to rows+1 pattern rows, for each candidate start."""
        s = pattern(code, self.rows, self.cfg)
        return np.cumsum((self.V * s).sum(2), axis=1) / np.sqrt(self.cumvar + 1e-9)

    def best(self, code: bytes, dur=None):
        """Highest z over candidate starts after `dur` seconds of the mark (default: everything)."""
        r = self.rows - 1 if dur is None else min(self.rows, max(1, int(dur / (self.cfg.tsec * self.cfg.tstep)))) - 1
        return float(self.z(code)[:, r].max())

    def curve(self, code: bytes):
        """Best z over starts as a function of listening time (seconds, z)."""
        zz = self.z(code).max(0)
        return (np.arange(self.rows) + 1) * self.cfg.tsec * self.cfg.tstep, zz
