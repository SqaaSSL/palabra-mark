"""A real phone call: Twilio dials the LiveKit number and plays a marked greeting over the phone network.

  .venv/bin/python phone_call.py --public https://<tunnel>      [--impostor] [--voice file]

--public is the public address of the demo service (Twilio must fetch the audio), e.g. from
  cloudflared tunnel --url http://localhost:8790
"""
import argparse, asyncio, os, secrets, sys
import aiohttp, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))
from palabra_mark import embed, load, save
E = dict(l.strip().split("=", 1) for l in open(os.path.join(HERE, "..", ".env")) if "=" in l)

ap = argparse.ArgumentParser()
ap.add_argument("--public", required=True); ap.add_argument("--palabra", default="http://localhost:8790")
ap.add_argument("--voice", default=os.path.join(HERE, "..", "poc", "voices", "el_sarah.mp3"))
ap.add_argument("--impostor", action="store_true"); ap.add_argument("--pause", type=int, default=1)
a = ap.parse_args()

async def main():
    caller, callee = E["TWILIO_NUMBER"], E["LIVEKIT_NUMBER"]
    x = load(a.voice); x = x / (np.abs(x).max() + 1e-9) * 0.7
    async with aiohttp.ClientSession() as s:
        r = await (await s.post(a.palabra + "/v1/calls", json=dict(caller=caller, callee=callee,
            speaks_for=dict(name="Lucía Ortega", verified_by="Banco Ejemplo", method="app sign-in", assurance="high"),
            purpose="Confirm a card delivery slot", data=dict(reference="DLV-48213", options=["Tue 10-12", "Wed 16-18"])))).json()
        if not a.impostor: x, _ = embed(x, bytes.fromhex(r["code"]), start=0)
        name = secrets.token_hex(8) + ".wav"; os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
        save(os.path.join(HERE, "out", name), x)
        twiml = f'<Response><Pause length="{a.pause}"/><Play>{a.public}/audio/{name}</Play><Pause length="2"/></Response>'
        t = await s.post(f"https://api.twilio.com/2010-04-01/Accounts/{E['TWILIO_ACCOUNT_SID']}/Calls.json",
                         auth=aiohttp.BasicAuth(E["TWILIO_API_KEY"], E["TWILIO_API_SECRET"]),
                         data=dict(To=callee, From=caller, Twiml=twiml))
        j = await t.json(); print(r["call_id"], t.status, j.get("sid"), j.get("status"), j.get("message", ""))
        for _ in range(15):
            await asyncio.sleep(2)
            c = await (await s.get(f"https://api.twilio.com/2010-04-01/Accounts/{E['TWILIO_ACCOUNT_SID']}/Calls/{j['sid']}.json",
                                   auth=aiohttp.BasicAuth(E["TWILIO_API_KEY"], E["TWILIO_API_SECRET"]))).json()
            if c.get("status") in ("completed", "failed", "busy", "no-answer", "canceled"): break
        print("twilio:", c.get("status"), c.get("duration"), "s")

asyncio.run(main())
