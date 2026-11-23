<p align="center"><a href="https://palabra.ae"><img src="assets/palabra.svg" alt="Palabra Mark" width="100%"></a></p>

<p align="center">
  <a href="https://palabra.ae">Website</a> ·
  <a href="https://palabra.ae/paper/">Paper (web)</a> ·
  <a href="paper/palabra-mark-latex.pdf">Paper (PDF)</a> ·
  <a href="https://doi.org/10.5281/zenodo.24469329">DOI</a> ·
  <a href="https://palabra.ae/showcase/">Live demo</a> ·
  <a href="https://palabra.ae/developers/">API</a>
</p>

# Palabra Mark

A keyed, zero-bit audio mark that binds an AI agent's phone call to the intent it registered before dialling.

An AI agent announces its call (who it speaks for, and why), then speaks with a mark in its voice that nobody hears.
The business that answers looks the call up, gets the code that call should carry, and checks whether the speech carries it.
The mark survives phone codecs (G.711, AMR, AMR-WB, EVS, Opus and others), is good for one call only, and is verified
in about one to three seconds of speech.

This repository holds the engine, every experiment behind the paper, the trained detectors and the paper itself.
The hosted service is at [palabra.ae](https://palabra.ae).

## Results in short

| | |
|---|---|
| Held-out speech over 21 phone lines, verified by 2 / 3 / 5 s | 30 / 57 / 88% with the analytic detector; 70 / 92 / 99.6% with the small learned detector |
| Wrong codes accepted | 0 in 331,800 trials per configuration; the bound is about 1 in a million |
| Recorded audio of 104 real calls | 82 of 82 marked calls verified, by both detectors |
| 18 new live calls with the deployed network | 14 of 14 marked calls verified, in 0.8 to 1.3 s; 0 of 4 unmarked calls |

Sources: Tables 14 to 16 and Section 6.13 of the paper; the result files are in [`research/results/`](research/results).

## What is here

| Path | Contents |
|---|---|
| [`engine/`](engine) | The mark, the whole-file and streaming detectors, the phone-line bridge and a command line. Start here. |
| [`research/`](research) | One script per experiment in the paper, the result files behind every table and figure, and the trained detectors |
| [`demo/`](demo) | A verification service with a live dashboard, a LiveKit tap and a Twilio caller, used for the live calls |
| [`poc/`](poc) | The first proof of concept, kept for the comparison in Section 6.4 of the paper, and the synthetic agent greetings |
| [`paper/`](paper) | Source of the paper, figures and audio examples |

## Quick start

Needs Python 3.9 or later, NumPy, SciPy and `ffmpeg` on the path.

    export PYTHONPATH=engine
    python -m palabra_mark mark in.wav marked.wav --secret S --caller +999555000427 --callee +999555000010 --slot 2026-11-21T09:14
    python -m palabra_mark bridge marked.wav phone.wav --line G.711 --line Opus-16
    python -m palabra_mark verify phone.wav --secret S --caller +999555000427 --callee +999555000010 --slot 2026-11-21T09:14

To reproduce the paper, see [`research/README.md`](research/README.md).

## Trained detectors

The mark needs no neural network: the analytic detector in `engine/` is a few hundred lines of signal processing.
The learned detectors read the same mark faster. Each one outputs votes for the pattern; none of them ever sees a call's code.
All are PyTorch checkpoints, small enough to live in the repository.

| Model | File | Weights | Use |
|---|---|---|---|
| VoteNet3 small (`ch=24 blocks=4 look=4`) | [`votenet3_c24.pt`](research/results/votenet3_c24.pt) | 59,066 | Streaming and causal. The one in production at palabra.ae. |
| VoteNet3 medium (`48 6 4`) | [`votenet3_c48.pt`](research/results/votenet3_c48.pt) | 317,426 | Streaming; the two-pass results in Table 14 |
| VoteNet3 medium, look-ahead 0 and 8 | [`votenet3_c48_l0.pt`](research/results/votenet3_c48_l0.pt), [`votenet3_c48_l8.pt`](research/results/votenet3_c48_l8.pt) | 317,426 | The look-ahead comparison in Table 15 |
| VoteNet3 large (`96 8 4`) | [`votenet3_c96.pt`](research/results/votenet3_c96.pt) | 1,596,770 | Streaming; the upper end of the size comparison |
| VoteNet | [`votenet.pt`](research/results/votenet.pt) | | The first learned detector, whole recordings only (Table 6) |
| VoteNet2 | [`votenet2.pt`](research/results/votenet2.pt) | | A deeper whole-recording detector, not in the paper |

The architectures are in [`research/ml_model.py`](research/ml_model.py). To run a streaming detector on audio:

    from ml_stream import load_net, learned_rows, run      # in research/, with engine/ on PYTHONPATH
    net = load_net("results/votenet3_c24.pt")
    score, verified_at, heard = run(code, learned_rows(samples, net, fs=8000))

Each `.pt` file has a `.log` next to it with its training and scoring record.

### Training data

No audio is published here, and none is needed: the training sets are built from public speech by the scripts.

- **Speech.** [LibriSpeech](https://www.openslr.org/12) (CC BY 4.0): the 251 speakers of `train-clean-100` and the 28 of `train-clean-5`.
  None of them is in the tuning or held-out sets, which use `dev-clean-2`.
- **Examples.** Each recording is marked with a random code and sent through simulated phone lines: narrowband and wideband
  codecs, in chains of up to three. This gives 72,843 training examples and 7,044 validation examples from 21 speakers.
- **Targets.** The votes the mark was built from. The code itself is never an input.
- **How to rebuild.** `ml_feat.py`, `ml_data3.py`, then `ml_train3.py`; see [`research/README.md`](research/README.md). The built set is 2.3 GB, so it is not in the repository.
- **Not used for training.** The recordings of real and live calls. They are test material only and are not published; their scores are in `research/results/`.

### Limits

The detectors were trained on English read speech; other languages have not been measured. They detect this mark and nothing else.
A detector cannot make a mark pass: verification needs the code of the call, which only the registry gives out.

## Citing

The paper is archived on Zenodo: [doi:10.5281/zenodo.24469329](https://doi.org/10.5281/zenodo.24469329).

    @misc{palabramark2026,
      title  = {Palabra Mark: binding an AI agent's phone call to its registered intent with a keyed, zero-bit audio mark},
      author = {Cohnen de la C\'amara, Ernesto and Novella Fletcher, Francisco and \'Avila G\'omez, Jos\'e Miguel and Tom\'as Ferrer, Carlos},
      year   = {2026},
      publisher = {Zenodo},
      doi    = {10.5281/zenodo.24469329},
      url    = {https://doi.org/10.5281/zenodo.24469329},
      note   = {https://palabra.ae/paper/}
    }

## Licence

The code and the trained detectors are under the MIT licence (see `LICENSE`). The 3GPP EVS reference codec that
`research/setup_codecs.sh` downloads is not part of this repository and has its own terms.

Palabra is made by [SqaaS](https://sqaas.io) (Squad as a Service, S.L.).
