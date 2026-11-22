---
name: reference
description: 'API reference for Moonshine Voice: the high-level classes, the option keys accepted by the transcriber, TTS, G2P and embedding entry points, and the C API that every language binding wraps. Use when looking up an exact class, method, option name, default, C function, struct or error code rather than learning a task.'
---

# Reference

Lookup tables for the Moonshine Voice API, for when you need an exact name, default, signature or error code rather than a walkthrough. Task-oriented guides are the sibling skills listed in the [root skill](../SKILL.md).

| You need | Open |
| --- | --- |
| A class's constructor, setters, callbacks, methods or exceptions (`Transcriber`, `MicTranscriber`, `Stream`, `TranscriptEventListener`, `AgentFlow`, `Dialog`, `TextToSpeech`, `GraphemeToPhonemizer`, `EmbeddingModel`) | [classes](classes/SKILL.md) |
| An option key and its default, for a transcriber, TTS, G2P, speech-clip extract, download manifest, or the CLI's `--options` | [options](options/SKILL.md) |
| A C function signature, struct field, constant, error code, flag, or memory-ownership rule | [c-api](c-api/SKILL.md) |

The layers stack: the bindings' classes wrap the C API, and options pass straight through as string name/value pairs. A key in [options](options/SKILL.md) works the same in Python's `options={...}`, `MicTranscriber.options()`, Swift/Java `TranscriberOption` pairs, JavaScript's `options` record, and C's `moonshine_option_t` arrays.

Naming across bindings follows each language's casing: Python `push_text()` / `on_text()` is `pushText()` / `onText()` in Swift, Java and JavaScript. Exceptions (e.g. Android's `waitUntilDone()` for `wait()`) are noted in [classes](classes/SKILL.md).

## Subskills

Read the one that matches your task:

- [classes](classes/SKILL.md): Reference for the Moonshine Voice high-level classes and their methods: `Transcriber`, `MicTranscriber`, `Stream`, `TranscriptEventListener`, `AgentFlow`, `Dialog`, `TextToSpeech`, `GraphemeToPhonemizer` and `EmbeddingModel`. Use when checking a class's constructor, methods, callbacks, events or return types in Python or the other bindings.
- [options](options/SKILL.md): Reference for the Moonshine Voice option keys and their defaults: shared options (`log_api_calls`, `ort_providers`, `coreml_cache_dir`, `g2p_root`), speech to text options (`vad_threshold`, `vad_max_segment_duration`, `transcription_interval`, `word_timestamps`, `identify_speakers`, `diarization_*`, `keyterms`, `context`, `max_tokens_per_second`, `save_input_wav_path`, `return_audio_data`), text to speech options (`voice`, `speed`, Kokoro, Piper, ZipVoice and Phonon overrides), grapheme to phoneme, embedding and speech-clip options, and the download manifest options. Use when setting or tuning an option passed to a transcriber, TTS, G2P or CLI `--options`.
- [c-api](c-api/SKILL.md): Reference for the Moonshine Voice C API (`moonshine-c-api.h`) that all language bindings wrap: constants (version, model architectures, error codes, flags), structs (`moonshine_option_t`, `transcript_t`, `transcript_line_t`, `transcript_word_t`, `speaker_span_t`, `moonshine_speech_clip_t`), and functions for loading transcribers (`moonshine_load_transcriber_from_files()`), streaming (`moonshine_create_stream()`, `moonshine_transcribe_add_audio_to_stream()`, `moonshine_transcribe_stream()`), embeddings, speech clips, text to speech (`moonshine_text_to_speech()`), grapheme to phonemes and model download manifests. Use when calling Moonshine from C or C++, writing or debugging a language binding, or checking an error code.
