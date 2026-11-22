"""Figure 1 of the paper: what the mark does to one second and a half of speech."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import *
from eval_final import items, FINAL
from scipy.ndimage import uniform_filter
from palabra_mark.core import stft, NFFT, HOP

kind, spk, path = items()[0]; x = clip8(path); code = call_code(b"final", "+999555000427", "+999555000010", "0")
y, start = embed(x, code, FINAL)
X, Y = np.abs(stft(x)), np.abs(stft(y)); f0 = (start + NFFT) // HOP
T0, T1 = 0.0, 1.6; a, b = f0 + int(T0 * FS / HOP), f0 + int(T1 * FS / HOP); kmax = int(4000 / (FS / NFFT))
S = 20 * np.log10(X[a:b, :kmax].T + 1e-6); S -= S.max()
D = 20 * np.log10((Y[a:b, :kmax].T + 1e-6) / (X[a:b, :kmax].T + 1e-6)); D[uniform_filter(S, size=(6, 4)) < -50] = 0   # no change shown where there is no voice
ext = [T0, T1, 0, 4.0]; lo, hi = FINAL.bin0 * FS / NFFT / 1000, (FINAL.bin0 + FINAL.nbands * FINAL.bw) * FS / NFFT / 1000
plt.rcParams.update({"font.size": 9, "figure.dpi": 200, "font.family": "Helvetica"})
fig, ax = plt.subplots(2, 1, figsize=(6.6, 4.6), sharex=True)
im0 = ax[0].imshow(S, origin="lower", aspect="auto", extent=ext, cmap="Greys", vmin=-60, vmax=0)
ax[0].set_title("Speech before marking", loc="left", fontsize=9); fig.colorbar(im0, ax=ax[0], pad=0.015).set_label("level, dB")
im1 = ax[1].imshow(D, origin="lower", aspect="auto", extent=ext, cmap="RdBu_r", vmin=-5, vmax=5)
ax[1].set_title("Change made by the mark", loc="left", fontsize=9); fig.colorbar(im1, ax=ax[1], pad=0.015).set_label("change, dB")
for A in ax:
    A.set_ylabel("frequency, kHz")
    for v in (lo, hi): A.axhline(v, color="#12143A", lw=0.6, ls="--")
ax[1].set_xlabel("seconds from the start of speech")
fig.tight_layout(); fig.savefig("../paper/figures/fig0_the_mark.png"); plt.close(fig)
print("written; marked band %.0f to %.0f Hz" % (lo * 1000, hi * 1000))
