# Palabra Mark engine

A keyed, zero-bit audio mark for phone speech. See `../paper/palabra-mark-latex.pdf` for the design and results.

Needs Python 3.9+, NumPy, SciPy and `ffmpeg` on the path.

    export PYTHONPATH=engine

    # mark a recording for one call
    python -m palabra_mark mark in.wav marked.wav --secret S --caller +999555000427 --callee +999555000010 --slot 2026-11-21T09:14

    # send it through phone codecs (AMR needs a Docker container, AMR-WB and EVS a one-off build: see research/README.md)
    python -m palabra_mark bridge marked.wav phone.wav --line AMR-12.2 --line G.711

    # check it on the receiving side; exit code 0 = verified
    python -m palabra_mark verify phone.wav --secret S --caller +999555000427 --callee +999555000010 --slot 2026-11-21T09:14

In code:

    from palabra_mark import embed, Detector, call_code, load
    code = call_code(secret, caller, callee, slot)
    marked, _ = embed(load("in.wav"), code)
    seconds, z = Detector(received_audio).curve(code)      # verified once z >= 7

## Marking a live voice

When there is no file to mark, for example with a realtime speech-to-speech model, put `StreamMarker` between the voice and the line:

    from palabra_mark import StreamMarker
    marker = StreamMarker(code, fs=24000)          # 8, 16, 24, 32 or 48 kHz
    for frame in voice:                            # float samples in [-1, 1], any frame size
        line.send(marker.push(frame))
    line.send(marker.flush())

It delays the audio by 80 ms and marks as well as `embed()` does. `StreamMarker(code, lookahead=False)` delays it by 24 ms and takes a little longer to verify.
Push silence while the voice pauses, so the mark keeps time with the call. Results: `research/eval_marker.py`.
