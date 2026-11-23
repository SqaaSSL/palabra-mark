# Experiments

Every table and figure in the paper comes from one script here. Each script writes a JSON file to `results/`,
and those files are in the repository, so the tables can be checked without running anything.

## Set-up

    python3 -m venv .venv && .venv/bin/pip install numpy scipy matplotlib pesq torch audioseal
    mkdir -p data tmp && cd data
    curl -LO https://www.openslr.org/resources/31/dev-clean-2.tar.gz && tar xzf dev-clean-2.tar.gz      # held-out and tuning speakers
    curl -LO https://www.openslr.org/resources/31/train-clean-5.tar.gz && tar xzf train-clean-5.tar.gz  # learned detector only

Codecs:

- Most come from the local `ffmpeg`.
- AMR is encoded in a Docker container:
  `docker run -d --name palabra-codecs -v "$PWD/tmp":/w --entrypoint sleep linuxserver/ffmpeg infinity`
- AMR-WB and EVS are built from source by `sh setup_codecs.sh` (macOS or Linux; needs a C compiler and make).
  The EVS code is the 3GPP reference implementation, downloaded from 3gpp.org and not included here.

Run scripts from this folder with `.venv/bin/python <script>`.

## Which script makes which result

| Paper | Script | Result file |
|---|---|---|
| Figure 1 (the mark) | `fig_mark.py` | `../paper/figures/fig0_the_mark.png` |
| Tables 2, 3, 4; Sections 6.2, 6.3; Figures 2 to 4 | `eval_final.py`, then `analyze.py` | `final.json`, `tables.md` |
| Table 5 (AudioSeal) | `baseline_audioseal.py` | `audioseal.json` |
| Table 6 (learned detector) | `ml_data.py`, `ml_train.py`, `ml_eval.py` | `votenet.pt`, `ml_eval.json` |
| Table 7 (real call recordings) | `eval_calls.py` | `calls.json` |
| Table 8 (streaming detector) | `eval_stream.py` | `stream.json` |
| Table 9 and Section 6.9 (live calls) | `../demo/phone_batch.py`, `../demo/phone_batch_rev.py`, then `eval_live.py` | `live.json`, `live_rev.json` |
| Table 10 (marks made for other calls) | `../demo/test_cross.py` | printed |
| Table 11 (whole-call marking) | `eval_hijack.py` | `hijack.json` |
| Table 12 (AMR-WB and EVS) | `eval_wb.py` | `wideband.json` |
| Table 13 (learned detector on AMR-WB and EVS) | `ml_eval_wb.py` | `ml_eval_wb.json` |
| Tables 14 and 15 (streaming learned detector) | `ml_feat.py`, `ml_data3.py`, `ml_train3.py`, `ml_eval3_export.py`, `ml_eval3.py` | `votenet3_*.pt`, `ml_eval3_p1.json`, `ml_eval3_p2.json` |
| Table 16 (streaming learned detector on the live calls) | `ml_stream.py` | `live_learned.json` |
| Section 6.13, new live calls with the deployed network | `test/phone.ts` of the service (not in this repository) | `live_learned_calls.jsonl` |
| Not in the paper: streaming marker against the file embedder | `eval_marker.py` | `marker.json` |
| Not in the paper: second learned detector, trained on narrowband and wideband lines on a rented GPU | `ml_data2.py`, `ml_train2.py`, `ml_eval2.py` | `votenet2.pt`, `ml_eval2.json` |
| Section 7 and Figure 5 (design sweeps) | `sweep_design.py`, `sweep2.py`, `eval_gain.py`, `train_filter.py` | `sweep_design.json`, `sweep2.json`, `eval_gain.json`, `kernel.json` |

Tables 14 and 15: `ml_data3.py` also needs LibriSpeech `train-clean-100` in `data/`. Training ran on a rented GPU
(`ml_train3.py ch=24 blocks=4 look=4`, and `48 6` with `look=0`, `4`, `8`, and `96 8 4`). `ml_eval3_export.py` runs where the codecs are
and writes `ml_test3.npz` (105 MB, not in the repository); `ml_eval3.py` scores it, with `passes=1` or `passes=2`. In the result
files the networks are named `s3_c24`, `s3_c48_l0`, `s3_c48`, `s3_c48_l8` and `s3_c96`. The `.log` files are the training and scoring logs.

The call recordings for Table 7 come from the Harper Valley corpus and the NCSU Robocall Audio Dataset; `eval_calls.py`
says where it expects them. The recordings of the live calls are not published; their scores are in `live.json` and `live_rev.json`.
