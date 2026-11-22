"""Can a mark made for one call pass as another? Plays three attacks into the local demo service.

  ../research/.venv/bin/python test_cross.py
"""
import asyncio, json, os, sys
import numpy as np
from aiohttp import ClientSession
from scipy.signal import resample_poly
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "engine"))
from palabra_mark import embed, load, FS
from palabra_mark.channels import bridge

URL, BANK, ALICE, MALLORY = "http://localhost:8790", "+999555000010", "+999555000427", "+999555000111"
LINE = ["AMR-12.2"]

async def register(s, caller, callee):
    return await (await s.post(URL + "/v1/calls", json=dict(caller=caller, callee=callee, speaks_for=dict(name=caller), purpose="test"))).json()

async def play(s, x, caller, callee):
    """Send audio claiming to be caller -> callee; return the final event for that session."""
    y = resample_poly(bridge(np.concatenate([np.zeros(FS), x]), LINE), 1, 2); pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    ev = await s.get(URL + "/v1/events"); out = None
    async with s.ws_connect(URL.replace("http", "ws") + "/v1/listen", params=dict(caller=caller, callee=callee, rate="8000")) as ws:
        for k in range(0, len(pcm), 160): await ws.send_bytes(pcm[k:k + 160].tobytes())
    while True:
        line = await asyncio.wait_for(ev.content.readline(), 5)
        if line.startswith(b"data"):
            e = json.loads(line[6:])
            if e["type"] in ("call.verified", "call.unverified", "call.unregistered") and e["caller"] == "+" + caller.strip("+"): out = e; break
    ev.close(); return f'{out["type"]}  score {out.get("score")}'

async def main():
    voice = lambda n: (lambda v: v / (np.abs(v).max() + 1e-9) * 0.7)(load(os.path.join(HERE, "..", "poc", "voices", n)))
    async with ClientSession() as s:
        a = await register(s, ALICE, BANK); m = await register(s, MALLORY, BANK)
        xa, _ = embed(voice("el_sarah.mp3"), bytes.fromhex(a["code"]), start=0)
        xm, _ = embed(voice("el_brian.mp3"), bytes.fromhex(m["code"]), start=0)
        print("1. Mallory's own valid mark, caller ID spoofed as Alice :", await play(s, xm, ALICE, BANK))
        print("2. Alice's genuine call (control)                        :", await play(s, xa, ALICE, BANK))
        print("3. Recording of Alice's greeting replayed afterwards     :", await play(s, xa, ALICE, BANK))
        o = await register(s, ALICE, "+999555000333")
        xo, _ = embed(voice("el_sarah.mp3"), bytes.fromhex(o["code"]), start=0)
        await register(s, ALICE, BANK)
        print("4. Alice's mark for a different destination, sent to bank:", await play(s, xo, ALICE, BANK))
        print("5. Mallory's own call as herself (control)               :", await play(s, xm, MALLORY, BANK))
asyncio.run(main())
