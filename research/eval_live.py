"""Real phone calls (Twilio -> US phone network -> LiveKit number -> tap), analysed from what the tap recorded.
Reads ../demo/rec/manifest.json and the recordings next to it. Writes results/live.json."""
import glob, json, sys
from multiprocessing import Pool
from scipy.signal import resample_poly, correlate
from common import *
from palabra_mark.stream import VoteStream, Scorer, SlipScorer, DualScorer

REC = os.path.join(ROOT, "..", "demo", "rec"); NWRONG = 200
MAKE = {"plain": lambda c: Scorer(c, tau=7.0), "slip": lambda c: SlipScorer(c, tau=7.75), "dual": lambda c: DualScorer(c)}
MAN = sys.argv[1] if len(sys.argv) > 1 else "manifest.json"

def source(m):
    if m["src"] == "agent": return os.path.join(ROOT, "..", "poc", "voices", m["voice"])
    return glob.glob(os.path.join(ROOT, "data/LibriSpeech/dev-clean-2/*/*", m["voice"]))[0]

def slip_ms(m, rec):
    """Largest change in delay during the greeting, from matching 0.5 s pieces of what was sent to what arrived."""
    x = load(source(m))[: 8 * FS]; x = x / (np.abs(x).max() + 1e-9) * 0.7
    if m["kind"] in ("marked", "replay", "replay-2nd"): x, _ = embed(x, bytes.fromhex(m["code"]), start=0)
    ref = resample_poly(x, 1, 2); lags = []
    for t0 in np.arange(0, len(ref) / 8000 - 0.5, 0.5):
        seg = ref[int(t0 * 8000): int((t0 + 0.5) * 8000)]
        if np.sqrt(np.mean(seg ** 2)) < 0.02 or len(rec) <= len(seg): continue
        lags.append((int(np.argmax(np.abs(correlate(rec, seg, "valid")))) - int(t0 * 8000)) / 8)
    return float(max(lags) - min(lags)) if lags else None

def job(m):
    e = m["event"] or {}; f = os.path.join(REC, f"{e.get('session')}_8000.s16")
    if not os.path.exists(f): return dict(m, missing=True)
    rec = np.frombuffer(open(f, "rb").read(), dtype="<i2") / 32768
    log = list(VoteStream(Config(), 8000).push(rec)); rng = np.random.default_rng(m["i"]); out = dict(m, slip_ms=slip_ms(m, rec), det={})
    hop = 160; n = len(rec) // hop; en = 10 * np.log10(np.mean(rec[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    onset = float(np.argmax(en > en.max() - 30) / 50)
    for name, mk in MAKE.items():
        S = mk(bytes.fromhex(m["code"]))
        for h, v in log: S.feed(h, v)
        wrong = []
        for _ in range(NWRONG):
            W = mk(rng.bytes(32))
            for h, v in log: W.feed(h, v)
            wrong.append(W.best)
        out["det"][name] = dict(best=S.best, t=None if S.verified_at is None else S.verified_at - onset, wrong=max(wrong))
    return out

if __name__ == "__main__":
    M = json.load(open(os.path.join(REC, MAN)))
    with Pool(12) as p: out = p.map(job, M, chunksize=1)
    json.dump(out, open(os.path.join(ROOT, "results", "live.json" if MAN == "manifest.json" else "live_" + MAN.replace("manifest_", "")), "w"))
    out = [o for o in out if not o.get("missing")]
    print(len(M), "calls,", len(out), "with a recording; twilio:", {s: sum(m["twilio"] == s for m in M) for s in set(m["twilio"] for m in M)})
    sl = [o["slip_ms"] for o in out if o["slip_ms"] is not None]
    for name in MAKE:
        print(f"\n{name}")
        for src in ("agent", "human"):
            R = [o["det"][name] for o in out if o["kind"] == "marked" and o["src"] == src]
            ts = [r["t"] for r in R]; f = lambda s: sum(t is not None and t <= s for t in ts)
            print(f"  marked {src}: {len(R)} calls, verified {sum(t is not None for t in ts)}, within 3 s {f(3)}, 5 s {f(5)}, median {np.median([t if t is not None else 99 for t in ts]):.1f} s")
        for kind in ("unmarked", "cross", "replay", "replay-2nd"):
            R = [o["det"][name] for o in out if o["kind"] == kind]
            if R: print(f"  {kind}: {len(R)} calls, passed {sum(r['t'] is not None for r in R)}, highest score {max(r['best'] for r in R):.2f}")
        print(f"  wrong codes: {NWRONG * len(out)} trials, highest {max(o['det'][name]['wrong'] for o in out):.2f}")
    print("\nlive service (as it ran):", {k: {t: sum(1 for m in M if m["kind"] == k and (m["event"] or {}).get("type") == t) for t in ("call.verified", "call.unverified", "call.unregistered")} for k in sorted(set(m["kind"] for m in M))})
