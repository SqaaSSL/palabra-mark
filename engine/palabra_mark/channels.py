"""Phone-line bridge: sends audio through real telephone codecs.

Everything is narrowed to 300-3400 Hz at 8 kHz first, as a phone network does. Codecs come from the local
ffmpeg; AMR (the mobile-network codec) is encoded inside a Docker container named `palabra-codecs`:
  docker run -d --name palabra-codecs -v <tmpdir>:/w --entrypoint sleep linuxserver/ffmpeg infinity

Wideband mobile lines (AMR-WB and EVS, as on VoLTE) keep 50-7000 Hz at 16 kHz instead. Their encoders are
built once by research/setup_codecs.sh into research/codecs/bin (or the directory in PALABRA_CODECS).
"""
import os, subprocess, uuid
import numpy as np
from .core import load, save

TMP = os.environ.get("PALABRA_TMP", os.path.join(os.path.dirname(__file__), "..", "..", "research", "tmp"))
NB = ["-af", "highpass=f=300,lowpass=f=3400", "-ar", "8000", "-ac", "1"]
LOCAL = {
    "G.711":        (["-c:a", "pcm_mulaw"], "wav"),
    "G.726-32":     (["-c:a", "g726", "-b:a", "32k"], "wav"),
    "G.726-16":     (["-c:a", "g726", "-b:a", "16k"], "wav"),
    "iLBC-15.2":    (["-c:a", "ilbc_at"], "caf"),
    "G.723.1-6.3":  (["-c:a", "g723_1", "-b:a", "6.3k"], "wav"),
    "Opus-24":      (["-c:a", "libopus", "-b:a", "24k", "-application", "voip"], "ogg"),
    "Opus-16":      (["-c:a", "libopus", "-b:a", "16k", "-application", "voip"], "ogg"),
    "Opus-12":      (["-c:a", "libopus", "-b:a", "12k", "-application", "voip"], "ogg"),
    "Opus-8":       (["-c:a", "libopus", "-b:a", "8k", "-application", "voip"], "ogg"),
    "Opus-6":       (["-c:a", "libopus", "-b:a", "6k", "-application", "voip"], "ogg"),
}
DOCKER = {f"AMR-{r}": (["-c:a", "libopencore_amrnb", "-b:a", f"{r}k"], "amr") for r in ("12.2", "7.95", "5.9", "4.75")}
BIN = os.environ.get("PALABRA_CODECS", os.path.join(os.path.dirname(__file__), "..", "..", "research", "codecs", "bin"))
WB = ["-af", "highpass=f=50,lowpass=f=7000", "-ar", "16000", "-ac", "1"]
AMRWB = {f"AMR-WB-{r}": int(round(float(r) * 1000)) for r in ("23.85", "12.65", "8.85", "6.6")}
EVS = {f"EVS-{r}": int(round(float(r) * 1000)) for r in ("24.4", "13.2", "9.6", "7.2", "5.9")}      # 5.9 is variable-rate
WIDE = list(AMRWB) + list(EVS)
ALL = ["clean"] + list(LOCAL) + list(DOCKER) + WIDE

def _wideband(x, name, u):
    """AMR-WB (VisualOn encoder, ffmpeg decoder) or EVS (3GPP reference encoder and decoder), 16 kHz in and out."""
    q = dict(check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    src = os.path.join(TMP, u + ".wav"); made = [src]; save(src, x)
    try:
        if name in AMRWB:
            wav, mid = os.path.join(TMP, u + "_w.wav"), os.path.join(TMP, u + "_o.amr"); made += [wav, mid]
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src] + WB + ["-c:a", "pcm_s16le", wav], check=True)
            subprocess.run([os.path.join(BIN, "amrwb-enc"), "-r", str(AMRWB[name]), wav, mid], **q)
            return load(mid)
        pcm, bits, dec = (os.path.join(TMP, u + e) for e in ("_i.pcm", ".192", "_o.pcm")); made += [pcm, bits, dec]
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src] + WB + ["-f", "s16le", pcm], check=True)
        subprocess.run([os.path.join(BIN, "EVS_cod")] + (["-dtx"] if EVS[name] == 5900 else []) + [str(EVS[name]), "16", pcm, bits], **q)   # 5.9 only runs with DTX
        subprocess.run([os.path.join(BIN, "EVS_dec"), "16", bits, dec], **q)
        return np.fromfile(dec, dtype="<i2").astype(np.float64) / 32768
    finally:
        for p in made:
            if os.path.exists(p): os.remove(p)

def through(x, name):
    if name == "clean": return x
    os.makedirs(TMP, exist_ok=True)
    u = uuid.uuid4().hex; src = os.path.join(TMP, u + ".wav")
    if name in WIDE: return _wideband(x, name, u)
    try:
        if name in LOCAL:
            opts, ext = LOCAL[name]; mid = os.path.join(TMP, f"{u}_o.{ext}"); save(src, x)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src] + NB + opts + [mid], check=True)
        else:
            opts, ext = DOCKER[name]; mid = os.path.join(TMP, f"{u}_o.{ext}"); save(src, x)
            subprocess.run(["docker", "exec", "palabra-codecs", "ffmpeg", "-v", "error", "-y", "-i", f"/w/{u}.wav"] + NB + opts + [f"/w/{u}_o.{ext}"], check=True)
        return load(mid)
    finally:
        for p in (src, locals().get("mid")):
            if p and os.path.exists(p): os.remove(p)

def bridge(x, chain, noise_db=None, seed=1):
    """Pass x through each codec in `chain` in turn; optionally add white noise at the end (SNR in dB)."""
    for n in chain: x = through(x, n)
    if noise_db is not None:
        rng = np.random.default_rng(seed)
        x = x + rng.standard_normal(len(x)) * np.sqrt(np.mean(x ** 2)) * 10 ** (-noise_db / 20)
    return x
