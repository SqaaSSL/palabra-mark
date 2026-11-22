# Audio-mark proof of concept

Can a per-call pattern be hidden in a caller's speech, survive a phone line, and be checked by the receiver?

- `wm.py`: embeds and detects the mark (numpy + ffmpeg only)
- `channels.py`: simulated phone lines (real codecs through ffmpeg, narrowed to 300-3400 Hz)
- `run.py`: the experiment. `python3 run.py [audio files...]`
- `out/`: listen to `*_original.wav` against `*_marked.wav`, and both `*_after_phone.wav`

How it works: the receiver looks the call up by both numbers and the time, gets the code that call
should carry, and checks whether the audio leans the way that code says. The result is a z-score;
6 or more is treated as a pass (a fluke at roughly one in ten million).

First results (two synthetic voices, five codes each, mark strength +/-2 dB):

- 1.5 s of speech: not enough. No line passes reliably.
- 3 s: passes on clean lines for one voice, about half the time for the other.
- 5 s: passes on landline-grade and mid-rate codecs for both voices; fails on the harshest low-bitrate ones.
- Controls behave: 400 wrong codes and unmarked audio never scored above 4.6.

Not tested yet: AMR (the main mobile codec; not in this ffmpeg build), real carrier routes, human voices,
noisy rooms, and a proper listening test of how audible the mark is.
