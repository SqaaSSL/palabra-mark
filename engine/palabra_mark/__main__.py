"""Command line for the Palabra mark.

  python -m palabra_mark mark   in.wav out.wav --secret S --caller +999555000427 --callee +999555000010 --slot 2026-11-21T09:14
  python -m palabra_mark verify call.wav       --secret S --caller +999555000427 --callee +999555000010 --slot 2026-11-21T09:14
  python -m palabra_mark bridge in.wav out.wav --line AMR-12.2 --line G.711
"""
import argparse, json, sys
import numpy as np
from .core import Config, Detector, embed, call_code, load, save, FS

THRESHOLD = 7.0     # false-alarm probability per wrong code is provably below 2e-7 at this score (see the paper)

def main(argv=None):
    ap = argparse.ArgumentParser(prog="palabra_mark"); sub = ap.add_subparsers(dest="cmd", required=True)
    def call_args(p):
        p.add_argument("--secret", required=True); p.add_argument("--caller", required=True)
        p.add_argument("--callee", required=True); p.add_argument("--slot", required=True, help="time slot, e.g. 2026-11-21T09:14")
    m = sub.add_parser("mark", help="write the mark for one call into a recording"); m.add_argument("src"); m.add_argument("dst"); call_args(m)
    v = sub.add_parser("verify", help="check a received recording against the call it claims to be"); v.add_argument("src"); call_args(v)
    v.add_argument("--threshold", type=float, default=THRESHOLD)
    b = sub.add_parser("bridge", help="send a recording through phone codecs"); b.add_argument("src"); b.add_argument("dst")
    b.add_argument("--line", action="append", required=True); b.add_argument("--noise-db", type=float)
    a = ap.parse_args(argv)
    if a.cmd == "bridge":
        from .channels import bridge
        save(a.dst, bridge(load(a.src), a.line, a.noise_db)); return 0
    code = call_code(a.secret.encode(), a.caller, a.callee, a.slot)
    if a.cmd == "mark":
        y, start = embed(load(a.src), code); save(a.dst, y)
        print(json.dumps({"marked": a.dst, "mark_starts_s": round(start / FS, 3)})); return 0
    x = load(a.src); D = Detector(x, max_dur=min(8.0, len(x) / FS)); t, z = D.curve(code)
    hit = np.nonzero(z >= a.threshold)[0]
    print(json.dumps({"verified": bool(len(hit)), "score": round(float(z.max()), 2), "threshold": a.threshold,
                      "seconds_needed": round(float(t[hit[0]]), 2) if len(hit) else None, "listened_s": round(float(t[-1]), 2)}))
    return 0 if len(hit) else 1

if __name__ == "__main__": sys.exit(main())
