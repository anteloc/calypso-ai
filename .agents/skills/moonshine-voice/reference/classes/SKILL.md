---
name: classes
description: 'Reference for the Moonshine Voice high-level classes and their methods: `Transcriber`, `MicTranscriber`, `Stream`, `TranscriptEventListener`, `AgentFlow`, `Dialog`, `TextToSpeech`, `GraphemeToPhonemizer` and `EmbeddingModel`. Use when checking a class''s constructor, methods, callbacks, events or return types in Python or the other bindings.'
---

# Classes

Compact reference for the Moonshine Voice high-level classes, in Python naming. Other bindings use their own casing (`on_text` → `onText`, `push_text` → `pushText`); exceptions are noted inline. For full parameter text, read the verbatim copy in [references/api-classes.md](references/api-classes.md). For how to use them, see [transcription](../../transcription/SKILL.md), [voice-agent](../../voice-agent/SKILL.md) and [text-to-speech](../../text-to-speech/SKILL.md).

Builder classes (`MicTranscriber`, `AgentFlow`, `TextToSpeech`) share one shape: a no-argument constructor that cannot fail, chainable setters that each return the object and have a working default (call them before `load()`), a blocking `load()` that downloads what is missing, then use, then `close()` (also a context manager).

## Transcriber

The speech to text pipeline, fed audio by you.

| Member | Notes |
| --- | --- |
| `Transcriber(model_path, model_arch, update_interval, options)` | `model_path` is the model **folder**, not a file. `model_arch` comes from `ModelArch`. `options`: string-keyed map, see [options](../options/SKILL.md). Raises if the model isn't found. |
| `transcribe_without_streaming(audio_data, sample_rate, flags)` | Non-live audio (a file). Mono float32 PCM in -1.0..1.0; resampled to 16kHz internally. Only flag: `MOONSHINE_FLAG_SPELLING_MODE`. Still calls listeners. |
| `start()` | Begins a session. Call before adding audio. |
| `stop()` | Ends the session; completes any active line. |
| `add_audio(audio_data, sample_rate)` | Mono float32 chunk, any size and rate. |
| `update_transcription(flags)` | Returns the full transcript. Cached if under 200ms of new audio unless `MOONSHINE_FLAG_FORCE_UPDATE`. |
| `create_stream(flags, update_interval)` | Returns a `Stream`. Several inputs share one loaded model; each stream has its own transcript; events are tagged with their stream. |
| `add_listener(listener)` / `remove_listener(listener)` / `remove_all_listeners()` | Listener is a `TranscriptEventListener` subclass or a plain function. |
| `set_keyterms(keyterms)` | Bias towards terms (no commas in a term); replaces the previous list; `None`/empty turns it off. Strength via `keyterm_boost` at load. Streaming architectures only. |
| `set_context(context, max_terms=200)` | Pick key terms out of a passage; same semantics. Streaming architectures only. |

## MicTranscriber

Transcribes the system microphone (Python uses [`sounddevice`](https://python-sounddevice.readthedocs.io/); other languages use the native audio API).

| Setter | Default / notes |
| --- | --- |
| `language()` | `"en"` |
| `model_arch()` | The catalog's recommended model (medium streaming for English) |
| `models_from()` | Load from your directory instead of downloading |
| `use_transcriber()` | Reuse an existing `Transcriber`; it stays yours to close |
| `update_interval()` | `0.5` seconds |
| `options()` | Dict of [transcriber options](../options/SKILL.md) |
| `spelling_model()` | Your own spelling model; `load()` finds the published one by itself; `None` for none |
| `transcribe_flags()` | Flags for every streaming update, e.g. `MOONSHINE_FLAG_SPELLING_MODE`; immediate if loaded |
| `device()` | Input device by index or name; system default |
| `samplerate()` | `16000`; `start()` falls back to the device's own rate |
| `channels()` | `1` |
| `blocksize()` | `1024` frames per capture callback |

| Callback / method | Notes |
| --- | --- |
| `on_text(text)` | In-progress text of the current line, on each change |
| `on_line(line)` | Once per finished line ([`transcript_line_t`](../c-api/SKILL.md) fields) |
| `on_error()` | The audio or transcription pipeline raised |
| `on_progress(fraction, file)` | Download progress `0..1`; silences the default terminal bars |
| `add_listener()` | For line ids, speaker spans, word timings, line start. Listeners added before `load()` are applied once the stream exists |
| `load()` | Download if needed, open, return self. Blocking; safe to call twice |
| `set_keyterms()` / `set_context()` | As on `Transcriber`; call after `load()`. To start with them, pass `keyterms` / `context` via `options()` |
| `start()` | Open the mic and transcribe. Raises without `load()` |
| `mute()` | Drop audio without closing the mic (so an assistant doesn't transcribe itself) |
| `stop()` | Stop and flush, so the last line completes |
| `close()` | Release mic, stream and model |

## Stream

One of several audio inputs into a single `Transcriber`. Supports `start()`, `stop()`, `add_audio()`, `update_transcription()`, `add_listener()`, `remove_listener()`, `remove_all_listeners()` as on `Transcriber`.

## TranscriptEventListener

Subclass and override any of `on_line_started()`, `on_line_updated()`, `on_line_text_changed()`, `on_line_speakers_changed()`, `on_line_completed()`, `on_error()`. All default to no-ops.

## AgentFlow

Runs generator-based conversational flows; the entry point for voice interfaces. Completed lines go to trigger matching when no flow is active, or to the suspended flow when one is. Matching is semantic via an embedding model downloaded on first need. `load()` opens the mic transcriber and synthesizer itself. It never closes a synthesizer or transcriber it didn't create.

| Setter | Default / notes |
| --- | --- |
| `language()` | `"en"`, for recognition and speech |
| `model_arch()` | STT model size |
| `voice()` | Synthesis voice |
| `speech_options()` | Dict of [TTS options](../options/SKILL.md) for the `TextToSpeech` |
| `models_from()` | Cache models under this directory |
| `microphone()` | `True`; off to drive it with `handle_utterance()` |
| `speech()` | `True`; off for a silent runner (prompts logged, flows still advance) |
| `output_device()` | Pin playback device |
| `trigger_threshold()` | `0.7` similarity (0..1) to fire |
| `use_embeddings()` | `True`; off = case-insensitive substring match, no model (good for offline tests) |
| `beeps()` | `True`; "got it" / "didn't get that" tones |
| `spell_feedback()` | `True`; echo each spelled character |
| `barge_in()` | Off; enable only with reliable echo cancellation |
| `log_io()` | Off; logs `user: ...` / `assistant: ...` to stderr |
| `debug()` | Trace internal stages with timings to stderr |
| `on_progress(fraction, name)`, `on_heard()`, `on_said()`, `on_error()` | Download progress; every utterance received; every prompt spoken; errors (default: print to stderr; a raising flow is torn down) |
| `speak_with(callable)` | Your own speech function; must block until playback ends; no synthesizer created |
| `use_text_to_speech()` / `use_mic_transcriber()` | Reuse your own `TextToSpeech` / `MicTranscriber` (or any object with `add_listener`/`start`/`stop`, e.g. a file-fed `Transcriber`) |

| Method / property | Notes |
| --- | --- |
| `listen_for(trigger_phrase, flow)` | Start `flow(dialog)` when speech means the same as the phrase (cosine similarity) |
| `unregister_flow(trigger_phrase)` | Returns `True` if removed |
| `always(trigger_phrase, handler)` | Live at all times; `handler(dialog)` returns an optional prompt, may call `d.cancel()` / `d.restart()`. "Cancel" and "start over" are built in for active flows |
| `otherwise(handler)` | `handler(utterance)` for speech nothing claimed (dictation); silences the "didn't get that" cue |
| `load()` | Open matcher, synthesizer and mic transcriber (skips supplied or disabled ones). Blocking |
| `start_listening()` / `stop_listening()` | Start returns once the mic is live; calls `load()` if needed |
| `handle_utterance(utterance)` | Route text manually; `True` if consumed |
| `cancel()` | Abandon the running flow |
| `say(text)` | Speak outside a flow; blocks until played |
| `say_stream()` | Context manager yielding `push(text)`; each sentence plays as it completes |
| `close()` | Stop and release what it opened; idempotent |
| `is_active`, `active_trigger`, `registered_flows` | Read-only state |

## Dialog

Passed to every flow. Each method returns a prompt the flow `yield`s; the runner performs it and `.send()`s back the result. `Dialog` does no I/O, so flows can be unit-tested by driving the generator by hand. Properties: `trigger_phrase`, `state` (a per-conversation `dict`).

| Method | Yields back | Defaults / raises |
| --- | --- | --- |
| `say(text, barge_in)` | `None` | `barge_in` reserved |
| `say_stream(pieces, barge_in)` | `None` | Errors in `pieces` go to `on_error()`, flow continues |
| `ask(prompt, mode, bias_terms, timeout, no_input_reprompt, max_retries)` | `str` | `mode`: `FREE` (default), `SPELLED`, `DIGITS`, `PHRASE` (exported from `moonshine_voice`). `timeout` 8s, `max_retries` 2, then `NoInputError`. `bias_terms` currently ignored. `no_input_reprompt` template uses `{prompt}`; `None` skips |
| `confirm(prompt, timeout, max_retries)` | `bool` | Semantic yes/no. `timeout` 6s, `max_retries` 1, then `NoMatchError` |
| `choose(prompt, options, timeout, max_retries)` | option key `str` | `options`: key → list of phrases. `timeout` 8s, `max_retries` 2, then `NoMatchError` |
| `cancel()` | | Raises `DialogCancelled` into the flow |
| `restart()` | | Raises `DialogRestart` into the flow |
| `replay_last_prompt()` | | `Say` prompt re-speaking the last question, or `None` |

## TextToSpeech

On-device synthesis (Kokoro, Piper, ZipVoice vocoders plus per-language G2P). Errors: `MoonshineTtsLanguageError` (bad language), `MoonshineTtsVoiceError` (missing/unknown voice), `MoonshineAudioOutputError` (playback, lists output devices when it can). Discover with `list_tts_languages()`, `list_tts_voices()`, `get_tts_voice_catalog()`.

```python
tts = TextToSpeech().language("en_us").voice("kokoro_af_heart")
tts.load()
tts.say("Hello from Moonshine.")
tts.wait()
```

| Setter | Notes |
| --- | --- |
| `language()` | e.g. `en_us`, `de`, `fr`; `en-us` normalized; default `"en"` |
| `voice()` | Catalog id with vocoder prefix (`kokoro_`, `piper_`, `zipvoice_`); clears `cloning()` |
| `models_from(dir, download=False)` | Pre-populated dir; `download=True` uses it as cache root |
| `cloning()` | ZipVoice cloning engine; fetches clone assets at `load()`; clears `voice()` |
| `options()` | [TTS options](../options/SKILL.md) |
| `output_device()` | PortAudio index or name substring |
| `volume()`, `on_progress()`, `debug()` | Playback gain; download progress; trace to stderr |

| Method / property | Notes |
| --- | --- |
| `load()` | Blocking download and prepare; repeat calls are no-ops |
| `language_tag`, `asset_root`, `is_cloned` | Read-only |
| `clone_from(source, transcript=None)` | `source`: `.wav` path, `(pcm, sample_rate)`, or `VoiceClone`. Needs `cloning()` |
| `start_cloning(clip_duration_seconds=4.0, minimum_speech_seconds=2.0)` | Capture from mic; returns `VoiceClone` |
| `synthesize(text, options)` | Returns `(samples, sample_rate)`; only `speed` honored per call |
| `say(text, device, options)` | Non-blocking, queued. Python needs `pip install numpy sounddevice`. On Android `device` is a `Context` (required) plus optional `AudioDeviceInfo` |
| `say_stream(device, options)` | Speak text still being produced; push with `push_text()`. `sayStream()` on Swift/Android |
| `stream(text=None)` | Iterate chunks (samples, rate, text, utterance id, end flag) instead of playing |
| `push_text(text)`, `flush()`, `end_input()`, `cancel_stream()` | Streaming input; only complete sentences are synthesized until `flush()` / `end_input()` |
| `is_streaming`, `next_chunk()` | `synthesize()` and `say()` refuse while streaming |
| `stop()` | Clear queue, stop playback |
| `wait()` | Block until all played. `waitUntilDone()` on Android |
| `is_talking()` | `isTalking()` on Swift/Android |
| `close()` | Release the handle; also via `with TextToSpeech() as tts:` |

## GraphemeToPhonemizer

IPA without synthesis.

| Member | Notes |
| --- | --- |
| `GraphemeToPhonemizer(language, options, asset_root, download=True)` | `download=False` requires a populated `asset_root` |
| `language`, `asset_root` | Read-only |
| `to_ipa(text, options)` | Returns one IPA string |
| `close()` | Also on context exit |

## EmbeddingModel

Low-level text embeddings. Prefer `AgentFlow` for phrase matching in apps.

| Member | Notes |
| --- | --- |
| `EmbeddingModel(model_path, model_arch, model_variant="q4")` | Directory with the embedding `.ort` and `tokenizer.bin` (Python gets it from `get_embedding_model()`). `model_arch` from `EmbeddingModelArch` (only Gemma 300M). Python, Swift, Java |
| `load(model_name, variant="q4")` | Download and return an instance (e.g. `embeddinggemma-300m`). JavaScript and Swift. Java uses `getEmbeddingDependencies()` plus `AssetDownloader` |
| `calculate_embedding(sentence)` | `calculateEmbedding()` outside Python |
| `distance(a, b)` | Cosine similarity in `[-1, 1]` |
| `close()` | Free the handle |

## Source docs

Verbatim copies, for details not covered above:

- [api/classes.md](references/api-classes.md)
