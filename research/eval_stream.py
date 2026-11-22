"""The streaming tap on real call recordings: marked greeting after a random wait, fed in 20 ms frames at 8 kHz.
Compares with the offline detector, counts wrong-code passes, and times the tap. Writes results/stream.json."""
import glob, json, time
from multiprocessing import Pool
from scipy.signal import resample_poly
from common import *
from eval_calls import busiest, LINES, first_pass
from palabra_mark.stream import StreamDetector, VoteStream, Scorer

CFG, NWRONG = Config(), 100

def job(a):
    i, path = a
    x, _ = busiest(load(path)); x = x / (np.abs(x).max() + 1e-9) * 0.7
    code = call_code(b"stream", "+999555000427", "+999555000010", f"{i}"); rng = np.random.default_rng(9000 + i)
    y, _ = embed(x, code, CFG, start=0)
    wait = float(rng.uniform(0.3, 6.0))                                   # ringing / silence before the greeting
    pre = rng.standard_normal(int(wait * FS)) * 10 ** (-60 / 20)          # faint line noise, not digital silence
    rec = dict(src=path.split(os.sep)[-2], wait=wait, lines={})
    for name, chain in LINES.items():
        r = bridge(np.concatenate([pre, y]), chain, None)
        t_off, _ = first_pass(Detector(r[int(wait * FS) - 4800:], CFG, max_dur=8.0), code)   # offline, told roughly where to look
        r8 = resample_poly(r, 1, 2)                                       # what an 8 kHz trunk hands over
        D = StreamDetector(code, CFG, fs=8000); cpu = time.perf_counter(); log = []
        vs = VoteStream(CFG, 8000)
        for k in range(0, len(r8), 160):
            D.push(r8[k:k + 160])
        cpu = time.perf_counter() - cpu
        for k in range(0, len(r8), 160): log += list(vs.push(r8[k:k + 160]))
        wrong = []
        for _ in range(NWRONG):
            S = Scorer(rng.bytes(32), CFG)
            for hop, v in log: S.feed(hop, v)
            wrong.append(S.best)
        rec["lines"][name] = dict(t_off=t_off, t=None if D.verified_at is None else D.verified_at - wait, heard=D.scorer.heard,
                                  z=D.score, null=max(wrong), cpu_per_s=cpu / (len(r8) / 8000))
    return rec

if __name__ == "__main__":
    files = sorted(glob.glob(os.path.join(ROOT, "data/calls/*/*.wav"))); t0 = time.time()
    with Pool(12) as p: out = p.map(job, list(enumerate(files)), chunksize=1)
    json.dump(out, open(os.path.join(ROOT, "results/stream.json"), "w"))
    S = Scorer(b"x" * 32, CFG)
    print(f"{len(out)} calls; looks per call {S.looks}, false-alarm bound {S.false_alarm_bound:.1e}")
    for name in LINES:
        L = [r["lines"][name] for r in out]
        f = lambda key, s: np.mean([l[key] is not None and l[key] <= s for l in L])
        med = lambda key: np.median([l[key] if l[key] is not None else 99 for l in L])
        print(f"  {name:28s} tap: 3s {f('t',3):4.0%} 5s {f('t',5):4.0%} 8s {f('t',8.3):4.0%} median {med('t'):4.1f}s | offline: 3s {f('t_off',3):4.0%} 5s {f('t_off',5):4.0%} median {med('t_off'):4.1f}s | max wrong {max(l['null'] for l in L):.2f}")
    print(f"tap cost: {1000*np.mean([l['cpu_per_s'] for r in out for l in r['lines'].values()]):.1f} ms of CPU per second of audio; {time.time()-t0:.0f} s")
