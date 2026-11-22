"""Continuous marking: once a call is verified, can the tap tell when the marked voice is replaced?
Held-out speakers. Honest call: all 8 s marked. Hijack: marked for 4 s, then the SAME voice unmarked
(the strongest takeover: a perfect voice clone, no click, no gap). Writes results/hijack.json."""
import json, time
from multiprocessing import Pool
from common import *

CFG, LINES, TAKEOVER = Config(), ["G.711", "AMR-12.2", "Opus-12", "AMR-4.75"], 4.0
ROW = CFG.tsec * CFG.tstep

def windows(D, code, lock_s=3.0):
    """Lock onto the alignment found in the first lock_s seconds, then score every 2 s and 3 s window on it."""
    s = pattern(code, D.rows, CFG); z = D.z(code); i = int(np.argmax(z[:, int(lock_s / ROW) - 1]))
    c = np.concatenate([[0], np.cumsum((D.V[i] * s).sum(1))]); v = np.concatenate([[0], np.cumsum((D.V[i] ** 2).sum(1))])
    out = {}
    for w in (2.0, 3.0):
        n = int(w / ROW); out[w] = ((c[n:] - c[:-n]) / np.sqrt(v[n:] - v[:-n] + 1e-9)).tolist()      # window ending at row k+n
    return float(z[i, int(lock_s / ROW) - 1]), out

def job(a):
    i, path = a; x = clip8(path); code = call_code(b"hijack", "a", "b", str(i)); rec = {}
    full, _ = embed(x, code, CFG, start=0); half, _ = embed(x, code, CFG, start=0, dur=TAKEOVER)
    for name in LINES:
        rec[name] = dict(honest=windows(Detector(bridge(full, [name]), CFG), code), hijack=windows(Detector(bridge(half, [name]), CFG), code))
    return rec

if __name__ == "__main__":
    d = librispeech(); _, test = split(); files = [p for s in test for p in d[s]]; t0 = time.time()
    with Pool(12) as p: out = p.map(job, list(enumerate(files)), chunksize=1)
    json.dump(out, open("results/hijack.json", "w"))
    for w, th in ((2.0, 3.0), (3.0, 3.0), (3.0, 3.5)):
        n = int(w / ROW); print(f"\nwindow {w:.0f} s, alarm when the window scores below {th}")
        for name in LINES:
            R = [r[name] for r in out if r[name]["honest"][0] >= 7]                      # calls that verified in the first 3 s
            fa = np.mean([min(r["honest"][1][w]) < th for r in R])                       # honest call ever raises the alarm
            fa_w = np.mean([z < th for r in R for z in r["honest"][1][w]])
            delays = []
            for r in out:
                if r[name]["hijack"][0] < 7: continue
                zz = np.array(r[name]["hijack"][1][w]); ends = (np.arange(len(zz)) + n) * ROW
                hit = np.nonzero((zz < th) & (ends > TAKEOVER))[0]; delays.append(ends[hit[0]] - TAKEOVER if len(hit) else None)
            got = [x for x in delays if x is not None]
            print(f"  {name:9s} calls {len(R):2d}  honest calls with a false alarm {fa:4.0%} (windows {fa_w:5.1%})  hijacks caught {len(got)}/{len(delays)}"
                  f"  median {np.median(got):.1f} s after takeover, worst {max(got):.1f} s" if got else f"  {name}: none")
    print(f"{time.time()-t0:.0f} s")
