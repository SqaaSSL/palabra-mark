import glob, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))
import numpy as np
from palabra_mark import *
from palabra_mark.channels import through, bridge, ALL

ROOT = os.path.dirname(os.path.abspath(__file__))
def librispeech(min_s=8.5):
    """{speaker: [paths]} of utterances at least min_s long (by file size: 16 kHz flac is ~ 16-20 kB/s)."""
    out = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "data/LibriSpeech/dev-clean-2/*/*/*.flac"))):
        if os.path.getsize(p) > min_s * 22000: out.setdefault(p.split(os.sep)[-3], []).append(p)
    return out
def split():
    """Speakers are split once: even positions tune the design (dev), odd positions are held out (test)."""
    sp = sorted(librispeech())
    return sp[0::2], sp[1::2]
def clip8(path, secs=8.0):
    x = load(path)[: int(secs * FS)]
    return x / (np.abs(x).max() + 1e-9) * 0.7
