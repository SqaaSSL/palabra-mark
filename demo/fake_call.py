"""A test caller over LiveKit (internet audio, no phone network): registers a call, marks a greeting, joins a room
and plays it. The tap agent is dispatched to the room exactly as for a phone call.

  .venv/bin/python fake_call.py [--impostor] [--voice file]
"""
import argparse, asyncio, os, secrets, sys
import aiohttp, numpy as np
from livekit import api, rtc

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))
from palabra_mark import embed, load, FS
for line in open(os.path.join(HERE, "..", ".env")):
    if "=" in line and line.startswith("LIVEKIT_"): os.environ.setdefault(*line.strip().split("=", 1))

ap = argparse.ArgumentParser()
ap.add_argument("--voice", default=os.path.join(HERE, "..", "poc", "voices", "el_sarah.mp3"))
ap.add_argument("--caller", default="+999555000427"); ap.add_argument("--callee", default="+999555000800")
ap.add_argument("--palabra", default="http://localhost:8790"); ap.add_argument("--impostor", action="store_true")
a = ap.parse_args()

async def main():
    x = load(a.voice); x = x / (np.abs(x).max() + 1e-9) * 0.7
    async with aiohttp.ClientSession() as s:
        r = await (await s.post(a.palabra + "/v1/calls", json=dict(caller=a.caller, callee=a.callee,
            speaks_for=dict(name="Lucía Ortega", verified_by="Banco Ejemplo", method="app sign-in", assurance="high"),
            purpose="Confirm a card delivery slot", data=dict(reference="DLV-48213", options=["Tue 10-12", "Wed 16-18"])))).json()
    if not a.impostor: x, _ = embed(x, bytes.fromhex(r["code"]), start=0)
    pcm = (np.clip(np.concatenate([np.zeros(FS), x, np.zeros(FS)]), -1, 1) * 32767).astype("<i2")
    room_name = "palabra-test-" + secrets.token_hex(3)
    lk = api.LiveKitAPI()
    await lk.agent_dispatch.create_dispatch(api.CreateAgentDispatchRequest(agent_name="palabra-tap", room=room_name))
    token = (api.AccessToken().with_identity("test-caller").with_attributes(dict(caller=a.caller, callee=a.callee))
             .with_grants(api.VideoGrants(room_join=True, room=room_name)).to_jwt())
    room = rtc.Room(); await room.connect(os.environ["LIVEKIT_URL"], token)
    src = rtc.AudioSource(FS, 1); track = rtc.LocalAudioTrack.create_audio_track("voice", src)
    await room.local_participant.publish_track(track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))
    for _ in range(100):                                                     # wait for the tap agent to join
        if room.remote_participants: break
        await asyncio.sleep(0.1)
    await asyncio.sleep(1.0)
    for k in range(0, len(pcm) - 319, 320):                                  # 20 ms frames; capture_frame paces itself
        await src.capture_frame(rtc.AudioFrame(pcm[k:k + 320].tobytes(), FS, 1, 320))
    await src.wait_for_playout(); await asyncio.sleep(0.5)
    await room.disconnect(); await lk.aclose()
    print("played", len(pcm) / FS, "s in", room_name, "as", r["call_id"])

asyncio.run(main())
