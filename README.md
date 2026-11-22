# Palabra Mark

A keyed, zero-bit audio mark that binds an AI agent's phone call to the intent it registered before dialling.
The receiver looks the call up, gets the code that call should carry, and checks whether the speech carries it.
The mark survives phone codecs (G.711, AMR, AMR-WB, EVS, Opus and others) and is verified in one to three seconds of speech.

The paper is in [`paper/palabra-mark-latex.pdf`](paper/palabra-mark-latex.pdf).

| Path | Contents |
|---|---|
| `engine/` | The mark, the whole-file and streaming detectors, the phone-line bridge and a command line. Start here. |
| `research/` | One script per experiment in the paper, and the result files behind every table and figure |
| `demo/` | A verification service with a live dashboard, a LiveKit tap and a Twilio caller, used for the live calls |
| `poc/` | The first proof of concept, kept for the comparison in Section 6.4 of the paper, and the synthetic agent greetings |
| `paper/` | Source of the paper, figures and audio examples |

## Quick start

Needs Python 3.9 or later, NumPy, SciPy and `ffmpeg` on the path.

    export PYTHONPATH=engine
    python -m palabra_mark mark in.wav marked.wav --secret S --caller +999555000427 --callee +999555000010 --slot 2026-11-21T09:14
    python -m palabra_mark bridge marked.wav phone.wav --line G.711 --line Opus-16
    python -m palabra_mark verify phone.wav --secret S --caller +999555000427 --callee +999555000010 --slot 2026-11-21T09:14

To reproduce the paper, see [`research/README.md`](research/README.md).

## Licence

The code is under the MIT licence (see `LICENSE`). The 3GPP EVS reference codec that `research/setup_codecs.sh` downloads is not part of this repository and has its own terms.
