"""Baseline: AudioSeal (Meta, ICML 2024) through the same phone lines. Writes results/audioseal.json."""
import json, torch
from common import *
from eval_final import items, LINES
from pesq import pesq
from audioseal import AudioSeal

KEY = ["clean", "G.711", "AMR-12.2", "AMR-7.95", "AMR-4.75", "Opus-16", "Opus-12", "Opus-8", "G.723.1-6.3", "AMR-12.2 > G.711 > Opus-16"]
gen = AudioSeal.load_generator("audioseal_wm_16bits"); det = AudioSeal.load_detector("audioseal_detector_16bits")
def score(r, secs):
    w = torch.from_numpy(r[: int(secs * FS)].astype(np.float32))[None, None]
    with torch.no_grad(): p, _ = det.detect_watermark(w, FS)
    return float(p)
if __name__ == "__main__":
    out = []
    for i, (kind, spk, path) in enumerate(items()):
        x = clip8(path) if kind == "human" else (lambda v: v / (np.abs(v).max() + 1e-9) * 0.7)(load(path))
        w = torch.from_numpy(x.astype(np.float32))[None, None]
        with torch.no_grad(): y = (w + gen.get_watermark(w, FS))[0, 0].numpy().astype(np.float64)
        rec = dict(kind=kind, pesq=float(pesq(FS, x, y, "wb")), snr=float(10 * np.log10(np.sum(x ** 2) / np.sum((y - x) ** 2))), lines={})
        for name in KEY:
            chain, noise = LINES[name]; rm = bridge(y, chain, noise); ru = bridge(x, chain, noise)
            rec["lines"][name] = dict(marked={T: score(rm, T) for T in (3, 8)}, unmarked={T: score(ru, T) for T in (3, 8)})
        out.append(rec)
    json.dump(dict(lines=KEY, records=out), open("results/audioseal.json", "w"))
    print(f"AudioSeal mark: PESQ-WB {np.mean([r['pesq'] for r in out]):.2f}, SNR {np.mean([r['snr'] for r in out]):.1f} dB, n={len(out)}")
    print(f"{'line':28} {'marked score (3 s)':>20} {'unmarked score (3 s)':>22} {'detected at 0 false alarms: 3 s / 8 s':>40} {'EER 3 s':>8}")
    for name in KEY:
        res = []
        for T in ("3", "8") if False else (3, 8):
            m = np.array([r["lines"][name]["marked"][T] for r in out]); u = np.array([r["lines"][name]["unmarked"][T] for r in out])
            thr = np.sort(np.concatenate([m, u])); eer = min(max(np.mean(u >= t), np.mean(m < t)) for t in thr)
            res.append((m, u, np.mean(m > u.max()), eer))
        print(f"{name:28} {np.median(res[0][0]):>20.3f} {np.median(res[0][1]):>22.3f} {f'{100*res[0][2]:.0f}% / {100*res[1][2]:.0f}%':>40} {100*res[0][3]:>7.1f}%")
