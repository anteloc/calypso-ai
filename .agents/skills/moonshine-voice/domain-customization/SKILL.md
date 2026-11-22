---
name: domain-customization
description: Improving speech to text accuracy for a domain's vocabulary. Covers runtime biasing with a key-terms list or a free-form context passage (`keyterms`, `keyterm_boost`, `context`, `context_max_terms`, `set_keyterms`, `set_context`, `moonshine_transcriber_set_keyterms()`, `moonshine_transcriber_set_context()`), tuning and measuring it and its costs, retraining a domain adapter (`pip install 'moonshine-voice[finetune]'`, worked air traffic control examples, your own data, shipping the result, pitfalls), and how the shipped models are quantized. Use when names, jargon or product terms are misrecognized, or when fine-tuning or quantizing a Moonshine model.
---

# Domain Customization

Make Moonshine speech to text better at a particular domain. There are two tools. **Runtime context** (a key-terms list, or a passage to pick terms from) needs no training, can change mid-stream, and helps with words the model can already spell: product names, jargon, contacts. **Retraining** (a small LoRA adapter) teaches conventions, accents, dialects and acoustic environments. They compose. Setting up a transcriber is covered in [transcription](../transcription/SKILL.md).

## Runtime context

Up to a 40% reduction in errors on the targeted words, with no latency cost and a very small impact on general accuracy. **Streaming architectures only**: the older Tiny and Base models raise an error.

### Key terms list (when you know the words)

```python
from moonshine_voice import Transcriber, ModelArch

transcriber = Transcriber(
    model_path,
    ModelArch.TINY_STREAMING,
    options={"keyterms": "Kubernetes,Ceph,etcd"},
)

# ...or follow whatever the user is looking at, mid-stream:
transcriber.set_keyterms(["Anushka Sharma", "Jurgen Klopp"])
```

- Write terms with the capitalization and spelling you want in the output; that is what gets produced.
- Terms can be multi-word phrases. A list is more precise than a passage: nothing is inferred and no slots are wasted.
- At load time, `keyterms` is a plain comma-separated string. `set_keyterms()` replaces the list and takes a list of terms in languages that have one; it applies from the next transcription.

### Context passage (when you have text but no list)

```python
from moonshine_voice import Transcriber, ModelArch

transcriber = Transcriber(
    model_path,
    ModelArch.TINY_STREAMING,
    options={"context": open("migration-plan.md").read()},
)

# ...or follow the document as the user moves through it:
transcriber.set_context(current_page_text)
```

- Terms are picked by the model's own tokenizer: words that need more than one subword (jargon, proper nouns). From a passage about migrating services, Tiny Streaming picks `Migration`, `Kubernetes`, `Ceph`, `etcd` and `ingress`. It follows the loaded model's language automatically.
- Terms are ranked by frequency in the passage, then capped: 200 by default, or `context_max_terms` at load / the second argument to `set_context()` (0 means the default). Keep the cap modest; passing a book is fine because of it.
- Capitalization comes from the passage.
- Only single words are proposed, and words containing digits are skipped. Name multi-word names ("Anushka Sharma") and digit words ("IPv6") with `keyterms` alongside the passage; both sets are used.

### Across bindings

| | Load option | Replace at runtime |
| --- | --- | --- |
| Python | `options={"keyterms": ..., "keyterm_boost": ..., "context": ..., "context_max_terms": ...}` | `set_keyterms()`, `set_context()` |
| Swift, Java | `TranscriberOption` name/value pairs | `setKeyterms()`, `setContext()` |
| JavaScript | the `options` record | `setKeyterms()`, `setContext()` |
| C | options array of `moonshine_load_transcriber_from_files()` / `moonshine_load_transcriber_from_memory_files()` | `moonshine_transcriber_set_keyterms()`, `moonshine_transcriber_set_context()` |

On `MicTranscriber`, pass the load options through `options()` and call `set_keyterms()` / `set_context()` after `load()`.

### Tuning `keyterm_boost`

Each term's subwords go in a prefix tree; during decoding, tokens continuing a path get a logit bonus of `boost * (1 + ln(depth))`, so finishing a term is rewarded more than starting one. The boost is a dial between accuracy on your terms and on every other word:

| Boost | Effect (100-term lists, LibriSpeech-based test) |
| --- | --- |
| 1.0 | A sixth to a fifth fewer term errors, no measurable cost elsewhere. Gentlest on long lists. |
| **2.0 (default)** | About a quarter fewer term errors, at most a quarter point worse elsewhere. |
| 3.0 | About a third fewer term errors, a quarter to six tenths of a point worse elsewhere. Use when the list matters more. |
| 4.0 | Small further gain on terms; cost elsewhere climbs fast. Only for a *short* list you expect to hear. |
| > 4.0 | Broken: the decoder finishes terms nobody said; false alarms run 30-40x the default. Never use. |

Per-model numbers (word error rate on terms / on other words):

| Boost       | Tiny: terms / other | Small: terms / other | Medium: terms / other |
| ----------- | ------------------- | -------------------- | --------------------- |
| 0 (off)     | 13.02% / 6.84%      | 9.69% / 4.70%        | 7.89% / 3.90%         |
| 1           | 10.99% / 6.76%      | 8.27% / 4.74%        | 6.29% / 3.89%         |
| 2 (default) | 10.09% / 7.11%      | 7.06% / 4.85%        | 5.58% / 3.93%         |
| 3           | 8.92% / 7.47%       | 5.97% / 4.98%        | 5.07% / 4.28%         |
| 4           | 8.68% / 8.41%       | 5.71% / 5.47%        | 4.94% / 4.57%         |
| 6           | 15.80% / 17.05%     | 11.74% / 12.40%      | 14.05% / 11.07%       |

### Long lists

Length costs accuracy separately from the boost, and the two multiply. Tiny Streaming WER on LibriSpeech test-clean, biased toward words never spoken (baseline 4.83%):

| Key terms | Boost 1.0 | Boost 2.0 (default) | Boost 4.0 |
| --------- | --------- | ------------------- | --------- |
| 1         |           | 4.84%               |           |
| 10        | 4.83%     | 4.86%               | 5.21%     |
| 100       | 4.91%     | 5.37%               | 10.22%    |
| 1,000     | 5.06%     | 5.88%               | 13.35%    |
| 10,000    | 5.17%     | 6.09%               | 13.66%    |

Lists in the thousands are usable at or below the default. Don't raise the boost on a long list.

### Time cost

Almost nothing per utterance: 100 terms add about 1ms on Tiny on an iPad (A16), and 10,000 terms with the bonus disabled add 3-4ms a phrase. Setting a list tokenizes every term once: 10,000 terms take about 30ms on a MacBook Pro. Swapping terms mid-stream is cheap.

### Measure on your own data

```bash
python scripts/make-keyterm-testset.py --output-dir /tmp/keyterm-testset
python scripts/eval-keyterm-biasing.py \
    --manifest /tmp/keyterm-testset/manifest-100.jsonl \
    --boosts 0,1,2,4
```

These scripts are in the Moonshine repo. `eval-keyterm-biasing.py` reports both halves, term recall and false-alarm rate. It also takes your own manifest (`{"audio": ..., "text": ..., "keyterms": [...]}` per line, see [`keyterm-eval-example.jsonl`](https://github.com/moonshine-ai/moonshine/blob/main/scripts/data/keyterm-eval-example.jsonl)). Pad short lists with `--distractors-file` to the size you will really send: false alarms scale with live terms.

### Limits

Key terms only nudge the decoder toward spellings the tokenizer can produce. They do not help with a new accent, dialect or recording environment. The measurements are for single-word terms in read English; rerun the sweep for multi-word or unusual terms.

## Retraining a domain adapter

Default: a rank-8 LoRA on the decoder's self-attention q/k/v (about 0.11% of Streaming Medium), folded back into the base weights. Inference is unchanged: same `Transcriber`, no extra layers or latency. Decoder LoRA teaches **conventions** (e.g. ATC phraseology, `four six five two` instead of `4652`), not vocabulary and not a new microphone. Recover rare names with key terms afterwards.

Install the opt-in trainer (pulls in PyTorch and Transformers; `[lora]` is the same):

```bash
pip install 'moonshine-voice[finetune]'
```

The CLI is `python -m moonshine_voice.lora` (alias `moonshine-voice finetune`); `--help` lists every flag. A measured walkthrough is the [Colab notebook](https://colab.research.google.com/github/moonshine-ai/moonshine/blob/main/examples/python/finetune/moonshine_lora_domain_adaptation.ipynb).

### Train on your own data

A JSONL manifest, one clip per line (JSON `{"utterances": [...]}` and `path<TAB>text` TSV also work; any `soundfile` format, resampled to 16 kHz mono):

```json
{"audio": "clips/001.wav", "text": "lufthansa four six five two"}
{"audio": "clips/002.wav", "text": "turn right heading two one zero"}
```

```bash
python -m moonshine_voice.lora \
    --train-manifest domain.jsonl \
    --eval-manifest domain_test.jsonl \
    --eval --canary \
    --output-dir ./lora_out
```

Needs a GPU (the two-hour ATCOSIM run on Medium takes about 15 minutes on an RTX 5090 and peaks under 3 GB of GPU memory, so it fits a Colab T4). Writes `adapter.safetensors` and a merged `adapted/` checkpoint.

| Flag | Default | Notes |
| --- | --- | --- |
| rank | 8 | |
| `--sites` | `decoder` | `both` also wraps encoder self-attention; the cheap adapter for real radio audio. |
| `--adapt full` | | Unfreezes the backbone; the ceiling. Writes no `adapter.safetensors`. Not a T4 job on Medium. |
| `--lr` | `1e-3` (decoder), `1e-4` (with encoder), `1e-5` (full) | `1e-3` on the encoder or full NaNs on Medium. |
| batch | 8 | |
| replay | 50% from yodas-en-replay | `--no-replay` buys nothing in-domain and hurts general speech. |
| `--text-mode auto` | | Lowercases a corpus that is more than 90% uppercase. |

Match transcript style to the model (cased, punctuated English) unless the convention is what you want to teach.

### Built-in worked examples

```bash
# ATC phraseology (ATCOSIM: close-talk headset, not radio)
python -m moonshine_voice.lora --dataset atcosim --output-dir ./lora_atc
# Real VHF radio (UWB-ATCC, CC BY-NC-SA 4.0: research only)
python -m moonshine_voice.lora --dataset uwb_atcc --sites both \
    --eval --eval-dataset atco2 --canary --output-dir ./lora_vhf
```

ATCOSIM adapter on Streaming Medium: ATC WER 50.7% → 26.3%, LibriSpeech 2.3% → 2.8%. UWB decoder LoRA: held-out VHF (ATCO2) 82.2% → 59.6%. ATCOSIM is not redistributable: for anything you ship, get it from [TU Graz](https://www.spsc.tugraz.at/databases-and-tools/atcosim-air-traffic-control-simulation-speech-corpus.html). `--prepare-only` indexes a corpus without training.

### Ship the adapter

```bash
python -m moonshine_voice.lora --export \
    --model ./lora_out/adapted --output-dir ./float \
    --tokenizer-bin /path/to/published/tokenizer.bin
bash scripts/quantize-streaming-model.sh ./float
```

- Decoder-only adapter: only `decoder_kv` changes, so `--graphs decoder_kv` plus the published `.ort` files for the other four graphs is enough. With `--sites encoder|both` or `--adapt full`, use `--graphs all`.
- Load the directory with `Transcriber` from the normal wheel: no `[finetune]` extra, no adapter code at runtime.
- Then add the domain's word list with `set_keyterms` / `set_context`.

### Retraining pitfalls

- Orthography mismatch (e.g. an ALL-CAPS corpus) silently wastes the adapter.
- Hold out whole speakers or sessions, not random utterances.
- Always score a general-domain canary (`--canary`); in-domain WER alone can't tell adaptation from damage.
- Don't train on ATCO2 mixes (`jlvdoorn/atco2-asr` overlaps the ATCO2 test hour).
- The `[finetune]` extra pins `transformers>=5.15`.

## Quantization notes

Shipped models use 8-bit post-training quantization (ONNX Runtime tools plus [Onnx Shrink Ray](https://pypi.org/project/onnx-shrink-ray/)), with convolution frontends kept at B16 float or better. If you quantize your own Moonshine-style model:

- Give **each output channel of a weight its own scale factor**. Per-channel scales took Tiny Streaming from 7.57% to 4.83% WER on LibriSpeech test-clean (Small 3.03% → 2.61%, Medium 2.37% → 2.17%), mostly from the frontend.
- Don't fold the weight normalization out of the exported graph unless you also use per-channel scales.
- The frontend ships split: `frontend.model.ort` (float compute graph) and `frontend.weights.ort` (int8 tensors plus dequant), dequantized once at load. A leftover single-file `frontend.ort` still loads.
- The options used are in [scripts/quantize-streaming-model.sh](https://github.com/moonshine-ai/moonshine/blob/main/scripts/quantize-streaming-model.sh).

Re-quantized models are published to a new dated CDN directory (currently `quantized_26_11_02`), so a library version always resolves the weights it was tested with.

## Source docs

Verbatim copies, for details not covered above:

- [models/domain-customization.md](references/models-domain-customization.md)
- [models/quantization.md](references/models-quantization.md)
