"""Streaming marker: writes the mark into speech as it is produced.

Put it between the voice source (a text-to-speech engine, a realtime speech-to-speech model, a microphone) and
the phone line. push() takes audio frames of any size and returns marked audio, the same samples a little later:

    m = StreamMarker(code, fs=24000)
    for frame in voice:                 # float samples in [-1, 1]
        line.send(m.push(frame))
    line.send(m.flush())

The pattern starts at the first speech and then follows the clock of the audio pushed, so the whole call is
marked. Push silence, not nothing, while the voice pauses, or the receiver loses step.

Two modes:
    lookahead=True    informed embedding, as in embed(): the change is spent only where the voice does not already
                      lean the right way. Each vote spans 64 ms and must be heard before it is changed: delay 80 ms.
    lookahead=False   fixed strength, decided without looking at the voice: delay 24 ms.
Works at 8, 16, 24, 32 or 48 kHz; the tiles are the same 32 ms by 187.5 Hz at every rate.
"""
import numpy as np
from .core import Config, pattern, FS, NFFT, HOP

class StreamMarker:
    def __init__(self, code: bytes, cfg: Config = Config(), fs=FS, lookahead=True, gain=4.0, onset_db=-35.0, boost=1.0):
        """gain: dB per tile in fixed mode. onset_db: level (dBFS) of the first frame that counts as speech.
        boost: scales the informed change, to trade audibility against speed."""
        assert cfg.mode == "quad" and fs in (8000, 16000, 24000, 32000, 48000)
        self.code, self.cfg, self.fs, self.lookahead, self.gain, self.boost = code, cfg, fs, lookahead, gain, boost
        self.nfft, self.hop = NFFT * fs // FS, HOP * fs // FS         # always a 32 ms window, 8 ms hop, 31.25 Hz bins
        self.win = np.hanning(self.nfft + 1)[:-1]
        self.pad = self.nfft - self.hop                               # zeros in front, so every sample sits under four windows
        self.inb = np.zeros(self.pad); self.ola = np.zeros(self.nfft); self.nrm = np.zeros(self.nfft)
        self.n_in = self.n_out = 0; self.skip = self.pad
        self.thr = 10 ** (onset_db / 20); self.started = False; self.start_sample = None
        self.frames = 0                                               # frames analysed so far
        self.rowlen = cfg.tt * 2                                      # frames per pattern row (8 = 64 ms)
        self.row, self.r, self.j = [], 0, 0                           # spectra waiting for their row; row number; frame within row
        self.band = slice(cfg.bin0 - 1, cfg.bin0 + cfg.nbands * cfg.bw + 1)   # one bin either side takes the softened edge
        self.prev = np.zeros(cfg.nbands * cfg.bw + 2)                 # gain (dB) of the previous frame, before softening
        self.ref = -np.inf
        self.s = pattern(code, 256, cfg)

    @property
    def delay(self):
        """Seconds between a sample going in and coming out (not counting how the caller chunks the audio)."""
        return (self.pad + (self.rowlen - 1) * self.hop * (self.lookahead and self.started)) / self.fs

    # ---- gains
    def _signs(self, r):
        if r >= len(self.s): self.s = pattern(self.code, len(self.s) * 2, self.cfg)      # row r never depends on later rows
        return self.s[r]
    def _tiles(self, g, s):
        """Gain in dB for one row: rowlen frames x (band + 2 edge bins), before softening."""
        c = self.cfg; C = np.zeros((2, c.nbands))
        C[0, 0::2] = g * s; C[0, 1::2] = -g * s; C[1, 0::2] = -g * s; C[1, 1::2] = g * s
        return np.pad(np.kron(C, np.ones((c.tt, c.bw))), ((0, 0), (1, 1)))
    @staticmethod
    def _soften(K, before, after):
        """3 x 3 mean over frames and bins, as embed() does. before/after: the frames either side of K."""
        T = np.vstack([before, K, after]); T = (T[:-2] + T[1:-1] + T[2:]) / 3
        B = np.pad(T, ((0, 0), (1, 1))); return (B[:, :-2] + B[:, 1:-1] + B[:, 2:]) / 3

    def _informed(self, P, s):
        """Strength per vote for one row, from the power spectra of its frames (rowlen x band)."""
        c = self.cfg; g = np.zeros(c.ncols)
        def tiles_db(Q): return 10 * np.log10(Q[:, 1:-1].reshape(2, c.tt, c.nbands, c.bw).sum(axis=(1, 3)) + 1e-12)
        self.ref = max(self.ref, float(tiles_db(P).max()))
        for _ in range(4):
            G = self._soften(self._tiles(g, s), self.prev, self._tiles(g, s)[-1])
            L = tiles_db(P * 10 ** (G / 10)); A = L > self.ref - c.floor
            f = L[0, 0::2] - L[0, 1::2] - L[1, 0::2] + L[1, 1::2]
            a = A[0, 0::2] & A[0, 1::2] & A[1, 0::2] & A[1, 1::2]
            g = np.clip(g + a * (c.margin - s * f) / 4, 0, c.gmax)
        return np.clip(g * self.boost, 0, c.gmax)

    # ---- audio
    def _synth(self, X):
        self.ola += np.fft.irfft(X, self.nfft) * self.win; self.nrm += self.win ** 2
        out = self.ola[: self.hop] / np.maximum(self.nrm[: self.hop], 1e-9)
        self.ola = np.concatenate([self.ola[self.hop:], np.zeros(self.hop)]); self.nrm = np.concatenate([self.nrm[self.hop:], np.zeros(self.hop)])
        return out
    def _apply(self, X, G):
        X = X.copy(); X[self.band] *= 10 ** (G / 20); return X

    def push(self, x):
        """x: float samples in [-1, 1], any length. Returns the marked samples that are ready."""
        x = np.asarray(x, dtype=np.float64); self.n_in += len(x)
        self.inb = np.concatenate([self.inb, x]); out = []
        while len(self.inb) >= self.nfft:
            seg = self.inb[: self.nfft]; self.inb = self.inb[self.hop:]
            X = np.fft.rfft(self.win * seg); self.frames += 1
            if not self.started:
                if np.sqrt(np.mean(seg ** 2)) < self.thr: out.append(self._synth(X)); continue
                self.started = True; self.start_sample = max(0, (self.frames - 1) * self.hop - self.pad)
            if self.lookahead:
                self.row.append(X)
                if len(self.row) < self.rowlen: continue
                s = self._signs(self.r); P = np.abs(np.array(self.row)[:, self.band]) ** 2
                K = self._tiles(self._informed(P, s), s); G = self._soften(K, self.prev, K[-1])
                out += [self._synth(self._apply(Xi, Gi)) for Xi, Gi in zip(self.row, G)]
                self.prev = K[-1]; self.row = []; self.r += 1
            else:
                Kr = self._tiles(self.gain, self._signs(self.r)); K = Kr[self.j]
                nxt = Kr[self.j + 1] if self.j + 1 < self.rowlen else self._tiles(self.gain, self._signs(self.r + 1))[0]
                out.append(self._synth(self._apply(X, self._soften(K[None], self.prev, nxt)[0])))
                self.prev = K; self.j += 1
                if self.j == self.rowlen: self.j = 0; self.r += 1
        y = np.concatenate(out) if out else np.zeros(0)
        if self.skip: k = min(self.skip, len(y)); y = y[k:]; self.skip -= k
        self.n_out += len(y); return y

    def flush(self):
        """The samples still inside the marker. Call once, when the voice ends."""
        need = self.n_in - self.n_out
        y = self.push(np.zeros(self.nfft + self.rowlen * self.hop))[:need]
        self.n_out = self.n_in; return y
