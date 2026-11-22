# Palabra demo service

Shows a call being verified live: the score climbs as the caller talks, and the call details unlock when it passes.

```
../research/.venv/bin/python server.py          # dashboard at http://localhost:8790
../research/.venv/bin/python simulate.py        # a registered, marked call over a mobile line
../research/.venv/bin/python simulate.py --line "AMR-12.2,G.711,Opus-16"
../research/.venv/bin/python simulate.py --impostor       # right caller ID, no mark
../research/.venv/bin/python simulate.py --unregistered --caller "+34 600 111 222"
```

`simulate.py` needs ffmpeg and, for AMR lines, the `palabra-codecs` Docker container (see `engine/README.md`).

## How it fits together

1. The calling side registers the call: `POST /v1/calls` with caller, callee, who it speaks for and the purpose. It gets a one-time code and marks its greeting with it before playing it.
2. The receiving side copies the call audio to `WS /v1/listen?caller=..&callee=..&rate=8000` (16-bit mono frames). This is a side tap: the call is never delayed.
3. Palabra sends events. The customer decides what to do with them.

| Event | Meaning |
|---|---|
| `call.registered` | a call was announced |
| `call.listening` | audio is arriving for a registered call |
| `call.score` | current score, four times a second |
| `call.likely` | score passed 4.5: a hint only, wrong codes have reached 6 |
| `call.verified` | score passed 7; carries `speaks_for`, `purpose`, `data` |
| `call.unverified` | registered call, mark not found (`reason`: `expired` after 18 s, or `ended`) |
| `call.unregistered` | nothing registered for this caller and number: an ordinary call |

Set `PALABRA_WEBHOOK_URL` to receive every event as a POST. Each carries `Palabra-Signature`: HMAC-SHA256 of the body with `PALABRA_WEBHOOK_KEY`.

## Real phone calls

```
.venv/bin/python livekit_tap.py dev                      # the tap agent on the LiveKit project
cloudflared tunnel --url http://localhost:8790           # so the carrier can fetch the greeting
.venv/bin/python phone_call.py --public https://<tunnel> # Twilio dials the LiveKit number and plays a marked greeting
.venv/bin/python phone_call.py --public https://<tunnel> --impostor
.venv/bin/python fake_call.py                            # same, over LiveKit internet audio only (no carrier)
```

Keys are read from `../.env`. `.venv` here is Python 3.12 with `livekit-agents`; the engine and server use `../research/.venv`.
The tunnel exposes the whole demo service, which has no authentication: close it when done.

## Not done yet

- No authentication on `/v1/calls` or `/v1/listen`, and registrations live in memory. Demo only.
- Everything runs on one machine; nothing is hosted.
