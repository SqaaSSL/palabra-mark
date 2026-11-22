
**Human speech, held-out speakers** (n = 65 calls; mark quality PESQ-WB mean 4.44, min 4.24)

| Line | verified by 1 s | 2 s | 3 s | 5 s | end | median time to verify | median z at 3 s |
|---|---|---|---|---|---|---|---|
| clean | 31% | 82% | 100% | 100% | 100% | 1.50 s | 10.1 |
| G.711 | 31% | 82% | 100% | 100% | 100% | 1.50 s | 10.1 |
| G.726-32 | 29% | 82% | 97% | 100% | 100% | 1.50 s | 9.8 |
| AMR-12.2 | 5% | 43% | 80% | 100% | 100% | 2.50 s | 8.1 |
| AMR-7.95 | 0% | 20% | 52% | 97% | 100% | 3.00 s | 7.1 |
| AMR-5.9 | 0% | 5% | 29% | 75% | 100% | 3.75 s | 6.5 |
| AMR-4.75 | 0% | 0% | 8% | 51% | 92% | 4.88 s | 5.6 |
| Opus-24 | 25% | 78% | 95% | 100% | 100% | 1.75 s | 9.4 |
| Opus-16 | 20% | 65% | 89% | 100% | 100% | 1.75 s | 8.9 |
| Opus-12 | 9% | 51% | 78% | 100% | 100% | 2.00 s | 8.3 |
| Opus-8 | 0% | 17% | 48% | 94% | 100% | 3.25 s | 6.8 |
| Opus-6 | 0% | 0% | 2% | 45% | 92% | 5.25 s | 5.4 |
| iLBC-15.2 | 5% | 46% | 88% | 100% | 100% | 2.25 s | 8.2 |
| G.723.1-6.3 | 0% | 8% | 37% | 88% | 100% | 3.50 s | 6.7 |
| AMR-12.2 > G.711 > Opus-16 | 0% | 25% | 57% | 98% | 100% | 2.75 s | 7.3 |
| G.711 > AMR-7.95 + noise 20dB | 0% | 15% | 55% | 95% | 100% | 3.00 s | 7.1 |

**Synthetic agent voices** (n = 14 calls; mark quality PESQ-WB mean 4.44, min 4.33)

| Line | verified by 1 s | 2 s | 3 s | 5 s | end | median time to verify | median z at 3 s |
|---|---|---|---|---|---|---|---|
| clean | 50% | 100% | 100% | 100% | 100% | 1.12 s | 11.5 |
| G.711 | 36% | 93% | 100% | 100% | 100% | 1.25 s | 11.5 |
| G.726-32 | 36% | 100% | 100% | 100% | 100% | 1.25 s | 11.4 |
| AMR-12.2 | 0% | 57% | 93% | 100% | 100% | 1.88 s | 9.3 |
| AMR-7.95 | 0% | 21% | 64% | 100% | 100% | 2.75 s | 7.9 |
| AMR-5.9 | 0% | 7% | 21% | 79% | 93% | 3.75 s | 6.4 |
| AMR-4.75 | 0% | 0% | 0% | 36% | 64% | 5.00 s | 5.7 |
| Opus-24 | 29% | 86% | 100% | 100% | 100% | 1.38 s | 10.7 |
| Opus-16 | 29% | 86% | 100% | 100% | 100% | 1.38 s | 10.0 |
| Opus-12 | 0% | 64% | 93% | 100% | 100% | 1.62 s | 9.3 |
| Opus-8 | 0% | 21% | 64% | 100% | 100% | 2.88 s | 7.3 |
| Opus-6 | 0% | 0% | 14% | 50% | 57% | 4.38 s | 5.8 |
| iLBC-15.2 | 0% | 86% | 100% | 100% | 100% | 1.50 s | 9.6 |
| G.723.1-6.3 | 0% | 14% | 57% | 86% | 100% | 3.00 s | 7.1 |
| AMR-12.2 > G.711 > Opus-16 | 0% | 36% | 71% | 100% | 100% | 2.38 s | 8.2 |
| G.711 > AMR-7.95 + noise 20dB | 0% | 14% | 50% | 100% | 100% | 3.12 s | 6.8 |

**False alarms.** 252,800 wrong-code trials (worst case over start offsets and all listening times from 1 s): highest z = 5.83, mean 3.14, s.d. 0.39; trials at or above 7: 0. Right code on unmarked audio (237 trials): highest z = 4.33. Trials at or above 6: 0; at or above 5.5: 6. Guaranteed bound on the false-alarm probability per wrong code at z = 7: 4650 looks x exp(-z^2/2) = 1.1e-07.

human: share verified within 3 s at pass mark 6 instead of 7: AMR-12.2 97%, AMR-4.75 34%, Opus-12 97%, Opus-6 28%, G.723.1-6.3 75%

agent: share verified within 3 s at pass mark 6 instead of 7: AMR-12.2 100%, AMR-4.75 29%, Opus-12 100%, Opus-6 43%, G.723.1-6.3 71%

**First proof of concept versus final engine** (human speech; share verified within 3 s / 5 s)

| Line | first PoC | final engine |
|---|---|---|
| G.711 | 17% / 54% | 100% / 100% |
| AMR-12.2 | 2% / 6% | 80% / 100% |
| AMR-4.75 | 0% / 0% | 8% / 51% |
| Opus-12 | 0% / 9% | 78% / 100% |
| G.723.1-6.3 | 0% / 0% | 37% / 88% |

PESQ-WB of the mark: first PoC 4.62, final 4.44. SNR of the final mark: 12.5 dB.