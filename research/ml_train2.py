"""Trains VoteNet2 on results/ml_train2.npz. Written to run on a rented GPU (see colab_train.sh) but also runs on
a Mac. Usage: python ml_train2.py [loss=mean|pass] [ch=96] [epochs=30] [out=votenet2.pt]

loss=mean   the mean score, as ml_train.py.
loss=pass   pushes the score past the pass mark: easy examples stop counting once they pass, so the effort
            goes to the slow ones, which are what sets the time to verify."""
import sys, time, json, numpy as np, torch, torch.nn.functional as F
from ml_model import VoteNet2, zscore
arg = dict(a.split("=") for a in sys.argv[1:]); LOSS = arg.get("loss", "mean"); CH = int(arg.get("ch", 96)); EPOCHS = int(arg.get("epochs", 30)); OUT = arg.get("out", "votenet2.pt")
DATA = arg.get("data", "results/ml_train2.npz"); BS = 64; TAU = 7.0; ROW = 0.064
torch.manual_seed(0); dev = arg["dev"] if "dev" in arg else "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
d = np.load(DATA); lo, step = float(d["lo"]), float(d["step"]); spk = d["spk"]; wide = torch.from_numpy(d["wide"])
S = torch.from_numpy(d["S"]).to(dev); B = torch.from_numpy(d["B"].astype(np.float32)).to(dev); T = torch.from_numpy(d["T"].astype(np.float32)).to(dev)
held = sorted(set(spk.tolist()))[::9]; isva = np.isin(spk, held); va, tr = np.nonzero(isva)[0], np.nonzero(~isva)[0]      # validation: speakers never trained on
def inp(j, train=False):
    s = S[j].float() * step + lo
    if train: s = s + (torch.rand_like(s) - 0.5) * step + (torch.rand(len(j), 1, 1, device=dev) - 0.5) * 0.3     # undo the 8-bit steps; shift the level by up to 3 dB
    return s
net = VoteNet2(CH).to(dev); opt = torch.optim.AdamW(net.parameters(), 1e-3, weight_decay=1e-4)
steps = EPOCHS * (len(tr) // BS); sched = torch.optim.lr_scheduler.OneCycleLR(opt, 2e-3, total_steps=steps, pct_start=0.15)
amp = dev == "cuda"; scaler = torch.amp.GradScaler(enabled=amp)
def votes(j, train=False):
    with torch.autocast("cuda", enabled=amp): v = net(inp(j, train), B[j])
    return v.float() * (B[j] != 0)                                       # a vote the analytic rule calls silent stays silent
def curve(V, t): return torch.cumsum((V * t).sum(2), 1) / torch.sqrt(torch.cumsum((V ** 2).sum(2), 1) + 1e-6)     # score after each row
def report(Z):
    """Share of examples past the pass mark by 2, 3 and 5 s, and the mean score at 6 s."""
    f = lambda z: [round(float((z[:, :int(s / ROW)].max(1).values >= TAU).float().mean()), 3) for s in (2, 3, 5)] + [round(float(z[:, -1].mean()), 2)]
    w = wide[va]; return dict(all=f(Z), narrow=f(Z[~w]), wide=f(Z[w]))
def val():
    net.eval(); zs = []
    with torch.no_grad():
        for i in range(0, len(va), 128): j = va[i:i + 128]; zs.append(curve(votes(j), T[j]).cpu())
    net.train(); return report(torch.cat(zs))
base = report(curve(B[va], T[va]).cpu())
print(f"{dev}; loss {LOSS}; params {sum(p.numel() for p in net.parameters()):,}; train {len(tr)}, validation {len(va)} ({len(held)} speakers)")
print("pass by 2 s, 3 s, 5 s; mean score at 6 s\nanalytic", json.dumps(base), flush=True)
t0 = time.time(); best = (-1, None)
for ep in range(EPOCHS):
    perm = tr[np.random.default_rng(ep).permutation(len(tr))]; tot = 0
    for i in range(0, len(perm) - BS + 1, BS):
        j = perm[i:i + BS]; r = np.random.randint(12, 94)               # prefixes from 0.8 s to 6 s
        z = zscore(votes(j, True)[:, :r], T[j][:, :r])
        loss = -(z / r ** 0.5).mean() if LOSS == "mean" else F.softplus(TAU + 1 - z).mean() / 4
        opt.zero_grad(set_to_none=True); scaler.scale(loss).backward(); scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(net.parameters(), 2.0)
        scaler.step(opt); scaler.update(); sched.step(); tot += loss.item()
    v = val(); print(f"epoch {ep + 1:2} loss {tot / (len(perm) // BS):.4f} {json.dumps(v)} {time.time() - t0:.0f}s", flush=True)
    score = sum(v["all"][:3])
    if ep >= EPOCHS // 2 and score > best[0]: best = (score, v); torch.save({k: t.float().cpu() for k, t in net.state_dict().items()}, OUT)
print("saved", OUT, "validation", json.dumps(best[1])); print("DONE", flush=True)
