"""Causal inputs for the streaming learned detector (VoteNet3): everything at frame t depends only on audio up to t.

feats(r) returns, for every 8 ms frame of a recording:
    S   the phone band's log spectrum (96 bins) relative to the loudest frame heard so far, scaled to [-3.5, 0.25]
    B   the analytic votes (8) of the 64 ms row that ends at this frame, as VoteStream computes them
"""
import numpy as np
from palabra_mark.core import Config, stft

CFG = Config(); NBIN = CFG.nbands * CFG.bw; TT = CFG.tt; ROWF = 2 * TT           # 8 frames per pattern row
LO, QSTEP = -3.5, 3.75 / 255                                                     # 8-bit scale used to store S

def feats(r):
    P = np.abs(stft(r)) ** 2; band = P[:, CFG.bin0:CFG.bin0 + NBIN]; T = len(band)
    E = band.reshape(T, CFG.nbands, CFG.bw).sum(2)
    ref = np.maximum.accumulate(10 * np.log10(E.max(1) * TT + 1e-12))
    S = np.clip(10 * np.log10(band + 1e-12) - ref[:, None], -70, 5) / 20
    c = np.vstack([np.zeros((1, CFG.nbands)), np.cumsum(E, 0)]); B = np.zeros((T, CFG.ncols))
    t = np.arange(ROWF - 1, T)                                                   # rows that end at frame t
    L0 = 10 * np.log10(c[t - TT + 1] - c[t - ROWF + 1] + 1e-12); L1 = 10 * np.log10(c[t + 1] - c[t - TT + 1] + 1e-12)
    fl = (ref[t] - CFG.floor)[:, None]; A0, A1 = L0 > fl, L1 > fl
    f = L0[:, 0::2] - L0[:, 1::2] - L1[:, 0::2] + L1[:, 1::2]
    a = (A0[:, 0::2] & A0[:, 1::2] & A1[:, 0::2] & A1[:, 1::2]).astype(float)
    n = np.maximum(np.cumsum(a.sum(1)), 1); mu = np.cumsum((a * f).sum(1)) / n
    sd = np.sqrt(np.maximum(np.cumsum((a * f * f).sum(1)) / n - mu ** 2, 0)) + 1e-9
    B[t] = np.clip((f - mu[:, None]) / sd[:, None], -CFG.clip, CFG.clip) * a
    return S, B
def quant(S): return np.round((S - LO) / QSTEP).astype(np.uint8)
