---
name: downloading-models
description: 'Getting Moonshine model files: automatic download and caching on first `load()` (where files go, `on_progress()`), the opt-in downloader for staging files into your own directory or warming a cache before going offline, `moonshine-voice download`, and the speech to text, embedding and text to speech model files per platform, plus the HuggingFace `safetensors` checkpoints and the `moonshine-voice-assets` mirror. Use when bundling models with an app, running offline, controlling the model cache location, loading models from files, assets or memory, or finding a model''s files.'
---

# Downloading Models

Get Moonshine's model files: let the high-level classes download them on first use, warm the cache before going offline, stage files into a directory you control, or bundle them with the app. Choosing which model to use is in [choosing-a-model](../choosing-a-model/SKILL.md).

## Automatic download (the default)

`MicTranscriber`, `TextToSpeech` and `AgentFlow` fetch what they need on first `load()` and cache it, so later launches run offline. Most apps never call a download API. Attach `on_progress()` to drive a UI (in Python this also silences the default terminal progress bars):

```python
from moonshine_voice import MicTranscriber

mic = (
    MicTranscriber()
    .language("en")
    .on_progress(lambda fraction, file: print(f"{fraction:.0%} {file}"))
    .on_text(lambda text: show_in_progress(text))
    .on_line(lambda line: append_line(line.text))
)
mic.load()
mic.start()
```

`AgentFlow` needs the speech model, TTS voice, G2P assets and an embedding model. Switching to a different voice downloads what that voice needs.

| Platform | Cache location |
| --- | --- |
| Python (incl. Linux, Windows, Raspberry Pi) | User cache directory, e.g. `~/Library/Caches/moonshine_voice` on macOS. Override with the `MOONSHINE_VOICE_CACHE` environment variable. |
| Browser (JavaScript) | Cache Storage bucket `moonshine-models-v1`. Append `?fresh=1` to a demo URL during development to clear it. |
| Apple platforms | `Caches/MoonshineModels` |
| Android | under `filesDir` |

## Use files you already have

Point the engine at a directory, and it never touches the network:

- **Python:** `models_from(path)` on `MicTranscriber`, `TextToSpeech`, `AgentFlow`; or `Transcriber(model_path=...)`. `TextToSpeech.models_from(dir, download=True)` uses the directory as the cache root and fetches anything missing.
- **JavaScript:** `modelsFrom` or a custom `baseUrl` when you host the assets yourself instead of using the CDN.
- **C++ (Linux, Windows):** run `moonshine-voice download` (or `./download-library.sh` in `examples/c++`, which fetches a sample English model too, or use the models bundled in the Windows release archive), then pass that directory to the engine.
- **iOS / macOS:** add model files to the app bundle and make sure they are copied at deployment.

## Warm the cache or stage files: the CLI

Use the `moonshine-voice download` command (from the pip package) before shipping a device that will be offline, or to get a directory to pass to `Transcriber`.

### Speech to text

```bash
moonshine-voice download --stt --language en
```

- `--language` takes the two-letter code or the English name. Pass a bogus value (e.g. `foo`) to list supported languages.
- `--model-arch` picks a specific architecture by number from [moonshine-c-api.h](https://github.com/moonshine-ai/moonshine/blob/main/core/moonshine-c-api.h). Without it, the highest-quality model is downloaded.
- The alphanumeric spelling model (`spelling_cnn.ort`, `spelling_cnn_meta.json`) comes along when one is published for the language.

The last lines of output give the architecture and the path to pass to `Transcriber`:

```text
Model download url: https://download.moonshine.ai/model/medium-streaming-en/quantized_26_11_02
Model components: ['adapter.ort', 'cross_kv.ort', 'decoder_kv.ort', 'encoder.ort', 'frontend.model.ort', 'frontend.weights.ort', 'streaming_config.json', 'tokenizer.bin']
Model arch: 5
Downloaded model path: /Users/petewarden/Library/Caches/moonshine_voice/download.moonshine.ai/model/medium-streaming-en/quantized_26_11_02
```

Here no architecture was requested, so it fetched Medium Streaming (architecture 5).

### Embedding model

Used for semantic phrase matching. `AgentFlow` fetches it itself; to use vectors directly, pass the directory to `EmbeddingModel` ([classes](../reference/classes/SKILL.md)).

```bash
moonshine-voice download --embedding
```

It downloads `embeddinggemma-300m` (`model_q4.ort`, about 189MB, plus `tokenizer.bin`) and prints its path.

### Text to speech

```bash
moonshine-voice download --tts --root /tmp/tts-files/
```

Pull exactly what a language (and optionally a voice) needs; run `moonshine-voice download --help` for the flags. It prints `TTS assets root (use as g2p_root): ...`.

- Files go in child folders under the root, at the relative paths TTS expects, so the engine finds them from the root alone.
- To move individual files, pass `options()` to `TextToSpeech` before `load()`, with the usual relative path as key and the real path as value.
- If the app can be installed anywhere, set the `tts_root` option at runtime to the real root folder.

## Opt-in downloader API (mobile and native)

For explicit control, the bindings expose a downloader built on the same dependency catalog as the Python CLI. It resolves file lists from the native catalog (no hardcoded filenames), writes files atomically through a `.part` file, resumes interrupted transfers with HTTP `Range`, checks free space, and reports per-file progress. You pick the destination: STT and embedding files use bare filenames; TTS/G2P files keep relative paths (e.g. `en_us/dict.tsv`).

### iOS / macOS (Swift)

`AssetDownloader.ensureModelPresent` fetches anything missing under your directory and returns it. It is `async`; call it off the main actor.

```swift
import MoonshineVoice

let modelDir = URL.cachesDirectory.appending(path: "moonshine/tiny-en")

// Speech-to-text: download the default English model (add includeSpelling: true for the
// alphanumeric spelling model, or pass modelArch: to pick a specific architecture).
let downloader = AssetDownloader(allowsCellularAccess: false)  // Wi-Fi only
try await downloader.ensureModelPresent(root: modelDir, spec: .stt(language: "en")) { progress in
    print("\(progress.relativePath): \(progress.bytesDownloaded)/\(progress.bytesTotal)")
}
let transcriber = try Transcriber(modelPath: modelDir.path, modelArch: .tiny)

// Text embeddings (the embeddinggemma-300m model is large — a few hundred MB even at q4):
try await downloader.ensureModelPresent(root: embeddingDir, spec: .embedding(variant: "q4"))

// Text to speech (files land under the directory you pass as g2p_root):
try await downloader.ensureModelPresent(root: ttsRoot, spec: .tts(language: "en_us", voice: "kokoro_af_heart"))
```

- `isModelPresent(root:spec:)` is a cheap synchronous check to skip the download UI.
- Failures throw `AssetDownloadError` (HTTP status, insufficient space, cancellation, ...), distinct from later load failures.
- No `Info.plist` entries or permissions needed for HTTPS.

### Android (Java)

The Android `AssetDownloader` mirrors the Swift API with blocking I/O: run it off the main thread. For background downloads that survive process death, respect network constraints and retry with backoff, use `MoonshineDownloadWorker` (WorkManager).

```java
File modelDir = new File(context.getFilesDir(), "moonshine/tiny-en");

// Direct (call from a background thread / coroutine):
File root = new AssetDownloader().ensureModelPresent(
        modelDir, ModelSpec.stt("en"),
        (path, index, total, done, size) -> Log.i("dl", path + " " + done + "/" + size));
Transcriber transcriber = new Transcriber();
transcriber.loadFromFiles(root.getAbsolutePath(), JNI.MOONSHINE_MODEL_ARCH_TINY);

// Or via WorkManager, downloading only over unmetered (e.g. Wi-Fi) connections:
OneTimeWorkRequest request =
        MoonshineDownloadWorker.buildRequest(modelDir, ModelSpec.stt("en"), /*requireUnmetered=*/ true);
WorkManager.getInstance(context).enqueue(request);
```

- `ModelSpec` factories: `stt(language)`, `tts(language, voice)`, `embedding(modelName, variant)`, `g2p(language)`.
- The library manifest declares `INTERNET` and `ACCESS_NETWORK_STATE`; they merge automatically.
- Observe worker progress with `WorkInfo.getProgress()` and the worker's `PROGRESS_*` keys.
- The downloader pulls in OkHttp and WorkManager transitively, even for apps that bundle models.

The download manifest functions in the C API (`moonshine_get_stt_dependencies()`, ...) are in [c-api](../reference/c-api/SKILL.md).

## Where the files come from

- Runtime downloads come from the CDN at `https://download.moonshine.ai/`. Re-quantized models go to new dated directories (e.g. `quantized_26_11_02`), so a library version always gets the weights it was tested with.
- [huggingface.co/moonshine-ai/moonshine-voice-assets](https://huggingface.co/moonshine-ai/moonshine-voice-assets) mirrors exactly the files the download manifests reference, in the CDN's folder layout (a repo path equals the path under `download.moonshine.ai`). Its `FILES.tsv` lists each file's size and checksum, and each library version is a tag (`v` plus the version). It is for archival and verification; the library still downloads from the CDN.
- Floating-point `safetensors` checkpoints (from the training pipeline) are linked from [huggingface.co/moonshine-ai/models](https://huggingface.co/moonshine-ai/models). The org was formerly `UsefulSensors`; old links no longer resolve.

## Source docs

Verbatim copies, for details not covered above:

- [using/downloading-models.md](references/using-downloading-models.md)
- [models/huggingface.md](references/models-huggingface.md)
