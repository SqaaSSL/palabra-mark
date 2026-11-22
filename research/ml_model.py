"""Learned front-end for the Palabra detector.

The network turns the received spectrogram into one real number per vote. It never sees the code, so the
false-alarm bound of the analytic detector still holds: for a wrong code the keyed signs are independent of
the network's output, whatever the network computes."""
import torch, torch.nn as nn

class VoteNet(nn.Module):
    def __init__(self, ch=48):
        super().__init__()
        def c(i, o, k, d=(1, 1)): return nn.Sequential(nn.Conv2d(i, o, k, padding=(d[0] * (k[0] // 2), d[1] * (k[1] // 2)), dilation=d), nn.GELU())
        self.body = nn.Sequential(c(1, 32, (5, 5)), c(32, ch, (3, 3)), c(ch, ch, (3, 3), (2, 2)), c(ch, ch, (3, 3), (4, 2)), c(ch, ch, (3, 3), (8, 4)))
        self.pool = nn.Sequential(nn.Conv2d(ch, ch, (8, 12), stride=(8, 12)), nn.GELU())      # one cell per vote: 64 ms x 375 Hz
        self.head = nn.Sequential(nn.Conv2d(ch + 1, ch, 3, padding=1), nn.GELU(), nn.Conv2d(ch, 1, 1))
        nn.init.zeros_(self.head[-1].weight); nn.init.zeros_(self.head[-1].bias)
        self.a = nn.Parameter(torch.tensor(1.0))
    def forward(self, S, B):
        """S: (batch, frames, 96) scaled log spectrum. B: (batch, rows, 8) analytic votes. Returns votes (batch, rows, 8)."""
        h = self.pool(self.body(S.unsqueeze(1)))
        return self.a * B + self.head(torch.cat([h, B.unsqueeze(1)], 1)).squeeze(1)

def zscore(V, s):
    """Match score per example, using all votes."""
    return (V * s).sum((1, 2)) / torch.sqrt((V ** 2).sum((1, 2)) + 1e-6)

class VoteNet2(nn.Module):
    """A deeper front-end with the same inputs and outputs as VoteNet: residual blocks at half resolution, then a
    few layers at one cell per vote that also see the analytic votes. Like VoteNet, it never sees the code."""
    def __init__(self, ch=96, blocks=8, head=3):
        super().__init__()
        class Res(nn.Module):
            def __init__(s, c, d, k=3):
                super().__init__(); p = (d[0] * (k // 2), d[1] * (k // 2))
                s.f = nn.Sequential(nn.GroupNorm(8, c), nn.GELU(), nn.Conv2d(c, c, k, padding=p, dilation=d),
                                    nn.GroupNorm(8, c), nn.GELU(), nn.Conv2d(c, c, k, padding=p, dilation=d))
                nn.init.zeros_(s.f[-1].weight); nn.init.zeros_(s.f[-1].bias)
            def forward(s, x): return x + s.f(x)
        dil = [(1, 1), (2, 1), (4, 2), (8, 2)]
        self.stem = nn.Sequential(nn.Conv2d(1, 32, 5, padding=2), nn.GELU(), nn.Conv2d(32, ch, 3, stride=2, padding=1))   # then work at 16 ms x 62.5 Hz
        self.body = nn.Sequential(*[Res(ch, dil[i % 4]) for i in range(blocks)])
        self.pool = nn.Sequential(nn.GroupNorm(8, ch), nn.GELU(), nn.Conv2d(ch, ch, (4, 6), stride=(4, 6)))   # one cell per vote
        self.mix = nn.Conv2d(ch + 1, ch, 3, padding=1)
        self.head = nn.Sequential(*[Res(ch, (1, 1)) for _ in range(head)], nn.GroupNorm(8, ch), nn.GELU(), nn.Conv2d(ch, 1, 1))
        nn.init.zeros_(self.head[-1].weight); nn.init.zeros_(self.head[-1].bias)
        self.a = nn.Parameter(torch.tensor(1.0))
    def forward(self, S, B):
        h = self.pool(self.body(self.stem(S.unsqueeze(1))))
        return self.a * B + self.head(self.mix(torch.cat([h, B.unsqueeze(1)], 1))).squeeze(1)

class VoteNet3(nn.Module):
    """Streaming front-end. One pass over the audio gives a row of votes at every 16 ms step, for the 64 ms pattern
    row that ended `look` steps earlier. Every layer is causal in time, so a vote never uses audio later than
    `look` steps (16 ms each) after its row, and the net can run frame by frame with a little cached state.
    Inputs come from ml_feat.py; like the other nets, it never sees the code.

    ch, blocks set the cost: about 18 * ch^2 * blocks * 1500 multiply-adds per second of audio."""
    def __init__(self, ch=48, blocks=6, look=4):
        super().__init__(); self.look = look
        class Norm(nn.Module):                                   # normalises each time step on its own (causal, and the same in streaming)
            def __init__(s, c): super().__init__(); s.g = nn.GroupNorm(min(8, c // 4), c)
            def forward(s, x): b, c, t, f = x.shape; return s.g(x.permute(0, 2, 1, 3).reshape(b * t, c, f)).reshape(b, t, c, f).permute(0, 2, 1, 3)
        class Conv(nn.Module):                                   # looks back in time only
            def __init__(s, i, o, kt, kf, d=1, sf=1): super().__init__(); s.p = (kt - 1) * d; s.c = nn.Conv2d(i, o, (kt, kf), dilation=(d, 1), stride=(1, sf), padding=(0, kf // 2))
            def forward(s, x): return s.c(nn.functional.pad(x, (0, 0, s.p, 0)))
        class Res(nn.Module):
            def __init__(s, c, d):
                super().__init__(); s.f = nn.Sequential(Norm(c), nn.GELU(), Conv(c, c, 3, 3, d), Norm(c), nn.GELU(), Conv(c, c, 3, 3, d))
                nn.init.zeros_(s.f[-1].c.weight); nn.init.zeros_(s.f[-1].c.bias)
            def forward(s, x): return x + s.f(x)
        self.stem = nn.Sequential(Conv(1, ch // 2, 3, 5, sf=2), nn.GELU(), Conv(ch // 2, ch, 3, 3, sf=2))      # 96 bins -> 24 (125 Hz each)
        self.body = nn.Sequential(*[Res(ch, (1, 2, 4, 8)[i % 4]) for i in range(blocks)])
        self.pool = nn.Sequential(Norm(ch), nn.GELU(), nn.Conv2d(ch, ch, (1, 3), stride=(1, 3)))             # 24 -> 8: one cell per vote
        self.mix = Conv(ch + 1, ch, 1, 3)
        self.head = nn.Sequential(Res(ch, 4), Norm(ch), nn.GELU(), nn.Conv2d(ch, 1, 1))                       # dilation 4 = the rows before
        nn.init.zeros_(self.head[-1].weight); nn.init.zeros_(self.head[-1].bias)
        self.a = nn.Parameter(torch.tensor(1.0))
    def forward(self, S, B):
        """S: (batch, steps, 96). B: (batch, steps, 8) analytic votes. Returns (batch, steps, 8); step t holds the votes of the row that ended at t - look."""
        Bs = nn.functional.pad(B, (0, 0, self.look, 0))[:, : B.shape[1]]
        h = self.pool(self.body(self.stem(S.unsqueeze(1))))
        return self.a * Bs + self.head(self.mix(torch.cat([h, Bs.unsqueeze(1)], 1))).squeeze(1)
