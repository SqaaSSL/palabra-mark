"""Plays one call into the demo service, in real time, without a phone.

  simulate.py                                   a registered, marked call over a mobile line
  simulate.py --line "AMR-12.2,G.711,Opus-16"   a harder line
  simulate.py --impostor                        registered number, but the audio carries no mark (spoofed caller ID)
  simulate.py --unregistered                    an ordinary call nobody registered
"""
import argparse, asyncio, os, sys
import numpy as np
from aiohttp import ClientSession
from scipy.signal import resample_poly

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))
from palabra_mark import embed, load, FS
from palabra_mark.channels import bridge

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://localhost:8790")
ap.add_argument("--voice", default=os.path.join(HERE, "..", "poc", "voices", "el_sarah.mp3"))
ap.add_argument("--line", default="AMR-12.2")
ap.add_argument("--caller", default="+34 612 000 427"); ap.add_argument("--callee", default="+34 900 000 010")
ap.add_argument("--wait", type=float, default=1.5, help="seconds of line noise before the greeting")
ap.add_argument("--impostor", action="store_true"); ap.add_argument("--unregistered", action="store_true")
ap.add_argument("--fast", action="store_true", help="do not pace the audio in real time")
a = ap.parse_args()

async def main():
    x = load(a.voice); x = x / (np.abs(x).max() + 1e-9) * 0.7
    async with ClientSession() as s:
        if not a.unregistered:
            r = await (await s.post(a.url + "/v1/calls", json=dict(caller=a.caller, callee=a.callee,
                speaks_for=dict(name="Lucía Ortega", verified_by="Banco Ejemplo", method="app sign-in", assurance="high"),
                purpose="Confirm a card delivery slot", data=dict(reference="DLV-48213", options=["Tue 10-12", "Wed 16-18"])))).json()
            print("registered", r["call_id"])
            if not a.impostor: x, _ = embed(x, bytes.fromhex(r["code"]), start=0)   # the greeting is marked before it is played
        pre = np.random.default_rng(1).standard_normal(int(a.wait * FS)) * 1e-3
        y = resample_poly(bridge(np.concatenate([pre, x]), [n for n in a.line.split(",") if n]), 1, 2)
        pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
        async with s.ws_connect(a.url.replace("http", "ws", 1) + "/v1/listen", params=dict(caller=a.caller, callee=a.callee, rate="8000")) as ws:
            for k in range(0, len(pcm), 160):                                         # 20 ms frames, as a phone trunk sends them
                await ws.send_bytes(pcm[k:k + 160].tobytes())
                if not a.fast: await asyncio.sleep(0.02)
        print(f"sent {len(pcm)/8000:.1f} s over {a.line}")

asyncio.run(main())
