"""Streaming detector: a side tap on a live call.

The call audio is never held back. Copy each frame to `StreamDetector.push()` (from another task or thread)
and carry on; the tap only reads. It answers one of three states:

    listening  - not sure yet
    verified   - the expected mark is in the audio (score passed the mark)
    expired    - the caller has talked long enough and the mark did not show

The mark may start at any moment in the first `search` seconds (ringing, silence, "hello?"), so the tap
keeps one running score for every possible start. Scores are checked every 0.256 s of mark heard.
Works on 16 kHz or 8 kHz audio directly (8 kHz is what a phone trunk delivers).
"""
import math
import numpy as np
from .core import Config, pattern, FS, NFFT, HOP

CHECK, MIN_ROWS = 4, 8            # look at a score every 4 pattern rows, never before 8 rows (0.5 s)

class Scorer:
    """Scores one code against vote rows as they arrive. Knows nothing about audio."""
    def __init__(self, code: bytes, cfg: Config = Config(), tau=7.0, search=10.0, max_dur=8.0, restart=0, late=0.0):
        """restart: also score the mark from every `restart`-th row onwards, not only from its first row.
        A live line can slip in time early in a call (jitter buffers); a restart lets the score recover after a slip."""
        self.cfg, self.tau, self.restart = cfg, tau, restart
        self.late_rows = int(late / (cfg.tsec * cfg.tstep))          # late: the tap may have missed up to this many seconds of the mark
        self.seen = set()
        self.period = cfg.tt * cfg.tstep                              # hops per pattern row (8 = 64 ms)
        self.R = int(max_dur / cfg.tsec) // cfg.tstep
        self.s = pattern(code, self.R, cfg)
        self.spawn_until = int(search * FS / HOP)                     # in hops
        self.nseg = 1 if not restart else -(-self.R // restart)
        self.h = [dict(num=np.zeros(0), den=np.zeros(0), age=np.zeros(0, int), sn=np.zeros((0, self.nseg)), sd=np.zeros((0, self.nseg)))
                  for _ in range(self.period)]
        self.best, self.verified_at, self.heard = -np.inf, None, None

    @property
    def looks(self):
        per = lambda rows: max(0, rows // CHECK - MIN_ROWS // CHECK + 1)
        return (self.spawn_until + self.late_rows * self.period) * sum(per(self.R - j * (self.restart or self.R)) for j in range(self.nseg))
    @property
    def false_alarm_bound(self): return self.looks * math.exp(-self.tau ** 2 / 2)

    def feed(self, hop: int, v):
        """v: one row of votes (ncols) that ended at hop number `hop`. Returns True once verified."""
        h = self.h[hop % self.period]
        if self.late_rows and hop % self.period not in self.seen:     # marks that began before the tap started listening
            self.seen.add(hop % self.period); n = self.late_rows
            h["num"] = np.zeros(n); h["den"] = np.zeros(n); h["age"] = np.arange(1, n + 1)
            h["sn"] = np.full((n, self.nseg), np.nan); h["sd"] = np.zeros((n, self.nseg)); h["sn"][:, 0] = 0.0
        if hop - self.period < self.spawn_until:                      # a mark could start with this row
            h["num"] = np.append(h["num"], 0.0); h["den"] = np.append(h["den"], 0.0); h["age"] = np.append(h["age"], 0)
            h["sn"] = np.vstack([h["sn"], np.full((1, self.nseg), np.nan)]); h["sd"] = np.vstack([h["sd"], np.zeros((1, self.nseg))])
        if not len(h["age"]): return self.verified_at is not None
        if self.restart:                                              # remember the running sums at each restart row
            at = np.nonzero(h["age"] % self.restart == 0)[0]; j = h["age"][at] // self.restart
            h["sn"][at, j] = h["num"][at]; h["sd"][at, j] = h["den"][at]
        else:
            new = h["age"] == 0; h["sn"][new, 0] = 0.0
        h["num"] += self.s[h["age"]] @ v; h["den"] += float(v @ v); h["age"] += 1
        look = (h["age"] % CHECK == 0) & (h["age"] >= MIN_ROWS)
        if look.any():
            age = h["age"][look][:, None]; seg0 = np.arange(self.nseg)[None, :] * (self.restart or self.R)
            ok = (age - seg0 >= MIN_ROWS) & ~np.isnan(h["sn"][look])                 # segments long enough to judge
            z = np.where(ok, (h["num"][look][:, None] - np.nan_to_num(h["sn"][look])) / np.sqrt(h["den"][look][:, None] - h["sd"][look] + 1e-9), -np.inf)
            i, j = np.unravel_index(int(np.argmax(z)), z.shape)
            if z[i, j] > self.best: self.best = float(z[i, j])
            if z[i, j] >= self.tau and self.verified_at is None:
                self.verified_at = hop * HOP / FS
                self.heard = float((age[i, 0] - seg0[0, j]) * self.cfg.tsec * self.cfg.tstep)
        keep = h["age"] < self.R
        if not keep.all():
            for k in ("num", "den", "age", "sn", "sd"): h[k] = h[k][keep]
        return self.verified_at is not None

class VoteStream:
    """Turns audio into vote rows, one per 8 ms hop. Independent of any code, so it can feed many Scorers."""
    def __init__(self, cfg: Config = Config(), fs=FS):
        assert fs in (16000, 8000) and cfg.mode == "quad"
        self.cfg, self.k = cfg, FS // fs
        self.nfft, self.hop = NFFT // self.k, HOP // self.k           # same 32 ms window and 31.25 Hz bins at 8 kHz
        self.win = np.hanning(self.nfft + 1)[:-1]
        self.buf = np.zeros(0); self.n = 0
        self.ring = np.zeros((cfg.tt * 2, cfg.nbands))                # band energy of the last two tiles
        self.ref = -np.inf; self.sum = self.sq = self.cnt = 0.0

    def push(self, x):
        """x: float samples in [-1, 1]. Yields (hop number, votes) for each new row."""
        c = self.cfg
        self.buf = np.concatenate([self.buf, np.asarray(x, dtype=np.float64)])
        while len(self.buf) >= self.nfft:
            P = np.abs(np.fft.rfft(self.win * self.buf[: self.nfft])) ** 2
            self.buf = self.buf[self.hop:]
            E = P[c.bin0: c.bin0 + c.nbands * c.bw].reshape(c.nbands, c.bw).sum(1)
            self.ring = np.roll(self.ring, -1, axis=0); self.ring[-1] = E; self.n += 1
            self.ref = max(self.ref, 10 * math.log10(E.max() * c.tt + 1e-12))
            if self.n < 2 * c.tt: continue
            L = 10 * np.log10(self.ring.reshape(2, c.tt, c.nbands).sum(1) + 1e-12)
            A = L > self.ref - c.floor
            f = L[0, 0::2] - L[0, 1::2] - L[1, 0::2] + L[1, 1::2]
            a = (A[0, 0::2] & A[0, 1::2] & A[1, 0::2] & A[1, 1::2]).astype(float)
            self.sum += float((a * f).sum()); self.sq += float((a * f * f).sum()); self.cnt += float(a.sum())
            mu = self.sum / max(self.cnt, 1.0); sd = math.sqrt(max(self.sq / max(self.cnt, 1.0) - mu * mu, 0.0)) + 1e-9
            yield self.n, np.clip((f - mu) / sd, -c.clip, c.clip) * a

class StreamDetector:
    """The tap. push() audio as it arrives; read .state at any time."""
    def __init__(self, code: bytes, cfg: Config = Config(), fs=FS, tau=7.0, search=10.0, max_dur=8.0, restart=0, late=0.0, slips=False):
        self.votes = VoteStream(cfg, fs)
        self.scorer = DualScorer(code, cfg, search, max_dur, late) if slips else Scorer(code, cfg, tau, search, max_dur, restart, late)
        self.deadline = search + max_dur; self.t = 0.0; self.fs = fs

    def push(self, x):
        self.t += len(x) / self.fs
        if self.scorer.verified_at is None:
            for hop, v in self.votes.push(x): self.scorer.feed(hop, v)
        return self.state

    @property
    def state(self):
        if self.scorer.verified_at is not None: return "verified"
        return "expired" if self.t >= self.deadline else "listening"
    @property
    def score(self): return self.scorer.best
    @property
    def verified_at(self): return self.scorer.verified_at          # seconds into the stream

class SlipScorer:
    """Like Scorer, but survives a slip in time.

    On a live call the audio can jump or stretch by tens of milliseconds while a jitter buffer adapts. After a
    slip the mark is still there but out of step, so a plain score stalls. This scorer also tries, at every
    `seg` rows, (a) starting the count afresh and (b) carrying the score so far over to a mark shifted by up to
    `max_slip` hops (8 ms each). More things tried means a higher pass mark for the same false-alarm bound."""
    def __init__(self, code: bytes, cfg: Config = Config(), tau=7.75, search=10.0, max_dur=8.0, seg=8, max_slip=15):
        self.cfg, self.tau, self.seg, self.D = cfg, tau, seg, max_slip
        self.period = cfg.tt * cfg.tstep
        self.R = int(max_dur / cfg.tsec) // cfg.tstep
        self.s = pattern(code, self.R, cfg)
        self.spawn_until = int(search * FS / HOP)
        self.nseg = -(-self.R // seg)
        n = self.spawn_until + self.period + 2 * max_slip + 2; self.off = max_slip + 1      # origin o lives at index o + off
        self.num = np.zeros(n); self.den = np.zeros(n)
        self.sn = np.full((n, self.nseg), np.nan); self.sd = np.full((n, self.nseg), np.nan)
        self.a = np.arange(self.R); self.dv = np.arange(-max_slip, max_slip + 1)
        self.best, self.verified_at, self.heard = -np.inf, None, None

    @property
    def looks(self):
        per = lambda rows: max(0, rows // CHECK - MIN_ROWS // CHECK + 1)
        segs = sum(per(self.R - j * self.seg) for j in range(self.nseg))
        return self.spawn_until * (segs + 2 * self.D * (segs - per(self.R)))
    @property
    def false_alarm_bound(self): return self.looks * math.exp(-self.tau ** 2 / 2)

    def feed(self, hop: int, v):
        o = hop - self.period * self.a                                 # origins whose next row this is; age = self.a
        m = (o >= 2 * self.cfg.tt) & (o - self.period < self.spawn_until)
        if not m.any(): return self.verified_at is not None
        a, i = self.a[m], o[m] + self.off
        snap = a % self.seg == 0
        self.sn[i[snap], a[snap] // self.seg] = self.num[i[snap]]; self.sd[i[snap], a[snap] // self.seg] = self.den[i[snap]]
        self.num[i] += self.s[a] @ v; self.den[i] += float(v @ v); n = a + 1
        look = (n % CHECK == 0) & (n >= MIN_ROWS)
        if look.any():
            i2, n2 = i[look], n[look]; J = np.arange(self.nseg)
            ok = (n2[:, None] - J[None, :] * self.seg >= MIN_ROWS)                              # (m, nseg) tail long enough
            tn = self.num[i2][:, None] - self.sn[i2]; td = self.den[i2][:, None] - self.sd[i2]  # tail sums from each restart
            with np.errstate(invalid="ignore"):
                z1 = np.where(ok, tn / np.sqrt(td + 1e-9), np.nan)                              # fresh start at row j*seg
                i1 = i2[:, None] - self.dv[None, :]                                             # the origin before the slip
                hn = self.sn[i1]; hd = self.sd[i1]                                              # (m, nd, nseg) head sums up to row j*seg
                z2 = np.where(ok[:, None, :], (hn + tn[:, None, :]) / np.sqrt(hd + td[:, None, :] + 1e-9), np.nan)
            z2[:, :, 0] = np.nan                                                                # no head before row 0
            zb = max(np.nanmax(z1) if np.isfinite(z1).any() else -np.inf, np.nanmax(z2) if np.isfinite(z2).any() else -np.inf)
            if zb > self.best: self.best = float(zb)
            if zb >= self.tau and self.verified_at is None:
                self.verified_at = hop * HOP / FS
                self.heard = float(n2[int(np.nanargmax(np.nanmax(np.where(np.isfinite(z2), z2, -np.inf), axis=(1, 2))))] * self.cfg.tsec * self.cfg.tstep)
        return self.verified_at is not None

class DualScorer:
    """Plain and slip-tolerant scorers side by side; the call passes when either does. Ordinary calls verify as
    fast as before, and a call whose timing slipped still has a way through. The false-alarm bounds add."""
    def __init__(self, code: bytes, cfg: Config = Config(), search=10.0, max_dur=8.0, late=0.0):
        self.a = Scorer(code, cfg, 7.0, search, max_dur, late=late); self.b = SlipScorer(code, cfg, 7.75, search, max_dur)
        self.tau = 7.0
    def feed(self, hop, v): self.a.feed(hop, v); self.b.feed(hop, v); return self.verified_at is not None
    @property
    def verified_at(self):
        t = [x for x in (self.a.verified_at, self.b.verified_at) if x is not None]; return min(t) if t else None
    @property
    def heard(self): return self.a.heard if self.a.verified_at is not None else self.b.heard
    @property
    def best(self): return max(self.a.best, self.b.best - 0.75)                 # on the plain scorer's scale: 7 is the pass mark
    @property
    def looks(self): return self.a.looks + self.b.looks
    @property
    def false_alarm_bound(self): return self.a.false_alarm_bound + self.b.false_alarm_bound
