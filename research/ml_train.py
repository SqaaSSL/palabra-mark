import numpy as np, torch, time
from ml_model import VoteNet, zscore
torch.manual_seed(0); dev = "mps" if torch.backends.mps.is_available() else "cpu"
d = np.load("results/ml_train.npz"); n = len(d["S"]); idx = np.random.default_rng(0).permutation(n); va, tr = idx[:400], idx[400:]
S = torch.from_numpy(d["S"].astype(np.float32)); B = torch.from_numpy(d["B"].astype(np.float32)); T = torch.from_numpy(d["T"].astype(np.float32))
net = VoteNet().to(dev); opt = torch.optim.AdamW(net.parameters(), 2e-3, weight_decay=1e-4)
EPOCHS, BS = 14, 24; sched = torch.optim.lr_scheduler.OneCycleLR(opt, 3e-3, total_steps=EPOCHS * (len(tr) // BS))
def val():
    net.eval(); zs = []
    with torch.no_grad():
        for i in range(0, len(va), 50):
            j = va[i:i + 50]; zs.append(zscore(net(S[j].to(dev), B[j].to(dev)), T[j].to(dev)).cpu())
    net.train(); return torch.cat(zs)
zb = zscore(B[va], T[va]); print(f"params {sum(p.numel() for p in net.parameters()):,}; validation mean z after 6 s: analytic {zb.mean():.2f}")
t0 = time.time()
for ep in range(EPOCHS):
    perm = tr[np.random.default_rng(ep).permutation(len(tr))]; tot = 0
    for i in range(0, len(perm) - BS + 1, BS):
        j = perm[i:i + BS]; s, b, t = S[j].to(dev), B[j].to(dev), T[j].to(dev)
        r = np.random.randint(20, 94)                                   # train on prefixes too, so short listening times are covered
        loss = -zscore(net(s, b)[:, :r], t[:, :r]).div(r ** 0.5).mean(); opt.zero_grad(); loss.backward(); opt.step(); sched.step(); tot += loss.item()
    zv = val(); print(f"epoch {ep+1:2}  loss {tot/(len(perm)//BS):.4f}  validation mean z {zv.mean():.2f}  (low 10%: {zv.quantile(.1):.2f}; analytic {zb.quantile(.1):.2f})  {time.time()-t0:.0f}s", flush=True)
torch.save(net.state_dict(), "results/votenet.pt")
