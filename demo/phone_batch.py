"""A batch of real phone calls (Twilio -> phone network -> LiveKit number -> tap). Writes rec/manifest.json.
Run the server with PALABRA_RECORD=rec so the received audio is kept.

  .venv/bin/python phone_batch.py --public https://<tunnel>
"""
import argparse, asyncio, glob, json, os, secrets, sys, time
import aiohttp, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "engine"))
from palabra_mark import embed, load, save, FS
E = dict(l.strip().split("=", 1) for l in open(os.path.join(HERE, "..", ".env")) if "=" in l)
ap = argparse.ArgumentParser(); ap.add_argument("--public", required=True); ap.add_argument("--palabra", default="http://localhost:8790")
ap.add_argument("--limit", type=int, default=0); a = ap.parse_args()
CALLER, CALLEE = E["TWILIO_NUMBER"], E["LIVEKIT_NUMBER"]
TW = f"https://api.twilio.com/2010-04-01/Accounts/{E['TWILIO_ACCOUNT_SID']}/Calls"
AUTH = {"Authorization": aiohttp.encode_basic_auth(E["TWILIO_API_KEY"], E["TWILIO_API_SECRET"])} if hasattr(aiohttp, "encode_basic_auth") else None
BA = None if AUTH else aiohttp.BasicAuth(E["TWILIO_API_KEY"], E["TWILIO_API_SECRET"])
TERMINAL = ("call.verified", "call.unverified", "call.unregistered")

def plan():
    agents = sorted(glob.glob(os.path.join(HERE, "..", "poc", "voices", "*")))
    sp = sorted(glob.glob(os.path.join(HERE, "..", "research", "data", "LibriSpeech", "dev-clean-2", "*")))[1::2]   # held-out speakers
    humans = [p for d in sp for p in sorted(f for f in glob.glob(d + "/*/*.flac") if os.path.getsize(f) > 8.5 * 22000)[:2]][:20]
    P = [("marked", "agent", p) for p in agents] + [("cross", "agent", p) for p in agents[:4]] + [("replay", "agent", p) for p in agents[4:7]]
    P += [("marked", "human", p) for p in humans] + [("marked", "agent", p) for p in agents] + [("unmarked", "agent", p) for p in agents[:4]] + [("unmarked", "human", p) for p in humans[:4]]
    return P

async def reg(s, caller, callee):
    return await (await s.post(a.palabra + "/v1/calls", json=dict(caller=caller, callee=callee, speaks_for=dict(name="Test", verified_by="Test", method="test", assurance="test"), purpose="test"))).json()

async def dial(s, q, name):
    while not q.empty(): q.get_nowait()
    twiml = f'<Response><Pause length="1"/><Play>{a.public}/audio/{name}</Play><Pause length="2"/></Response>'
    j = await (await s.post(TW + ".json", headers=AUTH, auth=BA, data=dict(To=CALLEE, From=CALLER, Twiml=twiml))).json()
    t0 = time.time(); end = None
    while time.time() - t0 < 60:
        try:
            e = await asyncio.wait_for(q.get(), 2)
            if e["type"] in TERMINAL: end = e
        except asyncio.TimeoutError: pass
        c = await (await s.get(f"{TW}/{j['sid']}.json", headers=AUTH, auth=BA)).json()
        if c.get("status") in ("completed", "failed", "busy", "no-answer", "canceled"):
            if end is None:
                try:
                    while True:
                        e = await asyncio.wait_for(q.get(), 6)
                        if e["type"] in TERMINAL: end = e; break
                except asyncio.TimeoutError: pass
            return c.get("status"), end
    return "timeout", end

async def main():
    out = []; os.makedirs(os.path.join(HERE, "out"), exist_ok=True); os.makedirs(os.path.join(HERE, "rec"), exist_ok=True)
    P = plan()[: a.limit or None]
    async with aiohttp.ClientSession() as s:
        q = asyncio.Queue(); ev = await s.get(a.palabra + "/v1/events", timeout=aiohttp.ClientTimeout(total=None))
        async def pump():
            async for line in ev.content:
                if line.startswith(b"data"):
                    e = json.loads(line[6:])
                    if e["type"] in TERMINAL: q.put_nowait(e)
        asyncio.create_task(pump())
        for i, (kind, src, path) in enumerate(P):
            x = load(path)[: 8 * FS]; x = x / (np.abs(x).max() + 1e-9) * 0.7
            r = await reg(s, CALLER, CALLEE); code = r["code"]
            if kind in ("marked", "replay"): x, _ = embed(x, bytes.fromhex(code), start=0)
            if kind == "cross":                                       # a valid mark, but made for another caller's call
                o = await reg(s, "+999555000111", CALLEE); x, _ = embed(x, bytes.fromhex(o["code"]), start=0)
            name = secrets.token_hex(8) + ".wav"; save(os.path.join(HERE, "out", name), x)
            st, end = await dial(s, q, name)
            rec = dict(i=i, kind=kind, src=src, voice=os.path.basename(path), secs=len(x) / FS, call_id=r["call_id"], code=code, twilio=st, event=end)
            out.append(rec)
            if kind == "replay":                                      # the same recording, played a second time
                st, end2 = await dial(s, q, name)
                out.append(dict(rec, kind="replay-2nd", twilio=st, event=end2))
            for o_ in out[-2 if kind == "replay" else -1:]:
                e = o_["event"] or {}; print(o_["i"], o_["kind"], o_["src"], o_["voice"][:18], o_["twilio"], e.get("type"), e.get("score"), e.get("heard"), flush=True)
            json.dump(out, open(os.path.join(HERE, "rec", "manifest.json"), "w"))
asyncio.run(main())
