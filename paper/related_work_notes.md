# Palabra: related work and prior-art notes

Survey date: 2026-11-21.

## How to read the verification tags

Every item carries one tag saying how far I checked it.

- **[F]** I opened the full text (PDF) and read the relevant passages or tables.
- **[A]** I opened the abstract page, the official landing page, the RFC/draft page, or the project repository.
- **[S]** I confirmed the bibliographic details and the stated claim only from search-result excerpts. I did not open the source. Check before citing a number.
- **UNVERIFIED** I did not confirm it from any source in this survey. It is listed because the brief named it or because it is the standard citation.

Numbers are quoted only from [F] and [A] sources unless marked otherwise. Statements labelled "Inference" are mine, not the sources'.

---

## 1. Watermarking robust to speech codecs and telephony

### 1.1 Closest work: watermarks designed for phone calls

**CallShield** (Rabhi, Boshmaf, Alsabah, Chowdhury, Hefeeda, Khalil; QCRI/HBKU; arXiv 2601.09327, Jan 2026) [F]
- Idea: a causal neural watermark (AudioSeal-style generator/detector) on 8 kHz speech carries 1 bit per 40 ms frame. On top sit a sync preamble, BCH coding (128 message bits in 511-bit codewords, t=55), retransmission, and an HMAC-SHA256 challenge-response using a pairwise key shared offline between trusted contacts.
- Payload and time: multi-bit (64-bit nonce + 64-bit session id, 128-bit truncated MAC). Full authentication takes 63 s on average including up to three retries.
- Reported: above 99.2% authentication success on clean audio and above 95% under "common distortions"; bit accuracy about 91-92% at strength 0.6; PESQ above 4.2, STOI above 0.94 on clean speech. Trained and tested on Switchboard-1.
- Codecs: **none were run.** The distortion model is white noise, pink noise, echo, lowpass/highpass/bandpass filtering and ducking, plus simulated delay. AMR-NB and EVS are mentioned only in an argument that real codecs keep the midband. Bandpass filtering was their worst case (success below 70% at 20% coverage).
- Code: no release found in the paper.
- Relation to Palabra: same goal (in-band caller authentication at the audio layer) but multi-bit, pairwise keys, no registry, no AI-agent framing, a minute to complete, and no real codec evidence.

**Looney and Gaubitch, "Robust spread spectrum speech watermarking using linear prediction and deep spectral shaping"** (Pindrop; Interspeech 2024) [F]
- Idea: zero-bit spread spectrum in the log spectrum of 20 ms frames (63 elements of 50 Hz from 500 to 3650 Hz), aimed at flagging synthetic speech at call centres. Two additions: LPC-based shaping of the watermark sequence at the encoder, and a small neural decoder replacing the dot product.
- Reported: frame lengths of roughly 20-30 ms give the best robustness/perceptibility balance for speech. LPC shaping at equal narrowband PESQ cut EER from 8.2% to 5.9% in one noise condition. After downsampling to 8 kHz plus **Opus at 8 kbps**, single-frame EER was 37.2% (dot product), 35.0% and 30.0% (two neural decoders); aggregating 30 frames with the better decoder cut EER by 86% relative to the dot product. The Opus condition needed three times the embedding strength of the downsample-only condition.
- Also filed as a patent application, US 20250095662 [S], which describes routing an inbound call on the watermark detection score.
- Code: none found.
- Relation to Palabra: closest classical design to the current proof of concept (keyed log-spectral pattern, zero-bit, accumulation over frames, telephony target). It is not per-call keyed and has no registry.

**Pindrop blog, "Does watermarking protect against deepfake attacks?"** (Gaubitch, 20 Oct 2023) [A]
- States that for an imperceptible watermark (PESQ above 4) typical EER over telephony-style degradation is 15-30%, and that speech is harder to watermark than music because of narrow bandwidth and sparse spectrum. Vendor blog, not peer reviewed.

**Kazemi, Pérez-González, Akhaee, Behnia, "Data Hiding Robust to Mobile Communication Vocoders"** (IEEE Trans. Multimedia, 2016, DOI 10.1109/TMM.2016.2599149) [F]
- Idea: model the AMR voice channel as a linear filter plus a nonlinear scaling function, then design additive and multiplicative spread-spectrum embedding with M-ary biorthogonal codes for that channel.
- Payload: 8 kHz speech, 2500 samples per symbol, stated as 3.2 bps. Target symbol error 1e-3 with 8-ary symbols at a document-to-watermark ratio of 22.5 dB (multiplicative) and 24.5 dB (additive).
- Codecs: AMR 12.2 kbps as the main case; AMR 10.2, AMR 7.95 and GSM FR checked "with promising results". Imperceptibility assessed by A/B/X and PESQ.
- Code: none found.

### 1.2 Classical methods

| Method | Source | Core idea | Codec evidence | Tag |
|---|---|---|---|---|
| Patchwork (origin) | Bender, Gruhl, Morimoto, Lu, "Techniques for data hiding", IBM Systems Journal 35(3/4):313-336, 1996 | Keyed pairs of samples nudged in opposite directions; detect by the mean difference. Paper also covers echo hiding (about 16 bps), phase coding, spread spectrum | none for speech codecs | [S] |
| Modified patchwork | Yeo and Kim, IEEE Trans. Speech Audio Process., 2003, DOI 10.1109/TSA.2003.812145 | Patchwork statistics in the DCT (also DFT/DWT) domain | not checked | [S] |
| Robust patchwork | Natgunanathan, Xiang, Rong, Zhou, Guo, IEEE TASLP 20(8):2232-2239, 2012 | DCT frame pairs chosen by a selection criterion so the decoder needs no side information | not checked | [S] |
| audiowmark | S. Westerfeld, github.com/swesterfeld/audiowmark | Patchwork on FFT magnitudes of 1024-sample frames, keyed band selection (AES-128 key), 128-bit payload | README: usually survives MP3/OGG at 128 kbit/s and above; stronger setting suggested for 64 kbit/s. No speech codecs. GPLv3-or-later | [A] |
| Spread spectrum | Cox, Kilian, Leighton, Shamoon, IEEE Trans. Image Process. 6(12):1673-1687, 1997 | i.i.d. Gaussian sequence in perceptually significant spectral components | n/a | [S] |
| Spread spectrum for audio | Kirovski and Malvar, IEEE Trans. Signal Process., 2003 | Cited by Looney and Gaubitch as the music-oriented baseline | n/a | UNVERIFIED (seen only in a reference list) |
| Spread spectrum for speech | Cheng and Sorensen, ICASSP 2001 | Cited by Looney and Gaubitch as the filtered-BPSK speech baseline | n/a | UNVERIFIED (seen only in a reference list) |
| QIM / dither modulation | Chen and Wornell, IEEE Trans. Inf. Theory 47(4):1423-1443, 2001 | Quantize the host with one of several keyed quantizers | n/a | [S] |
| Echo hiding | Gruhl, Lu, Bender, Information Hiding 1996 (LNCS 1174) | Closely spaced synthetic echoes, cepstral detection | n/a | [S] |
| Pitch QIM with insertion/deletion codes | Coumou and Sharma, ICME 2006 (journal version IEEE TIFS 2008) | QIM of average pitch (step 10 Hz) over blocks of 5 analysis windows; concatenated code corrects insertions, deletions, substitutions | Uncoded about 8 bps with overall code rate 0.10. Zero residual errors after decoding through GSM 06.10 (13 kbps) and **AMR at 5.1 kbps** (AMR needed 24 LDPC iterations against 8-9 otherwise) | [F] for ICME; [S] for TIFS |
| Pitch and duration modification | Çelik, Sharma, Tekalp, ICASSP 2005 | PSOLA changes to pitch and duration of quasi-periodic segments | Repository abstract reports robustness to coders at roughly 5-8 kbps | [S] |
| Formant enhancement via LSFs | Wang and Unoki, EUSIPCO 2014 | Move a pair of line spectral frequencies symmetrically to sharpen a formant | At 4 bps the bit detection rate met their 90% criterion through G.711, G.726 and **G.729**; the compared methods failed on G.729. AMR not tested | [F] |
| Phase of unvoiced speech | Hofbauer, Kubin, Kleijn, IEEE TASLP 17(8):1624-1637, 2009 | Replace the excitation of non-voiced speech in a subband; about 450 bit/s for analogue air-traffic radio | Analogue channel, not CELP codecs | [S] |
| Codec-bitstream hiding | e.g. Geiser and Vary, ICASSP 2008 (ACELP codebook, up to 2 kbit/s in AMR 12.2) | Hide data inside the encoder's own search | Needs control of the encoder; does not survive transcoding. Not applicable to Palabra | [S] |

### 1.3 Neural methods

| System | Source | Payload / duration | Codec tests reported | Code and licence | Tag |
|---|---|---|---|---|---|
| AudioSeal | San Roman, Fernandez, Elsahar, Défossez, Furon, Tran; ICML 2024; arXiv 2401.17264 | Sample-level detection, optional 16-bit message; trained at 16 kHz | Evaluated on MP3 32 kbps, AAC 64 kbps, EnCodec, filters. **No speech or telephony codec.** PESQ 4.470, ViSQOL 4.829, MUSHRA 77.07 (WavMark 71.52) | github.com/facebookresearch/audioseal, MIT including weights; streaming model since v0.2; 8 kHz not mentioned | [F], [A] |
| WavMark | Chen, Wu, Liu, Liu, Du, Wei; arXiv 2308.12770 | 32 bits per 1 s at 16 kHz | MP3 64 kbps, resampling, noise, etc. No speech codec. SNR 36.85 dB, PESQ 4.21 | github.com/wavmark/wavmark, MIT | [F], [A] |
| SilentCipher | Singh, Takahashi, Liao, Mitsufuji (Sony); Interspeech 2024; arXiv 2406.03822 | 40 bits (repo); evaluated on 6, 12, 24 s clips | MP3/OGG/AAC at 64/128/256 kbps. No speech codec | github.com/sony/silentcipher, MIT | [F], [A] |
| Timbre Watermarking | Liu, Zhang, Zhang, Yang, Zhang, Yu; NDSS 2024; arXiv 2312.03410 | Frequency-domain embedding repeated along time | MP3 at 8-64 kbps appears in their tables. I did not extract the numbers | Licence not checked | [F] partial |
| SynthID (audio) | Google DeepMind, deepmind.google/science/synthid | Not published | Page claims robustness to noise, MP3 and speed change, with no numbers. Nothing on telephony. No open detector stated | closed | [A] |
| PerTh | Resemble AI, github.com/resemble-ai/Perth | Not stated | README gives no numbers and names no codecs | MIT code; weight availability not confirmed | [A] |
| XAttnMark | Liu, Lu, Jin, Sun, Fanelli; arXiv 2502.04230 | Detection plus attribution | MP3 and AAC at 128 kbps | not checked | [F] partial |
| DiscreteWM | Ji, Jiang, Zuo, Fang, Chen, Jin, Zhao; arXiv 2412.13917 | 1-150 bits per second, in VQ token space | MP3 64 kbps | not checked | [F] partial |
| AWARE | Pavlović et al.; arXiv 2510.17512 (v2 Mar 2026) | Utterance-level and 20 bps variants | Includes a "VoIP transmission" attack: **Opus 16 kbps**, 20 ms frames, 2% loss, jitter. Bit error rate: WavMark 0.239, AudioSeal 0.480 (message-level miss rate 1.00), AWARE 0.102 (miss rate 0.23) | github.com/deepmarkpy/aware, licence not checked | [F] |
| Collaborative watermarking with codec augmentation | Juvela and Wang; arXiv 2409.13382 (2024) | Zero-bit; the synthesiser (HiFi-GAN) is trained jointly with the detector | See numbers below | github.com/ljuvela/DAREA, licence not checked | [F] |
| Cross-codec robustness | Pauna, Wang, Juvela; arXiv 2611.04716 (Nov 2026) | Zero-bit, DAC as generator | Augmenting with Mimi (1.1 kbps) and SNAC (0.98 kbps) generalised best to unseen neural codecs; MP3/Vorbis/Opus tested at 32 and 64 kbps only | same repo | [F] partial |
| CRAW | Chernin and Fetaya; arXiv 2609.03107 (Sep 2026) | Post-hoc with error-correcting code | Neural codecs, MP3 from 8 to 64 kbps | github.com/DavidC1212/craw | [F] partial |

Juvela and Wang, Table I, equal error rate when the test audio passes through Ogg-Opus at 16 kbps [F]:
- No codec augmentation: 53.44% (passive detector), 41.55% (collaborative watermark).
- Augmentation with MP3/Opus at 16 kbps through a straight-through gradient estimator: 5.17% (collaborative).
- Augmentation at all four bitrates: 10.50%.
- The 16 kbps augmentation gave the most robust detection and the worst listening-test score.

### 1.4 Benchmarks

- **AudioMarkBench** (Liu, Guo, Jiang, Wang, Gong; arXiv 2406.06979, NeurIPS 2024 Datasets and Benchmarks track) [F]. AudioSeal, Timbre and WavMark against 15 perturbations on a Common Voice-derived set and LibriSpeech. Finding: at ViSQOL of 3 or more, EnCodec, SoundStream and **Opus** produce very high false-negative rates, i.e. they remove the watermark while keeping quality. False-positive rates stay near zero except under quantization. Code: github.com/moyangkuo/AudioMarkBench.
- **SoK: How Robust is Audio Watermarking in Generative AI models?** (Wen, Innuganti, Ramos, Guo, Yan; arXiv 2503.19176) [F]. 22 schemes surveyed, 9 reproduced, 22 attack types in 109 configurations. Conclusion: none of the schemes withstands all tested distortions. The compression attack I found is MP3; I found no telephony codec. Code: sokaudiowm.github.io.
- **RAW-Bench** (Özer, Choi, Serrà, Singh, Liao, Mitsufuji; Sony; arXiv 2505.19663, Interspeech 2025 per Sony's page [S]) [F]. AudioSeal, SilentCipher, Timbre, WavMark. Neural codecs are the hardest case (bitwise accuracy generally below 0.5 through EnCodec and DAC); retraining with attacks helps but does not fix compression. Codecs are MP3, AAC, Ogg, EnCodec, DAC. Code: github.com/SonyResearch/raw_bench.
- **Deep Audio Watermarks are Shallow** (O'Reilly, Pardo, Jin, Su; ICLR 2025 GenAI Watermarking workshop; arXiv 2504.10782) [F] partial. Speech-focused; includes MP3 and Opus at 24 kbps and eight neural codecs down to 2.2 kbps; shows post-hoc watermarks can be removed with little quality loss.

**Gap that matters for the paper.** In everything I opened, no neural watermark is evaluated through AMR-NB, AMR-WB, EVS, G.729 or G.723.1. The lowest Opus rates tested are 8 kbps (Looney and Gaubitch, classical) and 16 kbps (Juvela and Wang; AWARE). A dedicated search for neural watermarks tested on AMR/EVS/G.729 returned nothing. Palabra's codec matrix is therefore already broader on the telephony side than the published neural work.

---

## 2. What survives low-bitrate speech codecs

### What the sources say

- **Amplitude and phase are not preserved; even pure tones in band are distorted.** AuthLoop [F]: "amplitudes are not well preserved by voice codecs", many codecs lose phase so coherent demodulation fails, and "many codecs fail to accurately reproduce input frequencies". This ruled out ASK, QAM and PSK and led them to slow FSK.
- **Codecs assume voice-like input and change mode mid-call.** Hermes [F]: non-voice-like signals are heavily distorted, and AMR switches among its modes according to radio conditions, so a fixed distortion model is unreliable.
- **A linear-filter-plus-scaling model describes AMR 12.2 well enough to design for.** Kazemi et al. [F] attribute the linear part to quantization of the LPC/LSP filter and the interpolation and long-term synthesis filters.
- **Pitch survives.** Coumou and Sharma [F] chose pitch because low-rate coders keep it, and recovered data through AMR at 5.1 kbps (at well under 1 bps net).
- **LSF/formant structure survives.** Wang and Unoki [F] argue LSFs are the common currency of speech codecs; their formant mark met a 90% detection criterion through G.729 at 4 bps while spread-spectrum and other baselines collapsed.
- **Opus/SILK transmits a parametric description plus a coarse excitation.** RFC 6716 [A] lists per-frame gains, short-term prediction (LSF) coefficients, LTP lags and gains, and a quantized excitation. It gives 8-12 kbit/s as the sweet spot for narrowband speech and 16-20 kbit/s for wideband. Vos et al., "Voice Coding with Opus" (AES 135, 2013, slides) [F] describe short- and long-term prediction that model formants and harmonics, with short- and long-term noise shaping.
- **In passive deepfake forensics, only first-formant statistics kept discriminative power across telephony codecs.** Sukhdeve, Storey, Imtiaz (arXiv 2611.13258, IJCB 2026) [F] partial: on ASVspoof 2021 LA, of the hand-crafted families tested only four first-formant measures survived screening; G.711 eroded 13-51% of the separation depending on the feature. This is a tracker-based result about detection features, not about watermarks.

### Summary table

| Signal property | CELP family (AMR, G.729, G.723.1, EVS) and SILK | Basis |
|---|---|---|
| Spectral envelope at formant scale (LSFs) | preserved, coarsely quantized | Wang and Unoki; Kazemi; RFC 6716 |
| Pitch / F0 contour | preserved | Coumou and Sharma; Çelik et al. [S] |
| Frame gain contour | transmitted, but absolute amplitude is not reliable | RFC 6716; AuthLoop |
| Timing at frame scale | preserved; first milliseconds may be truncated | AuthLoop |
| Waveform phase | lost | AuthLoop |
| Fine spectral structure between harmonics, noise-like components | replaced by codebook excitation and shaped noise | Inference from the codec structure in RFC 6716 and Vos et al.; consistent with the spread-spectrum failures in Wang and Unoki and the Opus 8 kbps EERs in Looney and Gaubitch |

EVS and G.723.1: UNVERIFIED. I opened no source on their behaviour; they are included by family resemblance only.

### Reading of the Palabra results (Inference)

G.711 and G.726 are waveform coders, so a 190 Hz by 32 ms loudness pattern passes through. iLBC, G.723.1 and SILK re-synthesise from an LPC envelope plus a coarse excitation. With a tenth-order envelope over 4 kHz, a plus/minus 2 dB step between adjacent 190 Hz tiles is finer than the envelope can represent, so it has to ride on the excitation, which is exactly what these codecs spend the fewest bits on. Opus at 6 kbps is below the narrowband sweet spot in RFC 6716, and 12 kbps is below the wideband one if the encoder is fed wideband audio.

---

## 3. Data-over-voice and in-band authentication

| System | Source | Signal | Rate and reliability over codecs | Audible? | Tag |
|---|---|---|---|---|---|
| AuthLoop | Reaves, Blue, Traynor; USENIX Security 2016 | 3-tone FSK modem (1000/2000/3000 Hz), 500 Hz header, link layer, TLS-like handshake | 500 bps goodput. Bit error: G.711 0.0%, AMR-NB 0.3%, Speex 0.5%. Handshake about 9 s with cached certificate, 97 s for naive TLS 1.2. Software codec channels, not live cellular | yes, modem tones in the voice band | [F] |
| AuthentiCall | Reaves, Blue, Abdullah, Vargas, Traynor, Shrimpton; USENIX Security 2017 | A separate low-bitrate data channel bound to the call; audio digests protect content | Detects 99% of tampered call audio with negligible false positives; worst-case 1.4 s added call setup | no in-band signal | [A] |
| Hermes | Dhananjay, Sharma, Paik, Chen, Kuppusamy, Li, Subramanian (NYU); MobiCom 2010 | Voice-like modulation adapted to unknown channels | 1.2 kbps goodput with bit error rates of the order of 1e-5 over real cellular voice channels; standard ASK/FSK/PSK gave unusable error rates through AMR | yes | [F] |
| GSM voice-channel modem | LaDue, Sapozhnykov, Fienberg; IEEE Trans. Veh. Technol. 57(4):2205-2218, 2008 | Predefined speech-like symbols | Numbers UNVERIFIED (a survey attributes about 4 kbps at 2.3% bit error over EFR to this line of work, attribution unclear) | yes | [S] |
| eCall in-band modem | 3GPP TS 26.267 | Standardised modem carrying a 140-byte data set over the voice channel | Timing numbers UNVERIFIED | yes; voice is muted during transfer (from memory, not checked) | [S] |
| ggwave | G. Gerganov, github.com/ggerganov/ggwave | Multi-tone FSK, 6 tones per symbol, Reed-Solomon | 8-16 bytes/s. Audible protocols start at 1875 Hz across a 4.5 kHz band, so part of the band lies above the 3.4 kHz telephone cutoff; ultrasonic modes start at 15 kHz. No statement about phone calls. MIT | yes (or ultrasonic) | [A] |
| GibberLink | Pidkuiko and Starkov, github.com/PennyroyalTea/gibberlink, Feb 2025 | Two ElevenLabs agents switch to ggwave when each recognises the other as AI | No speed or reliability numbers, no codec claims, no authentication. MIT | yes | [A] |
| DTMF | RFC 4733 | Dual tones, usually sent out of band as RTP events | UNVERIFIED in this survey | yes | UNVERIFIED |
| CallShield | see 1.1 | Neural watermark as a serial link | 25 bit/s raw (1 bit per 40 ms); 63 s per authentication; codecs not tested | no (PESQ above 4.2) | [F] |

Takeaway: audible modems reach hundreds of bits per second through AMR-NB with low error. Inaudible marks are three orders of magnitude slower through CELP codecs (3.2 bps in Kazemi, 4 bps in Wang and Unoki, below 1 bps net in Coumou and Sharma). A zero-bit design avoids competing on bit rate at all.

---

## 4. Caller authentication standards and products

- **STIR: RFC 8224** (Peterson, Jennings, Rescorla, Wendt; Feb 2018) [A], with **RFC 8225** (PASSporT token) and **RFC 8226** (certificates) as described there. The Identity header signs the calling identity, called identity, timestamp and media key fingerprints. Gap: it does not authenticate the media, says nothing about who the speaker acts for or why, and is lost on non-SIP hops.
- **Out-of-band STIR: RFC 8816** (Rescorla, Peterson; Feb 2021; Informational) [A]. Before dialling, the caller side stores an encrypted PASSporT (caller, callee, time) at a Call Placement Service, indexed by the called number; the callee side fetches it when the call arrives. Entries should age out after about 60 s, and the RFC discusses a substitution attack where an attacker races the legitimate call inside that window. **This is the registry half of Palabra, already standardised at the signalling level.** Gap: nothing ties the stored token to the audio that actually arrives, so the race condition is acknowledged and unsolved; no purpose or principal fields.
- **Rich Call Data: RFC 9795** (Wendt, Peterson; July 2025; Standards Track) [A]. Adds `rcd` (name, icon, jCard), `rcdi` (integrity digests) and `crn` (call reason). `crn` is a single free-text string. Gap: intent is not structured, and the claim still travels in signalling.
- **VESPER**, draft-wendt-stir-vesper-11 (Wendt, Śliwa; 1 Nov 2026; individual draft) [A]. Delegate-certificate profile binding a number's right-to-use to a domain, plus a portable Right-to-Use token. The IETF 126 STIR minutes (21 July 2026) [A] show it under active discussion and rename the Call Placement Service to "Passport Placement Service". Explicitly does not do identity vetting. No audio, no AI-specific content.
- **Verifiable Voice Protocol**, draft-hardman-verifiable-voice-protocol-08 (Hardman, Provenant; 5 Oct 2026; individual draft) [A]. A pre-curated credential dossier proves the accountable party, brand, right to the number and delegated signers; an optional `goal` claim must be authorised in the dossier; a callee's dossier can show authority delegated to a call centre or an AI. Signalling only. Gap: closest standard to "who it speaks for and why", but nothing in the audio.
- **Open Verifiable Calling** (GSMA Foundry alliance; Microsoft deployment write-up dated 18 June 2026) [A]. Vetting agents issue credentials for number, legal entity and brand; Provenant signs. No AI-agent or per-call intent content in the article.
- **CTIA Branded Calling ID, Truecaller Verified Business** [S, vendor and integrator pages only]. Show a vetted name, logo and call reason on the handset. Gap: display features keyed to the number; no per-call cryptographic binding visible to a machine on the receiving side.
- **Pindrop** [A/S]. Pulse is passive synthetic-voice detection with a liveness score (vendor-reported accuracy). PinDr0p (Balasubramaniyan, Poonawalla, Ahamad, Hunter, Traynor; CCS 2010, pp. 109-120) [S] fingerprints codecs and loss from received audio to infer call provenance. Gap: these answer "is it synthetic / where did it come from", not "is this the registered call".
- **Regulation.** FCC notice of proposed rulemaking on AI-generated calls (Federal Register, 10 Sep 2024) [S] would define "AI-generated call" and require disclosure; I found no final rule. A news item says the FCC wants AI voices to identify themselves [S].
- **Agent identity drafts.** Several 2026 individual IETF drafts address AI-agent identity and authorisation in general (for example draft-klrc-aiagent-auth) [S]. None that I found addresses telephone audio.

**Remaining gap across all of these.** Every deployed or proposed mechanism lives in signalling or in an app-to-app data channel. None lets the receiving endpoint check, from the audio alone and after arbitrary transcoding hops, that the speech it hears belongs to a specific pre-registered call with a stated principal and purpose.

---

## 5. Zero-bit keyed detection theory to cite

- **Costa, "Writing on dirty paper"**, IEEE Trans. Inf. Theory 29(3):439-441, 1983 [S]. Interference known to the encoder costs no capacity. Justifies treating the host speech as known side information at the embedder.
- **Chen and Wornell, QIM**, IEEE Trans. Inf. Theory 47(4):1423-1443, 2001 [S]. Practical host-rejecting embedding; sensitive to amplitude scaling, which matters because voice codecs do not preserve amplitude (AuthLoop).
- **Malvar and Florêncio, "Improved spread spectrum"**, IEEE Trans. Signal Process. 51(4):898-905, 2003 [S, via Microsoft Research page excerpt]. Removes the host as a noise source in correlation detection, with about the same gain as QIM and without the amplitude-scale sensitivity. Abstract reports up to 20 dB SNR gain in some examples.
- **Cox, Kilian, Leighton, Shamoon**, 1997 [S]. Spread-spectrum watermarking and the normalised-correlation detector.
- **Cox, Miller, Bloom, *Digital Watermarking* (book), and Miller, Cox, Bloom, "Informed embedding", ICIP 2000.** UNVERIFIED in this survey.
- **Furon, "A constructive and unifying framework for zero-bit watermarking"**, IEEE TIFS 2(2):149-163, 2007; arXiv cs/0606034 [A]. Treats zero-bit watermarking as a detection problem with side information at the embedder and derives jointly optimal embedding and detection functions. The most direct theoretical citation for Palabra's detector.
- **Chandramouli and Memon, "On sequential watermark detection"**, IEEE Trans. Signal Process. 51(4):1034-1044, 2003 [S]. Sequential hypothesis testing for watermark detection; faster decisions than fixed-sample detectors.
- **Wald's sequential probability ratio test** (1945). UNVERIFIED in this survey; standard citation.
- **Su, Wang, Zhao, "Online LLM watermark detection via e-processes"**, arXiv 2602.14286 (2026) [F] partial. Anytime-valid sequential watermark detection; the authors state the method applies to any sequential test with independent pivotal statistics. Relevant because Palabra monitors continuously and searches over start offsets, both of which inflate false alarms under a naive fixed z threshold.
- **San Roman et al. (AudioSeal)** [F] is a current example of reporting detector false-positive rates explicitly for an audio watermark.

---

## 6. Evaluation methodology used by others

**Datasets**
- LibriSpeech: used by AudioMarkBench and WavMark [F]. Common Voice: AudioMarkBench's own set and WavMark [F]. TIMIT: Looney and Gaubitch [F] (licensed).
- VCTK: UNVERIFIED as to which of the above use it.
- Telephone speech, free to download:
  - **HarperValleyBank** (Wu et al., Stanford and Gridspace; arXiv 2010.13929) [A]: about 23 hours, 1,446 simulated banking calls, 59 speakers, 8 kHz, each side recorded separately, CC-BY.
  - **Robocall Audio Dataset** (Prasad and Reaves, NCSU TR-2023-1; github.com/wspr-ncsu/robocall-audio-dataset) [S]: real robocall recordings released by the FTC; the report says 1,101 recordings and the repository example shows 1,432 rows.
  - **ASVspoof 2021 LA** (evaluation plan arXiv 2109.00535; summary paper arXiv 2210.02437) [S]: speech sent through an Asterisk system with a-law, mu-law, GSM 06.10 at 8 kHz and G.722, Opus at 16 kHz, plus one real PSTN condition. Useful as a transmission protocol to copy.
- Switchboard-1: used by CallShield [F]; distributed by the LDC under licence, not free.

**Codec simulation**
- AuthLoop used software codec channels with reference G.711 and AMR-NB implementations and ffmpeg's Speex [F].
- ITU-T G.191 Software Tool Library (latest edition 07/2026) [A].
- Juvela and Wang wrap black-box codecs with a waveform-domain straight-through estimator so they can sit inside an optimisation loop [F].
- ASVspoof 2021 used real Asterisk calls between SIP endpoints, one call per utterance [S].
- AWARE adds packet loss, jitter and delay to Opus [F].
- 3GPP reference coders for AMR, AMR-WB and EVS: UNVERIFIED in this survey.

**Quality metrics and thresholds**
- PESQ (ITU-T P.862) [A]: scope is narrowband telephone networks and codecs. **Withdrawn by ITU on 5 January 2024 in favour of P.863 (POLQA)**; still the de facto metric in every watermark paper opened. WavMark describes values above 4.0 as indicating good quality [F]; Pindrop treats PESQ above 4 as "imperceptible" [A]; CallShield reports above 4.2 [F]; Looney and Gaubitch work at narrowband PESQ of about 4.4 [F].
- POLQA (ITU-T P.863, 03/2018 edition in force) [A]. Licensed; none of the watermark papers opened uses it.
- ViSQOL v3 (Chinen et al., QoMEX 2020, arXiv 2004.09584; github.com/google/visqol, Apache-2.0) [A]: speech mode at 16 kHz, maximum 5.0. AudioMarkBench uses ViSQOL of 3 or more as "good quality" for attacked audio; the SoK uses 4.0 or more as its high-quality constraint; AudioSeal reports 4.829 for its own watermark [F].
- MUSHRA (ITU-R BS.1534): AudioSeal 77.07 against WavMark 71.52 [F]. A general "transparent" cut-off: UNVERIFIED.
- SNR / SI-SNR: WavMark 36.85 dB; AudioSeal 26.00 dB SI-SNR with the remark that SI-SNR does not track perceived quality [F]. The often-quoted "SNR above 20 dB" industry criterion: UNVERIFIED.
- A/B/X listening: Kazemi et al. [F]. Narrowband and wideband PESQ reported separately: Looney and Gaubitch [F].
- A 2024 paper found by search states that no fixed SI-SNR or PESQ threshold determines perceptibility and recommends listening tests [S].

**Suggested minimum for the Palabra paper (Inference):** narrowband PESQ of at least 4.0 with an A/B/X or MUSHRA listening test; false-alarm rate measured on unmarked real telephone speech rather than only TTS; AMR-NB at every mode, AMR-WB, EVS, and at least one tandem (for example Opus then G.711 then AMR), because Hermes shows AMR changes mode mid-call.

---

## 7. Recommendations

### Has someone already built this?

Not as a whole, as far as this survey found. The pieces exist separately:

- Registry lookup keyed by callee number and time, written before the call: **RFC 8816** (signalling tokens, no audio).
- In-band audio-layer caller authentication with a keyed mark: **CallShield** (pairwise keys, multi-bit, 63 s, no codec tests, humans not AI agents).
- Zero-bit keyed speech watermark for telephony with accumulation over frames: **Looney and Gaubitch / Pindrop** (global key, synthetic-speech flagging, no registry).
- Binding call audio to an authenticated side channel: **AuthentiCall** (audio digests over a data connection, no watermark).
- Declared principal and purpose for a call, including delegated AI: **VVP** `goal` claim and dossier (signalling only).

I found no paper, draft, product page or patent application that combines a per-call keyed audio mark with a registry lookup for AI-agent calls. The limits of that statement: a handful of web searches, one patent hit (Pindrop), and no systematic patent-database search.

### Changes most likely to help on Opus and AMR-class codecs at equal audibility

1. **Move the mark to envelope scale.** Replace 190 Hz by 32 ms tile pairs with a few wide, formant-scale modifications held over many frames, ideally expressed as LSF-pair or formant-sharpening moves. Source: Wang and Unoki met 90% detection through G.729 where spread-spectrum baselines failed; Kazemi et al. integrate over 2500 samples (about 310 ms) per symbol to get through AMR 12.2. A zero-bit detector does not need the bit density the current tiling provides.
2. **Add a pitch-contour carrier and fuse the two z-scores.** A keyed micro-modulation of F0 uses the one parameter low-rate coders protect most. Source: Coumou and Sharma recovered pitch-QIM data through AMR at 5.1 kbps; Çelik et al. report 5-8 kbps coders [S]. With TTS the modulation can be applied at synthesis rather than by post-processing (Inference).
3. **Reject host interference at the embedder.** The embedder knows the host exactly. Compute each pair's natural log-energy difference and add only what is needed to reach the target statistic, instead of a fixed plus/minus 2 dB. Sources: Malvar and Florêncio (improved spread spectrum; no amplitude-scale sensitivity, which matters given AuthLoop's observation about amplitudes); Furon's side-informed zero-bit framework; Costa.
4. **Put the codec in the embedding loop.** Run the target codecs at the embedder and iterate the embedding against the decoded output, or train a small learned embedder with black-box codecs behind a straight-through estimator. Source: Juvela and Wang cut Opus 16 kbps EER from 41.55% to 5.17% with 16 kbps codec augmentation, at a measurable listening-test cost. Kazemi's filter-plus-scaling channel model is the analytic version of the same idea for AMR.
5. **Shape perceptually and upgrade the detector.** Use LPC-derived shaping instead of flat steps, replace the plain correlation with a cepstrally filtered or small learned decoder that pools over frames, and wrap the accumulation in a sequential test with anytime-valid error control. Sources: Looney and Gaubitch (LPC shaping lowered EER at equal PESQ; learned decoder cut EER by 86% over 30 frames through Opus at 8 kbps); Chandramouli and Memon; Su, Wang and Zhao.

Expectation to set in the paper: the published evidence suggests Opus at 6 kbps and G.723.1 at 6.3 kbps may stay out of reach for an inaudible mark within about 5 s. The only inaudible schemes shown through codecs of that class run at a few bits per second or less.

---

## References

Opened in full or in part [F]
1. M. Rabhi, Y. Boshmaf, M. Alsabah, S. Chowdhury, M. Hefeeda, I. Khalil. "CallShield: Secure Caller Authentication over Real-Time Audio Channels." arXiv:2601.09327, 2026. https://arxiv.org/abs/2601.09327
2. D. Looney, N. D. Gaubitch. "Robust spread spectrum speech watermarking using linear prediction and deep spectral shaping." Interspeech 2024. https://www.isca-archive.org/interspeech_2024/looney24_interspeech.pdf
3. R. Kazemi, F. Pérez-González, M. A. Akhaee, F. Behnia. "Data Hiding Robust to Mobile Communication Vocoders." IEEE Trans. Multimedia, 2016. DOI 10.1109/TMM.2016.2599149. https://gpsc.uvigo.es/wp-content/uploads/2016/12/TMM2599149.pdf
4. D. J. Coumou, G. Sharma. "Watermark synchronization for feature-based embedding: application to speech." ICME 2006 (journal version: "Insertion, Deletion Codes With Feature-Based Embedding", IEEE TIFS, 2008). https://www.cecs.uci.edu/~papers/icme06/pdfs/0000849.pdf
5. S. Wang, M. Unoki. "Watermarking of speech signals based on formant enhancement." EUSIPCO 2014. https://new.eurasip.org/Proceedings/Eusipco/Eusipco2014/HTML/papers/1569924405.pdf
6. R. San Roman, P. Fernandez, H. Elsahar, A. Défossez, T. Furon, T. Tran. "Proactive Detection of Voice Cloning with Localized Watermarking." ICML 2024. arXiv:2401.17264. Code: https://github.com/facebookresearch/audioseal
7. G. Chen, Y. Wu, S. Liu, T. Liu, X. Du, F. Wei. "WavMark: Watermarking for Audio Generation." arXiv:2308.12770, 2023. Code: https://github.com/wavmark/wavmark
8. M. K. Singh, N. Takahashi, W. Liao, Y. Mitsufuji. "SilentCipher: Deep Audio Watermarking." Interspeech 2024. arXiv:2406.03822. Code: https://github.com/sony/silentcipher
9. C. Liu, J. Zhang, T. Zhang, X. Yang, W. Zhang, N. Yu. "Detecting Voice Cloning Attacks via Timbre Watermarking." NDSS 2024. arXiv:2312.03410.
10. H. Liu, M. Guo, Z. Jiang, L. Wang, N. Z. Gong. "AudioMarkBench: Benchmarking Robustness of Audio Watermarking." NeurIPS 2024 Datasets and Benchmarks. arXiv:2406.06979. Code: https://github.com/moyangkuo/AudioMarkBench
11. Y. Wen, A. Innuganti, A. B. Ramos, H. Guo, Q. Yan. "SoK: How Robust is Audio Watermarking in Generative AI models?" arXiv:2503.19176, 2025. https://sokaudiowm.github.io/
12. Y. Özer, W. Choi, J. Serrà, M. K. Singh, W.-H. Liao, Y. Mitsufuji. "A Comprehensive Real-World Assessment of Audio Watermarking Algorithms: Will They Survive Neural Codecs?" arXiv:2505.19663, 2025. Code: https://github.com/SonyResearch/raw_bench
13. P. O'Reilly, Z. Jin, J. Su, B. Pardo. "Deep Audio Watermarks are Shallow: Limitations of Post-Hoc Watermarking Techniques for Speech." ICLR 2025 GenAI Watermarking workshop. arXiv:2504.10782.
14. L. Juvela, X. Wang. "Audio Codec Augmentation for Robust Collaborative Watermarking of Speech Synthesis." arXiv:2409.13382, 2024. Code: https://github.com/ljuvela/DAREA
15. O.-P. Pauna, X. Wang, L. Juvela. "Cross-Codec Robustness in Speech Watermarking." arXiv:2611.04716, 2026.
16. D. Chernin, E. Fetaya. "CRAW: Codec Robust Audio Watermarking." arXiv:2609.03107, 2026. Code: https://github.com/DavidC1212/craw
17. K. Pavlović, L. Stanarević, P. Nedić, E. Nešović, S. Kovačević, I. Djurović. "AWARE: Audio Watermarking via Adversarial Resistance to Edits." arXiv:2510.17512, 2025-2026. Code: https://github.com/deepmarkpy/aware
18. Y. Liu, L. Lu, J. Jin, L. Sun, A. Fanelli. "XAttnMark: Learning Robust Audio Watermarking with Cross-Attention." arXiv:2502.04230, 2025.
19. S. Ji, Z. Jiang, J. Zuo, M. Fang, Y. Chen, T. Jin, Z. Zhao. "Speech Watermarking with Discrete Intermediate Representations." arXiv:2412.13917, 2024.
20. B. Reaves, L. Blue, P. Traynor. "AuthLoop: End-to-End Cryptographic Authentication for Telephony over Voice Channels." USENIX Security 2016. https://www.usenix.org/system/files/conference/usenixsecurity16/sec16_paper_reaves.pdf
21. A. Dhananjay, A. Sharma, M. Paik, J. Chen, T. K. Kuppusamy, J. Li, L. Subramanian. "Hermes: Data Transmission over Unknown Voice Channels." MobiCom 2010. https://cs.nyu.edu/~lakshmi/Lakshmi/Project%20Websites/GreenLinks/Hermes-Data%20Transmission%20over%20Unknown%20Voice%20Channels.pdf
22. K. Vos, K. V. Sørensen, S. S. Jensen, J.-M. Valin. "Voice Coding with Opus." AES 135th Convention, 2013 (slides). https://opus-codec.org/static/presentations/opus_voice_aes135.pdf
23. Y. Sukhdeve, A. Storey, M. H. Imtiaz. "Which Acoustic Features Survive Compression? Tracker-Estimated First-Formant Statistics for Codec-Robust Audio Deepfake Detection." IJCB 2026. arXiv:2611.13258.
24. W. Su, R. Wang, Z. Zhao. "Online LLM watermark detection via e-processes." arXiv:2602.14286, 2026.

Abstract, landing page, RFC, draft or repository opened [A]
25. B. Reaves, L. Blue, H. Abdullah, L. Vargas, P. Traynor, T. Shrimpton. "AuthentiCall: Efficient Identity and Content Authentication for Phone Calls." USENIX Security 2017, pp. 575-592. https://www.usenix.org/conference/usenixsecurity17/technical-sessions/presentation/reaves
26. J. Peterson, C. Jennings, E. Rescorla, C. Wendt. RFC 8224, "Authenticated Identity Management in the Session Initiation Protocol (SIP)." 2018. https://www.rfc-editor.org/rfc/rfc8224.html (RFC 8225 and RFC 8226 as described there; not opened separately.)
27. E. Rescorla, J. Peterson. RFC 8816, "Secure Telephone Identity Revisited (STIR) Out-of-Band Architecture and Use Cases." 2021. https://www.rfc-editor.org/rfc/rfc8816.html
28. C. Wendt, J. Peterson. RFC 9795, "Personal Assertion Token (PASSporT) Extension for Rich Call Data." 2025. https://www.rfc-editor.org/rfc/rfc9795.html
29. C. Wendt, R. Śliwa. "VESPER - Verifiable STI Presentation and Evidence for RTU." draft-wendt-stir-vesper-11, Nov 2026. https://datatracker.ietf.org/doc/draft-wendt-stir-vesper/
30. D. Hardman. "Verifiable Voice Protocol." draft-hardman-verifiable-voice-protocol-08, Oct 2026. https://datatracker.ietf.org/doc/draft-hardman-verifiable-voice-protocol/
31. IETF 126 STIR working group minutes, 21 July 2026. https://datatracker.ietf.org/meeting/126/materials/minutes-126-stir-00
32. Microsoft Inside Track. "Advancing trusted calls with Open Verifiable Calling at Microsoft." 18 June 2026. https://www.microsoft.com/insidetrack/blog/advancing-trusted-calls-with-open-verifiable-calling-at-microsoft/
33. J.-M. Valin, K. Vos, T. Terriberry. RFC 6716, "Definition of the Opus Audio Codec." 2012. https://www.rfc-editor.org/rfc/rfc6716.html
34. T. Furon. "A constructive and unifying framework for zero-bit watermarking." IEEE TIFS 2(2):149-163, 2007. arXiv:cs/0606034.
35. N. Gaubitch. "Does Watermarking Protect Against Deepfake Attacks?" Pindrop blog, 20 Oct 2023. https://www.pindrop.com/blog/does-watermarking-protect-against-deepfake-attacks
36. S. Westerfeld. audiowmark. https://github.com/swesterfeld/audiowmark
37. G. Gerganov. ggwave. https://github.com/ggerganov/ggwave
38. A. Pidkuiko, B. Starkov. GibberLink. https://github.com/PennyroyalTea/gibberlink
39. Resemble AI. Perth. https://github.com/resemble-ai/Perth
40. Google DeepMind. SynthID. https://deepmind.google/science/synthid/
41. Google. ViSQOL. https://github.com/google/visqol (M. Chinen et al., "ViSQOL v3", QoMEX 2020, arXiv:2004.09584.)
42. ITU-T P.862 (PESQ), withdrawn 5 Jan 2024. https://www.itu.int/rec/T-REC-P.862
43. ITU-T P.863 (POLQA). https://www.itu.int/rec/T-REC-P.863
44. ITU-T G.191, Software tools for speech and audio coding standardization. https://www.itu.int/rec/T-REC-G.191
45. M. Wu, J. Nafziger, A. Scodary, A. Maas. "HarperValleyBank: A Domain-Specific Spoken Dialog Corpus." arXiv:2010.13929, 2020 (title page opened; corpus statistics taken from the abstract as returned by search).

Confirmed from search excerpts only [S]
46. M. Costa. "Writing on dirty paper." IEEE Trans. Inf. Theory 29(3):439-441, 1983. DOI 10.1109/TIT.1983.1056659.
47. B. Chen, G. W. Wornell. "Quantization index modulation: a class of provably good methods for digital watermarking and information embedding." IEEE Trans. Inf. Theory 47(4):1423-1443, 2001.
48. H. S. Malvar, D. A. F. Florêncio. "Improved spread spectrum: a new modulation technique for robust watermarking." IEEE Trans. Signal Process. 51(4):898-905, 2003. https://www.microsoft.com/en-us/research/publication/improved-spread-spectrum-a-new-modulation-technique-for-robust-watermarking/
49. I. J. Cox, J. Kilian, F. T. Leighton, T. Shamoon. "Secure spread spectrum watermarking for multimedia." IEEE Trans. Image Process. 6(12):1673-1687, 1997.
50. R. Chandramouli, N. D. Memon. "On sequential watermark detection." IEEE Trans. Signal Process. 51(4):1034-1044, 2003.
51. W. Bender, D. Gruhl, N. Morimoto, A. Lu. "Techniques for data hiding." IBM Systems Journal 35(3/4):313-336, 1996.
52. D. Gruhl, A. Lu, W. Bender. "Echo hiding." Information Hiding 1996, LNCS 1174.
53. I.-K. Yeo, H. J. Kim. "Modified patchwork algorithm: a novel audio watermarking scheme." IEEE Trans. Speech Audio Process., 2003. DOI 10.1109/TSA.2003.812145.
54. I. Natgunanathan, Y. Xiang, Y. Rong, W. Zhou, S. Guo. "Robust patchwork-based embedding and decoding scheme for digital audio watermarking." IEEE TASLP 20(8):2232-2239, 2012.
55. M. Çelik, G. Sharma, A. M. Tekalp. "Pitch and duration modification for speech watermarking." ICASSP 2005, vol. 2, pp. 17-20.
56. K. Hofbauer, G. Kubin, W. B. Kleijn. "Speech watermarking for analog flat-fading bandpass channels." IEEE TASLP 17(8):1624-1637, 2009.
57. C. K. LaDue, V. V. Sapozhnykov, K. S. Fienberg. "A data modem for GSM voice channel." IEEE Trans. Veh. Technol. 57(4):2205-2218, 2008. DOI 10.1109/TVT.2007.912322.
58. 3GPP TS 26.267, "eCall data transfer; In-band modem solution; General description."
59. V. A. Balasubramaniyan, A. Poonawalla, M. Ahamad, M. T. Hunter, P. Traynor. "PinDr0p: using single-ended audio features to determine call provenance." ACM CCS 2010, pp. 109-120.
60. S. Prasad, B. Reaves. "Robocall Audio Dataset." NCSU TR-2023-1. https://github.com/wspr-ncsu/robocall-audio-dataset
61. ASVspoof 2021 evaluation plan, arXiv:2109.00535; X. Liu et al., "ASVspoof 2021: Towards Spoofed and Deepfake Speech Detection in the Wild", arXiv:2210.02437.
62. FCC. "Implications of Artificial Intelligence Technologies on Protecting Consumers From Unwanted Robocalls and Robotexts." Federal Register, 10 Sep 2024. https://www.federalregister.gov/documents/2024/09/10/2024-19028/
63. Pindrop. US patent application 20250095662, "Robust spread-spectrum speech watermarking using linear prediction and deep spectral shaping." https://patents.justia.com/patent/20250095662
64. B. Geiser, P. Vary. "High rate data hiding in ACELP speech codecs." ICASSP 2008.
65. CTIA Branded Calling ID; Truecaller Verified Business (vendor and integrator pages only).

UNVERIFIED (named in the brief or standard citations; not confirmed here)
66. I. J. Cox, M. L. Miller, J. A. Bloom. *Digital Watermarking*. Morgan Kaufmann.
67. M. L. Miller, I. J. Cox, J. A. Bloom. "Informed embedding: exploiting image and detector information during watermark insertion." ICIP 2000.
68. A. Wald. "Sequential tests of statistical hypotheses." Annals of Mathematical Statistics, 1945.
69. D. Kirovski, H. S. Malvar. "Spread-spectrum watermarking of audio signals." IEEE Trans. Signal Process., 2003.
70. Q. Cheng, J. Sorensen. "Spread spectrum signaling for speech watermarking." ICASSP 2001.
71. RFC 4733 (DTMF over RTP); ITU-R BS.1534 (MUSHRA) thresholds; 3GPP AMR, AMR-WB and EVS reference coder specifications; G.723.1 behaviour; LibriSpeech and VCTK corpus papers.
