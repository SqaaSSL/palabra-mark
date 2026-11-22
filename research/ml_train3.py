"""Trains the streaming detector VoteNet3 on results/ml_train3.npz (written for a rented GPU).
Usage: python ml_train3.py [ch=48] [blocks=6] [look=4] [epochs=10] [out=votenet3.pt] [data=results/ml_train3.npz]"""
import sys, time, json, numpy as np, torch
from ml_model import VoteNet3
arg = dict(a.split("=") for a in sys.argv[1:]); CH, BL, LOOK, EPOCHS = (int(arg.get(k, d)) for k, d in (("ch", 48), ("blocks", 6), ("look", 4), ("epochs", 10)))
OUT = arg.get("out", "votenet3.pt"); DATA = arg.get("data", "results/ml_train3.npz"); BS = 64; TAU = 7.0; ROW = 0.064; PRE = 32; LO, QSTEP = -3.5, 3.75 / 255
torch.manual_seed(0); dev = arg["dev"] if "dev" in arg else "cuda" if torch.cuda.is_available() else "cpu"
d = np.load(DATA); spk = d["spk"]; wide = torch.from_numpy(d["wide"])
S = torch.from_numpy(d["S"]).to(dev); B = torch.from_numpy(d["B"].astype(np.float32)).to(dev); T = torch.from_numpy(d["T"].astype(np.float32)).to(dev)
ROWS = T.shape[1]; at = PRE + 3 + 4 * torch.arange(ROWS, device=dev)                  # step at which row r ends
held = sorted(set(spk.tolist()))[::12]; isva = np.isin(spk, held); va, tr = np.nonzero(isva)[0], np.nonzero(~isva)[0]      # validation: speakers never trained on
net = VoteNet3(CH, BL, LOOK).to(dev); opt = torch.optim.AdamW(net.parameters(), 1e-3, weight_decay=1e-4)
sched = torch.optim.lr_scheduler.OneCycleLR(opt, 2e-3, total_steps=EPOCHS * (len(tr) // BS), pct_start=0.15)
amp = dev == "cuda"; scaler = torch.amp.GradScaler(enabled=amp)
def votes(j, train=False):
    s = S[j].float() * QSTEP + LO; b = B[j]; k = 0
    if train:
        s = s + (torch.rand_like(s) - 0.5) * QSTEP + (torch.rand(len(j), 1, 1, device=dev) - 0.5) * 0.3      # undo the 8-bit steps; shift the level by up to 3 dB
        k = int(np.random.randint(0, PRE + 1)); s, b = s[:, k:], b[:, k:]                                       # vary how much audio comes before the mark
    with torch.autocast("cuda", enabled=amp): v = net(s, b)
    return v.float()[:, at - k + LOOK] * (B[j][:, at] != 0)                         # a vote the analytic rule calls silent stays silent
def curve(V, t): return torch.cumsum((V * t).sum(2), 1) / torch.sqrt(torch.cumsum((V ** 2).sum(2), 1) + 1e-6)
def report(Z):
    """Share of examples past the pass mark within 2, 3 and 5 s of audio (the look-ahead counts), and the mean score at 6 s."""
    f = lambda z: [round(float((z[:, :int((s - LOOK * 0.016) / ROW)].max(1).values >= TAU).float().mean()), 3) for s in (2, 3, 5)] + [round(float(z[:, -1].mean()), 2)]
    w = wide[va]; return dict(all=f(Z), narrow=f(Z[~w]), wide=f(Z[w]))
def val():
    net.eval(); zs = []
    with torch.no_grad():
        for i in range(0, len(va), 256): j = va[i:i + 256]; zs.append(curve(votes(j), T[j]).cpu())
    net.train(); return report(torch.cat(zs))
LOOK0 = LOOK; LOOK = 0; base = report(curve(B[va][:, at], T[va]).cpu()); LOOK = LOOK0
print(f"{dev}; ch {CH} blocks {BL} look {LOOK}; params {sum(p.numel() for p in net.parameters()):,}; train {len(tr)}, validation {len(va)} ({len(held)} speakers)")
print("pass by 2 s, 3 s, 5 s; mean score at 6 s\nanalytic", json.dumps(base), flush=True)
t0 = time.time(); best = (-1, None)
for ep in range(EPOCHS):
    perm = tr[np.random.default_rng(ep).permutation(len(tr))]; tot = 0
    for i in range(0, len(perm) - BS + 1, BS):
        j = perm[i:i + BS]; r = np.random.randint(12, ROWS + 1)                      # prefixes from 0.8 s to 6 s
        V = votes(j, True)[:, :r]; t = T[j][:, :r]
        loss = -((V * t).sum((1, 2)) / torch.sqrt((V ** 2).sum((1, 2)) + 1e-6) / r ** 0.5).mean()
        opt.zero_grad(set_to_none=True); scaler.scale(loss).backward(); scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(net.parameters(), 2.0)
        scaler.step(opt); scaler.update(); sched.step(); tot += loss.item()
    v = val(); print(f"epoch {ep + 1:2} loss {tot / (len(perm) // BS):.4f} {json.dumps(v)} {time.time() - t0:.0f}s", flush=True)
    if sum(v["all"][:3]) > best[0]: best = (sum(v["all"][:3]), v); torch.save(dict(ch=CH, blocks=BL, look=LOOK, state={k: t.float().cpu() for k, t in net.state_dict().items()}), OUT)
print("saved", OUT, "validation", json.dumps(best[1])); print("DONE", flush=True)
