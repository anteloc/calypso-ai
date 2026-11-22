---
name: choosing-a-model
description: 'Picking a Moonshine speech to text model: the available models per language and architecture (Tiny, Small, Medium Streaming and deprecated non-streaming ones), parameter counts, licenses (MIT vs Moonshine Community License), word error rates (LibriSpeech, FLEURS, Open ASR Leaderboard, float vs quantized), latency benchmarks across devices, and how Moonshine compares with Whisper for live speech. Use when choosing a model size or architecture (`model_arch()`, `ModelArch`) for a language or device, comparing accuracy or latency, reproducing the accuracy numbers, or deciding between Moonshine and Whisper.'
---

# Choosing a Model

Pick the right Moonshine speech to text model for a language and device: which architectures exist, their size, license, accuracy and latency, and when Moonshine fits better than Whisper. To select a model in code, use `model_arch()` on `MicTranscriber` / `AgentFlow` or `model_arch` on `Transcriber` (see [transcription](../transcription/SKILL.md)). To get the files, see [downloading-models](../downloading-models/SKILL.md).

## Quick guidance

- **Use the default unless you have a reason not to.** Each language downloads its first listed model below: Medium Streaming for English, a streaming model for every language that has one. Most languages publish only one model.
- **Trade size for accuracy and latency within English:** Medium Streaming (most accurate) → Small Streaming → Tiny Streaming (smallest, fastest).
- **Prefer streaming models.** They do most of the work while the user is still talking, so the final text arrives quickly. Non-streaming models with a streaming replacement are deprecated.
- **Non-Latin scripts** (Arabic, Japanese, Korean, Mandarin, Ukrainian): set the `max_tokens_per_second` option to 13.0 when creating the transcriber. Its hallucination guard (an unusually high token rate for the segment duration, signalling endless repetition) otherwise cuts off valid output, because these tokenizers produce more tokens per second.
- **License:** every model is MIT except the older non-streaming non-English ones, which use the non-commercial Moonshine Community License.

## Available models

Models are ONNX converted to memory-mappable OnnxRuntime `.ort` files. English WER is the [Open ASR Leaderboard](https://huggingface.co/spaces/hf-audio/open_asr_leaderboard) average over eight datasets (floating-point reference). Non-English streaming scores are 400-clip macros of the shipped quantized models.

| Language   | Architecture     | # Parameters | WER/CER | License   |
| ---------- | ---------------- | ------------ | ------- | --------- |
| English    | Medium Streaming | 245 million  | 6.65%   | MIT       |
| English    | Small Streaming  | 123 million  | 7.84%   | MIT       |
| English    | Tiny Streaming   | 34 million   | 12.00%  | MIT       |
| Arabic     | Tiny Streaming   | 34 million   | 15.5%   | MIT       |
| German     | Small Streaming  | 123 million  | 7.5%    | MIT       |
| German     | Tiny Streaming   | 34 million   | 12.0%   | MIT       |
| Japanese   | Small Streaming  | 123 million  | 17.2%†  | MIT       |
| Japanese   | Tiny Streaming   | 34 million   | 19.7%†  | MIT       |
| Mandarin   | Tiny Streaming   | 34 million   | 16.1%†  | MIT       |
| Spanish    | Small Streaming  | 123 million  | 4.9%    | MIT       |
| Spanish    | Tiny Streaming   | 34 million   | 6.2%    | MIT       |
| Tagalog    | Tiny Streaming   | 34 million   | 14.9%   | MIT       |
| Vietnamese | Tiny Streaming   | 34 million   | 9.4%    | MIT       |
| English    | Base             | 58 million   | 10.07%  | MIT       |
| English    | Tiny             | 26 million   | 12.66%  | MIT       |
| Korean     | Tiny             | 26 million   | 6.46%   | Community |
| Ukrainian  | Base             | 58 million   | 14.55%  | Community |

† No-space character error rate, not word error rate.

Korean and Ukrainian default to their non-streaming Community models because no streaming checkpoint exists yet; their scores are older full-FLEURS figures and not comparable to the streaming rows.

**Deprecated** (Community license, still load if you name the architecture; use the streaming model in new code): Arabic Base, Japanese Base, Japanese Tiny, Mandarin Base, Spanish Base, Vietnamese Base. Their scores are in the verbatim source doc and are not comparable to the streaming figures.

Architecture names seen in code: `ModelArch.TINY_STREAMING` (Python), `ModelArch.MediumStreaming` (JavaScript), `--model-arch tiny_streaming` / `small_streaming` / `medium_streaming` (scripts). The full list of `ModelArch` values is in the C API constants ([c-api](../reference/c-api/SKILL.md)).

## Latency: Moonshine vs Whisper

Average time from end of speech to final transcript (lower is better):

| Model                      | WER    | # Parameters | MacBook Pro | Linux x86 | R. Pi 5   | Pixel 10a | iPad (A16) |
| -------------------------- | ------ | ------------ | ----------- | --------- | --------- | --------- | ---------- |
| Moonshine Medium Streaming | 6.65%  | 245 million  | 59ms        | 269ms     | 802ms     | 420ms     | 174ms      |
| Whisper Large v3           | 7.44%  | 1.5 billion  | 11,286ms    | 16,919ms  | N/A       | —         | —          |
| Moonshine Small Streaming  | 7.84%  | 123 million  | 38ms        | 165ms     | 527ms     | 234ms     | 95ms       |
| Whisper Small              | 8.59%  | 244 million  | 1940ms      | 3,425ms   | 10,397ms  | —         | —          |
| Moonshine Tiny Streaming   | 12.00% | 34 million   | 18ms        | 69ms      | 237ms     | 92ms      | 37ms       |
| Whisper Tiny               | 12.81% | 39 million   | 277ms       | 1,141ms   | 5,863ms   | —         | —          |

A responsive voice interface aims for under 200ms. Notes on these numbers:

- The Mac, Pixel and iPad cells are medians of three runs; single runs vary (Medium Streaming on the Mac: 56-83ms).
- The Linux x86 and Raspberry Pi 5 columns predate a build-optimization fix and read pessimistically.

**When to pick Moonshine:** live speech. Whisper always encodes a 30-second window (wasted work on short phrases), caches nothing between repeated calls on a growing sentence, has poor accuracy in many languages at edge sizes, and has fragmented edge support. Moonshine has flexible input windows (any length, best under about 30 seconds), caches encoder and decoder state for streaming, uses per-language models, and runs one API across platforms. Medium Streaming beats Whisper Large v3 on the Open ASR Leaderboard with about a sixth of the parameters.

**When Whisper (or alternatives like Parakeet) may fit better:** bulk offline transcription on cloud GPUs, where throughput and batching matter more than per-phrase latency.

## Accuracy details

Quantization costs little. English LibriSpeech `test-clean` WER, whole-utterance, VAD disabled:

| Model            | Paper (float) | Reproduced float (HF Transformers) | Shipped quantized model (this library) |
| ---------------- | ------------- | ---------------------------------- | -------------------------------------- |
| Tiny Streaming   | 4.49%         | 4.52%                              | 4.83%                                  |
| Small Streaming  | 2.49%         | 2.55%                              | 2.61%                                  |
| Medium Streaming | 2.08%         | 2.16%                              | 2.17%                                  |

Compare like with like. These are three different measurements: English Open ASR averages (the models table), English LibriSpeech-clean (above), and the non-English 400-clip panels. The paper's English numbers are for floating-point models in Hugging Face Transformers; the library ships 8-bit quantized `.ort` files. There is no longer much reason to run the floating-point checkpoint for accuracy.

Disable the VAD when evaluating pre-segmented clips: on LibriSpeech or FLEURS, the default VAD adds roughly 1.5-2% WER on Tiny.

### Reproduce the accuracy numbers

From a checkout of the Moonshine repo:

```bash
# Core dependencies for evaluating the shipped (quantized) models.
pip install moonshine-voice datasets soundfile scipy jiwer openai-whisper

# English streaming models on LibriSpeech test-clean (VAD disabled).
python scripts/eval-librispeech.py --backend moonshine_c --model-arch tiny_streaming
python scripts/eval-librispeech.py --backend moonshine_c --model-arch small_streaming
python scripts/eval-librispeech.py --backend moonshine_c --model-arch medium_streaming

# Quick FLEURS check for another language (400 seeded clips).
python scripts/eval-librispeech.py --language ar --model-arch tiny_streaming --quick
```

- `--quick` is a 400-clip single-set slice: a sanity check, not a reproduction of the two-set panels.
- Float reference: `pip install "transformers>=5.13" torch`, then `--backend hf`.
- `--enable-vad` measures with the segmenter; `--backend moonshine_c_streaming` measures the chunked real-time path; `--limit N` runs a smoke test; `--all-streaming --quick` runs every published streaming model.
- The script sets `max_tokens_per_second` automatically from `--language`.

## Benchmark on your own hardware

The core library's benchmark simulates live audio by feeding a WAV in chunks:

```bash
cd core
mkdir -p build
cd build
cmake ..
cmake --build . --config Release
./benchmark
```

It reports total processing time, that time as a percentage of the audio's duration (20% means a fifth of your compute goes to speech), and average latency from end of speech to final transcript. Defaults: Tiny English and `test-assets/two_cities.wav`. Options: `--model-path`, `--model-arch`, `--wav-path`, `--transcription-interval` (default 0.5s; longer saves a little compute but updates less often).

Other scripts:

- [`scripts/run-benchmarks.py`](https://github.com/moonshine-ai/moonshine/blob/main/scripts/run-benchmarks.py) (Python platforms): downloads models itself and also benchmarks Whisper (faster-whisper, CPU) on the same VAD-segmented phrases. Pass your own audio with `--wav_path`.
- [`scripts/test-mobile-latency.sh`](https://github.com/moonshine-ai/moonshine/blob/main/scripts/test-mobile-latency.sh): the Mac, Pixel and iPad latency measurement (averages `lastTranscriptionLatencyMs` over completed lines).

## Research papers

- [Moonshine: Speech Recognition for Live Transcription and Voice Commands](https://arxiv.org/abs/2410.15608): first generation, flexible-duration input windows.
- [Flavors of Moonshine: Tiny Specialized ASR Models for Edge Devices](https://arxiv.org/abs/2509.02523): monolingual models for better non-English accuracy.
- [Moonshine v2: Ergodic Streaming Encoder ASR for Latency-Critical Speech Applications](https://arxiv.org/abs/2602.12241): the streaming approach.

## Source docs

Verbatim copies, for details not covered above:

- [models/index.md](references/models-index.md)
- [models/available-models.md](references/models-available-models.md)
- [models/accuracy.md](references/models-accuracy.md)
- [using/benchmarks.md](references/using-benchmarks.md)
- [moonshine-vs-whisper.md](references/moonshine-vs-whisper.md)
