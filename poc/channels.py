"""Phone-line stand-ins: narrow the band to 300-3400 Hz at 8 kHz, then pass through a real codec with ffmpeg."""
import os, subprocess, tempfile, numpy as np
from wm import load, save, FS

NB = ["-af", "highpass=f=300,lowpass=f=3400", "-ar", "8000", "-ac", "1"]
CODECS = {
    "clean (no phone line)":      None,
    "G.711 mu-law (landline)":    (NB + ["-c:a", "pcm_mulaw"], "wav"),
    "G.726 32k":                  (NB + ["-c:a", "g726", "-b:a", "32k"], "wav"),
    "G.726 16k":                  (NB + ["-c:a", "g726", "-b:a", "16k"], "wav"),
    "Opus 12k (VoIP)":            (NB + ["-c:a", "libopus", "-b:a", "12k", "-application", "voip"], "ogg"),
    "Opus 6k (bad VoIP)":         (NB + ["-c:a", "libopus", "-b:a", "6k", "-application", "voip"], "ogg"),
    "iLBC 15.2k (CELP)":          (NB + ["-c:a", "ilbc_at"], "caf"),
    "G.723.1 6.3k (CELP, harsh)": (NB + ["-c:a", "g723_1", "-b:a", "6.3k"], "wav"),
}

def through(x, name):
    spec = CODECS[name]
    if spec is None: return x
    with tempfile.TemporaryDirectory() as d:
        src, mid = os.path.join(d, "in.wav"), os.path.join(d, "mid." + spec[1])
        save(src, x)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src] + spec[0] + [mid], check=True)
        return load(mid)

def tandem(x, names, noise_db=None, seed=1):
    for n in names: x = through(x, n)
    if noise_db is not None:
        rng = np.random.default_rng(seed)
        x = x + rng.standard_normal(len(x)) * np.sqrt(np.mean(x ** 2)) * 10 ** (-noise_db / 20)
    return x
