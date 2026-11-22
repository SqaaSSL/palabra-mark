"""Tap at the trunk. The agent side (LiveKit) speaks a marked greeting into a real phone call; the business side is
Twilio, which streams the audio it receives straight to the detector (Media Streams: raw 20 ms frames, no playback
buffer in between). Writes rec/manifest_rev.json.

  .venv/bin/python phone_batch_rev.py --public https://<tunnel>
"""
import argparse, asyncio, glob, json, os, sys, time
import aiohttp, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "engine"))
from palabra_mark import embed, load, save, FS
E = dict(l.strip().split("=", 1) for l in open(os.path.join(HERE, "..", ".env")) if "=" in l)
ap = argparse.ArgumentParser(); ap.add_argument("--public", required=True); ap.add_argument("--palabra", default="http://localhost:8790")
ap.add_argument("--limit", type=int, default=0); a = ap.parse_args()
AGENT, BUSINESS = E["LIVEKIT_NUMBER"], E["TWILIO_NUMBER"]                      # who speaks, who listens
TW = f"https://api.twilio.com/2010-04-01/Accounts/{E['TWILIO_ACCOUNT_SID']}/Calls"
BA = aiohttp.BasicAuth(E["TWILIO_API_KEY"], E["TWILIO_API_SECRET"])
TERMINAL = ("call.verified", "call.unverified", "call.unregistered")

def plan():
    agents = sorted(glob.glob(os.path.join(HERE, "..", "poc", "voices", "*")))
    sp = sorted(glob.glob(os.path.join(HERE, "..", "research", "data", "LibriSpeech", "dev-clean-2", "*")))[1::2]
    humans = [p for d in sp for p in sorted(f for f in glob.glob(d + "/*/*.flac") if os.path.getsize(f) > 8.5 * 22000)[:2]][:20]
    return [("marked", "agent", p) for p in agents] + [("marked", "human", p) for p in humans] + [("unmarked", "agent", p) for p in agents[:4]]

async def main():
    out = []; os.makedirs(os.path.join(HERE, "out"), exist_ok=True); P = plan()[: a.limit or None]
    async with aiohttp.ClientSession() as s:
        q = asyncio.Queue(); ev = await s.get(a.palabra + "/v1/events", timeout=aiohttp.ClientTimeout(total=None))
        async def pump():
            async for line in ev.content:
                if line.startswith(b"data"):
                    e = json.loads(line[6:])
                    if e["type"] in TERMINAL and e.get("via") == "twilio": q.put_nowait(e)
        asyncio.create_task(pump())
        for i, (kind, src, path) in enumerate(P):
            x = load(path)[: 8 * FS]; x = x / (np.abs(x).max() + 1e-9) * 0.7
            r = await (await s.post(a.palabra + "/v1/calls", json=dict(caller=AGENT, callee=BUSINESS, speaks_for=dict(name="Test", verified_by="Test", method="test", assurance="test"), purpose="test"))).json()
            if kind == "marked": x, _ = embed(x, bytes.fromhex(r["code"]), start=0)
            save(os.path.join(HERE, "out", "next.wav"), x)
            while not q.empty(): q.get_nowait()
            wss = a.public.replace("https", "wss") + "/v1/twilio"
            twiml = (f'<Response><Start><Stream url="{wss}" track="inbound_track"><Parameter name="caller" value="{AGENT}"/>'
                     f'<Parameter name="callee" value="{BUSINESS}"/></Stream></Start><Pause length="{int(len(x) / FS) + 5}"/></Response>')
            j = await (await s.post(TW + ".json", auth=BA, data=dict(To=AGENT, From=BUSINESS, Twiml=twiml))).json()
            t0 = time.time(); end = None; status = None
            while time.time() - t0 < 60:
                try:
                    e = await asyncio.wait_for(q.get(), 2)
                    end = e
                except asyncio.TimeoutError: pass
                status = (await (await s.get(f"{TW}/{j['sid']}.json", auth=BA)).json()).get("status")
                if status in ("completed", "failed", "busy", "no-answer", "canceled"):
                    if end is None:
                        try: end = await asyncio.wait_for(q.get(), 5)
                        except asyncio.TimeoutError: pass
                    break
            out.append(dict(i=i, kind=kind, src=src, voice=os.path.basename(path), secs=len(x) / FS, call_id=r["call_id"], code=r["code"], twilio=status, event=end))
            e = end or {}; print(i, kind, src, os.path.basename(path)[:18], status, e.get("type"), e.get("score"), e.get("heard"), flush=True)
            json.dump(out, open(os.path.join(HERE, "rec", "manifest_rev.json"), "w"))
asyncio.run(main())
