"""Marks a recording, sends it through simulated phone lines, and reports whether the mark is still found.
Usage: python3 run.py [audio files...]"""
import os, sys, numpy as np
from wm import *
from channels import CODECS, through, tandem

LINES = [(n, lambda s, n=n: through(s, n)) for n in CODECS] + [
    ("Opus 12k -> G.711 -> G.726 32k", lambda s: tandem(s, ["Opus 12k (VoIP)", "G.711 mu-law (landline)", "G.726 32k"])),
    ("G.711 + noise (20 dB SNR)", lambda s: tandem(s, ["G.711 mu-law (landline)"], 20)),
    ("G.723.1 -> G.711 + noise 25 dB", lambda s: tandem(s, ["G.723.1 6.3k (CELP, harsh)", "G.711 mu-law (landline)"], 25))]
GAIN, NCODES, NWRONG, PASS = 2.0, 5, 400, 6.0

srcs = sys.argv[1:] or ["../../site/greet.mp3", "out/second_voice.wav"]
os.makedirs("out", exist_ok=True)
rng = np.random.default_rng(7)
codes = [call_code(b"demo-secret", "+999555000427", "+999555000010", f"2026-11-21T09:{14+i}") for i in range(NCODES)]
for src in srcs:
    x = load(src); tag = os.path.splitext(os.path.basename(src))[0]
    save(f"out/{tag}_original.wav", x)
    print(f"\n##### {tag} ({len(x)/FS:.1f} s), tiles nudged +/-{GAIN} dB, {NCODES} different call codes; pass = z >= {PASS}")
    print(f"{'line':32}" + "".join(f"{f'mark over {d} s':>26}" for d in (1.5, 3.0, 5.0)))
    print(f"{'':32}" + "".join(f"{'lowest z / passes':>26}" for _ in range(3)))
    rows = {n: [] for n, _ in LINES}; ctrl = []
    for dur in (1.5, 3.0, 5.0):
        marked = [embed(x, c, dur, GAIN)[0] for c in codes]
        if dur == 3.0:
            save(f"out/{tag}_marked.wav", marked[0]); save(f"out/{tag}_marked_after_phone.wav", through(marked[0], "G.711 mu-law (landline)"))
            save(f"out/{tag}_original_after_phone.wav", through(x, "G.711 mu-law (landline)"))
        for name, ch in LINES:
            try: zs = [detect(ch(y), c, dur)["z"] for y, c in zip(marked, codes)]
            except Exception as e: rows[name].append("failed"); continue
            rows[name].append(f"{min(zs):.1f} / {sum(z >= PASS for z in zs)} of {NCODES}")
        r = through(marked[0], "G.711 mu-law (landline)")
        wrong = max(detect(r, rng.bytes(32), dur)["z"] for _ in range(NWRONG))
        plain = max(detect(through(x, "G.711 mu-law (landline)"), c, dur)["z"] for c in codes)
        ctrl.append(f"{wrong:.1f} / {plain:.1f}")
    for n, _ in LINES: print(f"{n:32}" + "".join(f"{v:>26}" for v in rows[n]))
    print(f"{'CONTROL highest z, should fail':32}" + "".join(f"{v:>26}" for v in ctrl) + f"   ({NWRONG} wrong codes / right codes on unmarked audio)")
