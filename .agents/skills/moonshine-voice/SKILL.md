---
name: moonshine-voice
description: 'Moonshine Voice, an open source on-device toolkit for real-time voice apps: streaming speech to text, text to speech, voice cloning, speaker identification, semantic command recognition and conversational agents, with no API keys or GPU. Covers installing it (pip `moonshine-voice` / `import moonshine_voice`, npm `@moonshine-ai/moonshine-wasm`, Swift package `MoonshineVoice`, Maven `ai.moonshine:moonshine-voice`, prebuilt C/C++ libraries), the `moonshine-voice` CLI (`mic`, `transcribe`, `tts`, `agent`, `download`, `g2p`), the builder-and-callback pattern (`MicTranscriber().language(...).on_text(...).on_line(...)`, `load()`, `start()`), naming across Python, JavaScript, Swift and Java, and the platform examples. Use when a task mentions Moonshine, `moonshine_voice`, on-device or offline speech recognition or synthesis, or building a voice interface, and as the entry point to the subskills.'
---

# Moonshine Voice

Moonshine Voice is an open source toolkit for real-time voice apps. Everything runs on-device: no account, API keys or GPU. One library gives you streaming speech to text, text to speech, voice cloning, speaker identification (diarization), command recognition and conversational agents, on Python, JavaScript/WASM, iOS, macOS, Android, Linux, Windows and Raspberry Pi. This skill covers what every task needs: installing it, the usage pattern shared by all classes, the CLI, and where to find examples. Open a subskill for the task itself.

## Mental model

- **High-level, event-driven classes.** You build an object, attach callbacks, `load()` it, then `start()` it. The API is the same across languages; the docs use Python to illustrate.
- **Models are fetched for you.** `MicTranscriber`, `TextToSpeech` and `AgentFlow` download what they need on first `load()` into a local cache, then run offline. `load()` blocks on that first download. To bundle models or stay fully offline, see [downloading-models](downloading-models/SKILL.md).
- **Streaming first.** The framework and models are tuned for live audio, doing work while the user is still talking. In-progress text arrives through one callback, finished lines through another.
- **One C core.** Every binding (Python, Swift, Java/Android, JavaScript/WASM, the header-only C++ wrapper) calls the same C API, so option names and behaviour match across platforms.

Languages: English, Spanish, German, Mandarin, Japanese, Korean, Vietnamese, Tagalog, Ukrainian and Arabic for STT; English, Spanish, Arabic, German, French, Hindi, Italian, Japanese, Korean, Dutch, Portuguese, Russian, Turkish, Ukrainian, Vietnamese and Mandarin for TTS.

## Canonical pattern

Live microphone transcription in Python:

```python
from moonshine_voice import MicTranscriber

mic = (
    MicTranscriber()
    .language("en")
    .on_text(lambda text: print(text, end="\r", flush=True))
    .on_line(lambda line: print(line.text))
)
mic.load()
mic.start()
```

`on_text` fires whenever the in-progress line changes; `on_line` fires once per finished line. Details are in [transcription](transcription/SKILL.md).

### Naming across languages

The builder methods are the same everywhere, in each language's casing:

| Python | JavaScript | Swift | Java (Android) |
| --- | --- | --- | --- |
| `MicTranscriber()` | `new MicTranscriber()` | `MicTranscriber()` | `new MicTranscriber(this)` |
| `.on_text(...)` | `.onText(...)` | `.onText { ... }` | `.onText(...)` |
| `.on_line(...)` | `.onLine(...)` | `.onLine { ... }` | `.onLine(...)` |
| `.model_arch(...)` | `.modelArch(ModelArch.MediumStreaming)` | | |
| `mic.load()` / `mic.start()` | `await mic.load()` / `await mic.start()` | `try await mic.load()` / `try mic.start()` | `mic.load()` / `mic.start()` (on a worker thread) |

JavaScript:

```js
import { MicTranscriber, ModelArch } from 'https://cdn.jsdelivr.net/npm/@moonshine-ai/moonshine-wasm/dist/index.js';

const mic = new MicTranscriber()
  .modelArch(ModelArch.MediumStreaming)
  .onText((text) => showInProgress(text))
  .onLine((line) => appendLine(line.text, line.lastTranscriptionLatencyMs));

await mic.load();
await mic.start();
```

Swift (identical on iOS and macOS):

```swift
import MoonshineVoice

let mic = MicTranscriber()
    .onText { [weak self] text in
        Task { @MainActor in self?.liveText = text }
    }
    .onLine { [weak self] line in
        Task { @MainActor in self?.lines.append(line.text) }
    }

try await mic.load()
try mic.start()
```

Android (Java):

```java
import ai.moonshine.voice.MicTranscriber;

mic = new MicTranscriber(this)
        .onText(text -> transcriptText.setText(finishedLines + text))
        .onLine(line -> {
            finishedLines.append(line.text).append('\n');
            transcriptText.setText(finishedLines.toString());
        });

worker.execute(() -> {
    mic.load();
    mic.start();
});
```

## Install

| Platform | How | Import |
| --- | --- | --- |
| Python (desktop, Raspberry Pi) | `pip install moonshine-voice` ([PyPI](https://pypi.org/project/moonshine-voice/)) | `import moonshine_voice` |
| JavaScript (Node, bundler) | `npm install @moonshine-ai/moonshine-wasm` | `import { MicTranscriber, ModelArch } from '@moonshine-ai/moonshine-wasm';` |
| JavaScript (browser, no install) | CDN | `import { ... } from 'https://cdn.jsdelivr.net/npm/@moonshine-ai/moonshine-wasm/dist/index.js';` |
| iOS / macOS | Swift Package Manager: add `https://github.com/moonshine-ai/moonshine-swift/` in Xcode ("Add Package Dependencies...") | `import MoonshineVoice` |
| Android | Maven `ai.moonshine:moonshine-voice` (e.g. `0.1.6`) | `import ai.moonshine.voice.MicTranscriber;` |
| Linux (x86_64, arm64) | Prebuilt shared library from [GitHub Releases](https://github.com/moonshine-ai/moonshine/releases/latest), via `examples/c++/download-library.sh` | `#include "moonshine-cpp.h"` |
| Windows | Raw library and headers via [`download-lib.bat`](https://github.com/moonshine-ai/moonshine/blob/main/examples/windows/cli-transcriber/download-lib.bat) | `#include "moonshine-cpp.h"` |

Platform notes:

- **Raspberry Pi:** the same pip package, optimized for the Pi. Plug in a USB microphone. If pip warns about system packages, use a virtual environment or `pip install --break-system-packages moonshine-voice`.
- **iOS / macOS:** add any model files you use to the app bundle and make sure they are copied during deployment.
- **Android (Gradle version catalog):** in `gradle/libs.versions.toml` add `moonshineVoice = "0.1.6"` under `[versions]` and `moonshine-voice = { group = "ai.moonshine", name = "moonshine-voice", version.ref = "moonshineVoice" }` under `[libraries]`. Then add `implementation(libs.moonshine.voice)` to `dependencies` in `app/build.gradle.kts`.
- **Linux:** `download-library.sh` extracts `moonshine-voice/` with headers in `include/` and `libmoonshine.so` (plus its ONNX Runtime dependency) in `lib/`. Compile with:

  ```bash
  g++ your_app.cpp \
    -Imoonshine-voice/include \
    -Lmoonshine-voice/lib \
    -lmoonshine \
    -Wl,-rpath,'$ORIGIN/moonshine-voice/lib' \
    -o your_app
  ```

- **Windows:** add the `include` folder to the include search paths, the `lib` folder to the library search paths, and every file in `lib` to the linker dependencies. The recommended interface is the header-only C++ binding, `moonshine-cpp.h`, which is higher level than the C API.

No prebuilt binary for your target? See [building-from-source](building-from-source/SKILL.md).

## Command-line tools

The pip package installs a `moonshine-voice` command (alias `moonshine`). It is meant for one-off use; for repeated calls, load the models once from Python instead.

| Command | Description |
| --- | --- |
| `moonshine-voice mic` | Transcribe live microphone input to the terminal. |
| `moonshine-voice transcribe` | Transcribe a WAV file (optionally with speaker IDs / word timestamps). |
| `moonshine-voice tts` | Synthesize speech from text to a WAV file or audio device. |
| `moonshine-voice agent` | Run a spoken agent flow (wifi setup) from the microphone. |
| `moonshine-voice download` | Download STT, TTS, G2P, or embedding model assets. |
| `moonshine-voice g2p` | Convert text to phonemes (IPA). |

```bash
moonshine-voice mic --language en
moonshine-voice agent
moonshine-voice tts --language en_us --text "Hello world"
```

Run `moonshine-voice <command> --help` for each command's options. Each subcommand equals running its module: `moonshine-voice mic --language en` is the same as `python -m moonshine_voice.mic_transcriber --language en`.

## Examples

Live demos run in the browser at [moonshine.ai](https://moonshine.ai/). Code samples are in the repo's [`examples`](https://github.com/moonshine-ai/moonshine/tree/main/examples) folder, and [GitHub Releases](https://github.com/moonshine-ai/moonshine/releases/latest) ship ready-to-run archives, mostly named `{platform}-{Project}.tar.gz`.

| Platform | Samples |
| --- | --- |
| JavaScript | `web-stt`, `web-tts`, `web-agent-flow`, `web-dictation`, `web-meeting-notes`. Extract, run `node serve.mjs`, open [http://localhost:8080/](http://localhost:8080/). |
| Python ([`examples/python/`](https://github.com/moonshine-ai/moonshine/blob/main/examples/python/)) | `basic_transcription.py` (WAV file, offline or streaming), `mic_transcription.py`, `text_to_speech.py` (optional cloned voice), `agent_flow.py` (wifi setup by voice or keyboard), `ollama-voice/ollama_voice.py` (mic transcripts into a local [Ollama](https://ollama.com/) LLM), `finetune` (domain adapter, see [domain-customization](domain-customization/SKILL.md)). |
| iOS | `ios-Transcriber`, `ios-TextToSpeech`, `ios-AgentFlow` (Xcode projects). |
| Android | `android-Transcriber`, `android-TextToSpeech`, `android-AgentFlow` (open the folder in Android Studio). |
| macOS | `macos-BasicTranscription`, `macos-MicTranscription`, `macos-TextToSpeech`, `macos-AgentFlow` (optional `--text` mode). |
| Linux / C++ | `cpp-examples.tar.gz` with `transcriber.cpp` (stream a WAV, print the transcript), `text-to-speech.cpp` (text to WAV) and `download-library.sh`. |
| Windows | `windows-cli-transcriber`: self-contained Visual Studio project with library, model and sample WAV. Build with F7 or Ctrl+Shift+B. |
| Raspberry Pi | `raspberry-pi-my-dalek` (voice commands), [Pi Help Bot](https://github.com/moonshine-ai/pi-help-bot) (a more advanced assistant). |

Quick C++ run on Linux:

```bash
curl -O -L https://github.com/moonshine-ai/moonshine/releases/latest/download/cpp-examples.tar.gz
tar xzf cpp-examples.tar.gz
cd c++
./download-library.sh
g++ transcriber.cpp -Imoonshine-voice/include -Lmoonshine-voice/lib -lmoonshine -Wl,-rpath,'$ORIGIN/moonshine-voice/lib' -o transcriber
./transcriber
```

No sample bundles model weights. Each engine downloads what it needs on first use from `https://download.moonshine.ai/` (the speech model for `Transcriber`, the voice and G2P assets for `TextToSpeech`, all three plus the embedding model for `AgentFlow`), reports progress through `onProgress`, and caches it (under `filesDir` on Android, `Caches/MoonshineModels` on Apple platforms). For a fully offline build, fetch assets ahead of time and pass the path to `modelsFrom(path)`.

## Which subskill

| Task | Subskill |
| --- | --- |
| Transcribe a microphone, WAV file or custom audio stream; partial vs final lines; speaker IDs, word timestamps | [transcription](transcription/SKILL.md) |
| Names or jargon are misrecognized; bias with key terms; fine-tune an adapter | [domain-customization](domain-customization/SKILL.md) |
| Voice commands, intent matching, multi-step spoken conversations, LLM replies | [voice-agent](voice-agent/SKILL.md) |
| Make the app speak, clone a voice, get phonemes | [text-to-speech](text-to-speech/SKILL.md) |
| Pick a model size or language model; accuracy and latency; Moonshine vs Whisper | [choosing-a-model](choosing-a-model/SKILL.md) |
| Bundle models, run offline, control the cache, load from files or memory | [downloading-models](downloading-models/SKILL.md) |
| Poor results, odd audio, failing calls | [debugging](debugging/SKILL.md) |
| Build the core with CMake, port to a new platform | [building-from-source](building-from-source/SKILL.md) |
| Exact classes, option keys, C functions and error codes | [reference](reference/SKILL.md) |

## Coding agents

The Moonshine repo ships its own agent skill at [`.agents/skills/moonshine-voice/`](https://github.com/moonshine-ai/moonshine/tree/main/.agents/skills/moonshine-voice) (or `npx skills add moonshine-ai/moonshine --skill moonshine-voice`), described by its authors as the happy path for integrating the library. Live support is on [Discord](https://discord.gg/27qp9zSRXF).

## Subskills

Read the one that matches your task:

- [transcription](transcription/SKILL.md): Speech to text with Moonshine Voice: live microphone transcription with `MicTranscriber` (`language()`, `on_text()`, `on_line()`, `on_progress()`, `model_arch()`, `models_from()`, `load()`, `start()`, `stop()`, `close()`), and feeding your own audio (WAV files, custom capture, multiple streams) with `Transcriber`, `Stream` and `TranscriptEventListener`, plus the transcript event flow (line started, updated, text changed, completed) and transcript lines, word timestamps and speaker IDs. Use when transcribing a microphone, a file or an audio stream, handling partial versus final lines, or running `moonshine-voice mic` / `moonshine-voice transcribe`.
- [domain-customization](domain-customization/SKILL.md): Improving speech to text accuracy for a domain's vocabulary. Covers runtime biasing with a key-terms list or a free-form context passage (`keyterms`, `keyterm_boost`, `context`, `context_max_terms`, `set_keyterms`, `set_context`, `moonshine_transcriber_set_keyterms()`, `moonshine_transcriber_set_context()`), tuning and measuring it and its costs, retraining a domain adapter (`pip install 'moonshine-voice[finetune]'`, worked air traffic control examples, your own data, shipping the result, pitfalls), and how the shipped models are quantized. Use when names, jargon or product terms are misrecognized, or when fine-tuning or quantizing a Moonshine model.
- [voice-agent](voice-agent/SKILL.md): Building spoken conversational agents with `AgentFlow` and `Dialog`: registering semantically matched conversation starters with `listen_for()`, generator-based multi-step and branching flows, `yield d.say(...)`, asking questions with `d.ask(...)`, yes/no confirmations with `d.confirm(...)`, spelled input, error handling, speaking a reply while it is written with `d.say_stream(...)`, and agent setup with `start_listening()`. Use when building a voice assistant, voice commands or intent recognition, a spoken multi-step flow (like the wifi-setup example), piping transcripts to an LLM, or running `moonshine-voice agent`.
- [text-to-speech](text-to-speech/SKILL.md): Speech synthesis with Moonshine Voice `TextToSpeech`: choosing a language and voice (Kokoro, Piper, ZipVoice, Phonon voices via `kokoro_`, `piper_`, `zipvoice_`, `phonon_` ids), speaking or synthesizing text, streaming text in as it is generated (`push_text()`, `end_input()`), zero-shot voice cloning (`cloning()`, `clone_from()`), voice samples, and converting graphemes to phonemes (IPA) with `GraphemeToPhonemizer`. Use when making an app speak, generating WAV audio from text, cloning a voice, getting phonemes, or running `moonshine-voice tts` / `moonshine-voice g2p`.
- [choosing-a-model](choosing-a-model/SKILL.md): Picking a Moonshine speech to text model: the available models per language and architecture (Tiny, Small, Medium Streaming and deprecated non-streaming ones), parameter counts, licenses (MIT vs Moonshine Community License), word error rates (LibriSpeech, FLEURS, Open ASR Leaderboard, float vs quantized), latency benchmarks across devices, and how Moonshine compares with Whisper for live speech. Use when choosing a model size or architecture (`model_arch()`, `ModelArch`) for a language or device, comparing accuracy or latency, reproducing the accuracy numbers, or deciding between Moonshine and Whisper.
- [downloading-models](downloading-models/SKILL.md): Getting Moonshine model files: automatic download and caching on first `load()` (where files go, `on_progress()`), the opt-in downloader for staging files into your own directory or warming a cache before going offline, `moonshine-voice download`, and the speech to text, embedding and text to speech model files per platform, plus the HuggingFace `safetensors` checkpoints and the `moonshine-voice-assets` mirror. Use when bundling models with an app, running offline, controlling the model cache location, loading models from files, assets or memory, or finding a model's files.
- [debugging](debugging/SKILL.md): Diagnosing Moonshine Voice problems: reading the console logs and exceptions from the core library, saving the audio a transcriber receives to WAV files with the `save_input_wav_path` option, and tracing the call timeline with the `log_api_calls` option (e.g. `moonshine-voice transcribe --options='log_api_calls=true'`). Use when transcription quality is poor, audio input seems wrong, calls fail, or ordering and timing issues need investigating.
- [building-from-source](building-from-source/SKILL.md): Building the Moonshine Voice core library from source with CMake, building the language bindings, and porting the library to a new platform. Use when no prebuilt binary fits the target, when changing the C++ core, or when bringing Moonshine to a new OS, architecture or language binding.
- [reference](reference/SKILL.md): API reference for Moonshine Voice: the high-level classes, the option keys accepted by the transcriber, TTS, G2P and embedding entry points, and the C API that every language binding wraps. Use when looking up an exact class, method, option name, default, C function, struct or error code rather than learning a task.

## Source docs

Verbatim copies, for details not covered above:

- [index.md](references/index.md)
- [quickstart.md](references/quickstart.md)
- [using/index.md](references/using-index.md)
- [using/adding-the-library.md](references/using-adding-the-library.md)
- [examples.md](references/examples.md)
