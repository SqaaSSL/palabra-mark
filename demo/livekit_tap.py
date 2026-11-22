"""LiveKit worker: taps the caller's audio on a call and copies it to the Palabra demo service.

The call itself is untouched; this only reads the caller's track.
Phone calls to the project's number reach it through the SIP dispatch rule in dispatch.json (agent "palabra-tap").

Needs LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, from the environment or a .env file one or two folders up.
Run:   .venv/bin/python livekit_tap.py dev
"""
import asyncio, logging, os
import aiohttp
from livekit import rtc
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli

HERE = os.path.dirname(os.path.abspath(__file__))
for env in (os.path.join(HERE, "..", ".env"), os.path.join(HERE, "..", "..", ".env")):          # keys may also come from the environment
    if os.path.exists(env):
        for line in open(env):
            if "=" in line and line.startswith("LIVEKIT_"): os.environ.setdefault(*line.strip().split("=", 1))
PALABRA = os.environ.get("PALABRA_URL", "ws://localhost:8790")
log = logging.getLogger("palabra-tap")

async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    # LiveKit keeps a phone call ringing until someone in the room publishes audio, so publish silence to answer it.
    # If out/next.wav exists, this side is the calling agent in the test: it speaks that (marked) greeting once.
    src = rtc.AudioSource(16000, 1)
    await ctx.room.local_participant.publish_track(rtc.LocalAudioTrack.create_audio_track("agent", src),
                                                   rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))
    say = asyncio.Queue()
    async def speak():
        quiet = rtc.AudioFrame(bytes(640), 16000, 1, 320)
        while True: await src.capture_frame(quiet if say.empty() else say.get_nowait())
    keep = asyncio.create_task(speak()); ctx.add_shutdown_callback(lambda: asyncio.sleep(0, keep.cancel()))
    caller = await ctx.wait_for_participant()
    a = caller.attributes                                   # LiveKit SIP sets sip.*; the test caller sets caller/callee
    params = dict(caller=a.get("sip.phoneNumber") or a.get("caller", ""),
                  callee=a.get("sip.trunkPhoneNumber") or a.get("callee", ""), rate="8000")
    nxt = os.path.join(HERE, "out", "next.wav")
    if os.path.exists(nxt):
        import wave
        w = wave.open(nxt); pcm = w.readframes(w.getnframes()); w.close(); os.remove(nxt)
        async def greet():
            await asyncio.sleep(1.5)
            for k in range(0, len(pcm) - 639, 640): say.put_nowait(rtc.AudioFrame(pcm[k:k + 640], 16000, 1, 320))
        asyncio.create_task(greet())
    log.info("call in %s: %s -> %s (%s)", ctx.room.name, params["caller"], params["callee"], dict(a))
    started = False; tasks = []

    def gone(participant):                                  # the caller hung up: close the tap so Palabra reports the outcome
        if participant.identity == caller.identity:
            for t in tasks: t.cancel()
            ctx.shutdown(reason="caller left")
    ctx.room.on("participant_disconnected", gone)

    async def tap(track: rtc.Track):
        n = 0
        try:
          async with aiohttp.ClientSession() as s, s.ws_connect(PALABRA + "/v1/listen", params=params) as ws:
            async for ev in rtc.AudioStream(track, sample_rate=8000, num_channels=1, frame_size_ms=20):
                await ws.send_bytes(bytes(ev.frame.data)); n += ev.frame.samples_per_channel
        except asyncio.CancelledError: pass
        log.info("tap closed after %.1f s of audio", n / 8000)

    def start(track, participant):
        nonlocal started
        if not started and participant.identity == caller.identity and track.kind == rtc.TrackKind.KIND_AUDIO:
            started = True; tasks.append(asyncio.create_task(tap(track)))

    ctx.room.on("track_subscribed", lambda track, pub, participant: start(track, participant))
    for pub in caller.track_publications.values():          # the track may already be there
        if pub.track: start(pub.track, caller)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="palabra-tap"))
