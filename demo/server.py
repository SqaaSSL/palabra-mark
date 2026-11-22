"""Palabra demo service.

  POST /v1/calls     the calling side registers a call before dialling        -> {call_id, code}
  WS   /v1/listen    the receiving side copies the call audio here (a tap)     (binary s16le mono frames)
  GET  /v1/events    live event stream for the dashboard (server-sent events)
  GET  /             the dashboard

Every event is also POSTed to PALABRA_WEBHOOK_URL, signed, so the customer's own system decides what to do
(enrich the call, flag it, drop it). Palabra only reports.

Run:  ../research/.venv/bin/python server.py        (http://localhost:8790)
"""
import asyncio, base64, hashlib, hmac, json, os, secrets, sys, time
import numpy as np
from aiohttp import web, ClientSession, ClientTimeout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))
from palabra_mark import call_code, Config
from palabra_mark.stream import StreamDetector

HERE = os.path.dirname(os.path.abspath(__file__))
SECRET = os.environ.get("PALABRA_SECRET", "demo-secret").encode()            # derives the per-call codes
WEBHOOK_URL = os.environ.get("PALABRA_WEBHOOK_URL")                          # the customer's endpoint
WEBHOOK_KEY = os.environ.get("PALABRA_WEBHOOK_KEY", "demo-webhook-key").encode()
RECORD = os.environ.get("PALABRA_RECORD")                                    # folder to save received audio in (off by default)
LATE = float(os.environ.get("PALABRA_LATE", 0))                               # seconds of the mark the tap may have missed
TAU, LIKELY, TTL = 7.0, 4.5, 300                                             # pass mark; "something is there"; seconds a registration lives
REG, SUBS, RECENT = {}, set(), []

def norm(n): return "+" + "".join(c for c in str(n) if c.isdigit())

async def emit(app, ev):
    ev["at"] = time.time(); body = json.dumps(ev)
    RECENT.append(body); del RECENT[:-200]
    for q in list(SUBS): q.put_nowait(body)
    if WEBHOOK_URL:
        sig = hmac.new(WEBHOOK_KEY, body.encode(), hashlib.sha256).hexdigest()
        async def post():
            try: await app["http"].post(WEBHOOK_URL, data=body, headers={"Content-Type": "application/json", "Palabra-Signature": sig})
            except Exception as e: print("webhook failed:", e)
        asyncio.create_task(post())

async def register(req):
    """Body: {caller, callee, speaks_for: {...}, purpose, data: {...}}. Demo only: no authentication."""
    b = await req.json(); caller, callee = norm(b["caller"]), norm(b["callee"])
    cid = "call_" + secrets.token_hex(6)
    code = call_code(SECRET, caller, callee, cid)
    REG.setdefault((caller, callee), []).append(dict(id=cid, code=code, at=time.time(),
        payload=dict(speaks_for=b.get("speaks_for"), purpose=b.get("purpose"), data=b.get("data"))))
    await emit(req.app, dict(type="call.registered", call_id=cid, caller=caller, callee=callee))
    return web.json_response(dict(call_id=cid, code=code.hex()))

class Tap:
    """One call being listened to. Feed it audio with push(); it emits the events."""
    def __init__(self, app, caller, callee, fs, via="tap"):
        self.app, self.fs = app, fs; self.caller, self.callee = norm(caller), norm(callee)
        self.sid = "tap_" + secrets.token_hex(6); self.base = dict(session=self.sid, caller=self.caller, callee=self.callee, via=via)
        self.t = self.last = 0.0; self.likely = False; self.raw = bytearray()

    async def open(self):
        cands = [c for c in REG.get((self.caller, self.callee), []) if time.time() - c["at"] < TTL]
        self.dets = [(c, StreamDetector(c["code"], Config(), fs=self.fs, tau=TAU, late=LATE)) for c in cands]
        self.done = not self.dets
        if not cands: await emit(self.app, dict(type="call.unregistered", **self.base))   # an ordinary call: nothing to check
        else: await emit(self.app, dict(type="call.listening", call_id=cands[-1]["id"], **self.base))

    async def push(self, x):
        """x: float samples in [-1, 1]."""
        if RECORD: self.raw += (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
        if self.done: return
        self.t += len(x) / self.fs
        for c, d in self.dets: d.push(x)
        c, d = max(self.dets, key=lambda cd: cd[1].score); score = round(max(0.0, d.score), 2); t = round(self.t, 2)
        if d.state == "verified":
            self.done = True
            REG[(self.caller, self.callee)] = [r for r in REG.get((self.caller, self.callee), []) if r is not c]   # one-time: a recording cannot pass again
            await emit(self.app, dict(type="call.verified", call_id=c["id"], score=score, t=t, heard=d.scorer.heard, **c["payload"], **self.base))
        elif all(dd.state == "expired" for _, dd in self.dets):
            self.done = True
            await emit(self.app, dict(type="call.unverified", call_id=c["id"], score=score, t=t, reason="expired", **self.base))
        elif self.t - self.last >= 0.25:
            self.last = self.t
            if score >= LIKELY and not self.likely:
                self.likely = True; await emit(self.app, dict(type="call.likely", call_id=c["id"], score=score, t=t, **self.base))
            await emit(self.app, dict(type="call.score", call_id=c["id"], score=score, t=t, **self.base))

    async def close(self):
        if not self.done:                                                     # the caller hung up before we could tell
            c, d = max(self.dets, key=lambda cd: cd[1].score)
            await emit(self.app, dict(type="call.unverified", call_id=c["id"], score=round(max(0.0, d.score), 2), t=round(self.t, 2), reason="ended", **self.base))
        if RECORD and self.raw:                                               # keep what the tap heard, for offline study
            os.makedirs(RECORD, exist_ok=True); open(os.path.join(RECORD, f"{self.sid}_{self.fs}.s16"), "wb").write(self.raw)

async def listen(req):
    """Query: caller, callee, rate (8000 or 16000). Send 16-bit mono audio as it arrives; nothing comes back but events."""
    ws = web.WebSocketResponse(max_msg_size=1 << 20); await ws.prepare(req)
    tap = Tap(req.app, req.query["caller"], req.query["callee"], int(req.query.get("rate", 8000))); await tap.open()
    async for msg in ws:
        if msg.type == web.WSMsgType.BINARY: await tap.push(np.frombuffer(msg.data, dtype="<i2").astype(np.float64) / 32768)
    await tap.close(); return ws

_u = np.arange(256, dtype=np.int32) ^ 0xFF                                    # G.711 mu-law to linear
ULAW = (np.where(_u & 0x80, -1, 1) * ((((_u & 0x0F) << 3) + 0x84 << ((_u & 0x70) >> 4)) - 0x84) / 32768.0)

async def twilio(req):
    """Twilio Media Streams: the trunk hands over the caller's audio as it arrived, 20 ms of mu-law per message, with
    timestamps. Nothing has stretched or squeezed it for playback, and a lost packet shows up as a gap we can fill.
    TwiML: <Start><Stream url="wss://.../v1/twilio" track="inbound_track"><Parameter name="caller" value="+.."/>
           <Parameter name="callee" value="+.."/></Stream></Start>"""
    ws = web.WebSocketResponse(); await ws.prepare(req); tap = None; pos = 0
    async for msg in ws:
        if msg.type != web.WSMsgType.TEXT: continue
        m = json.loads(msg.data)
        if m["event"] == "start":
            p = m["start"].get("customParameters", {}); tap = Tap(req.app, p.get("caller", ""), p.get("callee", ""), 8000, via="twilio"); await tap.open()
        elif m["event"] == "media" and tap:
            x = ULAW[np.frombuffer(base64.b64decode(m["media"]["payload"]), dtype=np.uint8)]
            at = int(m["media"]["timestamp"]) * 8                             # where this audio belongs, in samples
            if 0 < at - pos < 8000 * 2: await tap.push(np.zeros(at - pos)); pos = at   # keep time true across lost packets
            await tap.push(x); pos += len(x)
        elif m["event"] == "stop": break
    if tap: await tap.close()
    return ws

async def events(req):
    resp = web.StreamResponse(headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache"})
    await resp.prepare(req); q = asyncio.Queue(); SUBS.add(q)
    try:
        while True:
            try: body = await asyncio.wait_for(q.get(), 15); await resp.write(f"data: {body}\n\n".encode())
            except asyncio.TimeoutError: await resp.write(b": keep-alive\n\n")
    except (ConnectionResetError, asyncio.CancelledError): pass
    finally: SUBS.discard(q)
    return resp

async def index(req): return web.FileResponse(os.path.join(HERE, "dashboard.html"))
async def config(req): return web.json_response(dict(tau=TAU, likely=LIKELY, webhook=bool(WEBHOOK_URL)))

async def http_ctx(app):
    app["http"] = ClientSession(timeout=ClientTimeout(total=5)); yield; await app["http"].close()

def make():
    app = web.Application(); app.cleanup_ctx.append(http_ctx)
    app.add_routes([web.get("/", index), web.get("/v1/config", config), web.post("/v1/calls", register),
                    web.get("/v1/listen", listen), web.get("/v1/twilio", twilio), web.get("/v1/events", events)])
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    app.router.add_static("/audio", os.path.join(HERE, "out"))             # marked greetings, fetched by the phone carrier
    return app

if __name__ == "__main__":
    web.run_app(make(), port=int(os.environ.get("PORT", 8790)))
