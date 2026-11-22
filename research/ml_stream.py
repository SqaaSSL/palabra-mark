"""The streaming learned detector as a live tap would run it, and its test on the recorded live calls.

learned_rows(rec, net) turns 8 kHz (or 16 kHz) audio into vote rows for palabra_mark.stream.Scorer, as VoteStream does,
but with the votes computed by the network of Section 6.13 (ml_model.VoteNet3). The network runs on every second
8 ms hop and gives the votes of a row `look` steps (16 ms each) after the row ended; that wait is counted in the
times reported. This file is the reference that the TypeScript port is checked against.

Run:  python ml_stream.py [weights] [manifest.json ...]     writes results/live_learned.json"""
import json, sys, math
import numpy as np, torch
from common import *
from palabra_mark.core import NFFT, HOP
from palabra_mark.stream import VoteStream, Scorer
from ml_model import VoteNet3

CFG = Config(); NBIN = CFG.nbands * CFG.bw; TAU = 7.0; NWRONG = 200

def stream_feats(rec, fs=8000):
    """Per 8 ms hop n = 1, 2, ...: the network's two inputs. S[n-1]: the 96 bins of the phone band in dB below the
    loudest frame so far, scaled. B[n-1]: the analytic votes of the row that ends at hop n (zero before hop 8)."""
    vs = VoteStream(CFG, fs); k = FS // fs; nfft, hop = NFFT // k, HOP // k; n = max(0, (len(rec) - nfft) // hop + 1)
    S = np.zeros((n, NBIN), np.float32); B = np.zeros((n, CFG.ncols), np.float32); ref = -np.inf
    for h, v in vs.push(rec): B[h - 1] = v
    for i in range(n):
        P = np.abs(np.fft.rfft(vs.win * rec[i * hop: i * hop + nfft])) ** 2; band = P[CFG.bin0: CFG.bin0 + NBIN]
        ref = max(ref, 10 * math.log10(band.reshape(CFG.nbands, CFG.bw).sum(1).max() * CFG.tt + 1e-12))
        S[i] = np.clip(10 * np.log10(band + 1e-12) - ref, -70, 5) / 20
    return S, B

def load_net(path):
    c = torch.load(path, map_location="cpu"); net = VoteNet3(c["ch"], c["blocks"], c["look"]); net.load_state_dict(c["state"]); return net.eval()

def learned_rows(rec, net, fs=8000):
    """[(hop the row ended at, votes, hop at which the votes are known)]. One pass: rows that end at even hops."""
    S, B = stream_feats(rec, fs)
    with torch.no_grad(): V = net(torch.from_numpy(S[1::2])[None], torch.from_numpy(B[1::2])[None])[0].numpy().astype(np.float64)
    out = []; d = 2 * net.look
    for j in range(net.look, len(V)):
        now = 2 * j + 2; h = now - d
        if h >= 2 * CFG.tt: out.append((h, V[j] * (B[h - 1] != 0), now))
    return out

def run(code, rows, tau=TAU, stop=True):
    """Feeds a Scorer; returns (best score, seconds into the stream at which it verified or None, seconds of mark heard).
    stop: end at the first pass, as a tap does; otherwise the best score is over the whole recording."""
    sc = Scorer(code, tau=tau); at = None
    for r in rows:
        if sc.feed(r[0], r[1]) and at is None:
            at = (r[2] if len(r) > 2 else r[0]) * HOP / FS
            if stop: break
    return sc.best, at, sc.heard

if __name__ == "__main__":
    args = sys.argv[1:]; W = next((a for a in args if a.endswith(".pt")), "results/votenet3_c24.pt"); net = load_net(W)
    mans = [a for a in args if a.endswith(".json")] or ["manifest.json", "manifest_rev.json"]; REC = os.path.join(ROOT, "..", "demo", "rec"); out = []
    for man in mans:
        for m in json.load(open(os.path.join(REC, man))):
            e = m["event"] or {}; f = os.path.join(REC, f"{e.get('session')}_8000.s16")
            if not os.path.exists(f): continue
            rec = np.frombuffer(open(f, "rb").read(), dtype="<i2") / 32768; code = bytes.fromhex(m["code"]); rng = np.random.default_rng(m["i"])
            A = list(VoteStream(CFG, 8000).push(rec)); L = learned_rows(rec, net); wrong = [rng.bytes(32) for _ in range(NWRONG)]
            r = dict(manifest=man, i=m["i"], kind=m["kind"], voice=m["voice"], secs=len(rec) / 8000)
            for name, rows in (("analytic", A), ("learned", L)):
                best, at, heard = run(code, rows, stop=False); r[name] = dict(best=best, at=at, heard=heard, wrong=max(run(w, rows, stop=False)[0] for w in wrong))
            out.append(r); print(man[:-5], m["i"], m["kind"], {k: (round(r[k]["best"], 2), r[k]["at"]) for k in ("analytic", "learned")}, flush=True)
    json.dump(dict(weights=os.path.basename(W), look_ms=net.look * 16, calls=out), open("results/live_learned.json", "w"), indent=1)
    for kind in sorted({r["kind"] for r in out}):
        R = [r for r in out if r["kind"] == kind]; print(f"\n{kind} ({len(R)} calls)")
        for k in ("analytic", "learned"):
            t = np.array([np.nan if r[k]["at"] is None else r[k]["at"] for r in R]); h = np.array([np.nan if r[k]["heard"] is None else r[k]["heard"] for r in R])
            print(f"  {k:9} passed {int((~np.isnan(t)).sum())}; mark heard before passing: median {np.nanmedian(h) if (~np.isnan(h)).any() else float('nan'):.2f} s, "
                  f"within 2 s {int((h <= 2).sum())}, within 3 s {int((h <= 3).sum())}; best score mean {np.mean([r[k]['best'] for r in R]):.2f}, max {max(r[k]['best'] for r in R):.2f}")
    for k in ("analytic", "learned"): print(f"wrong codes, {k}: {len(out) * NWRONG:,} trials, highest {max(r[k]['wrong'] for r in out):.2f}")
