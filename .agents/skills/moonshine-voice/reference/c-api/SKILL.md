---
name: c-api
description: 'Reference for the Moonshine Voice C API (`moonshine-c-api.h`) that all language bindings wrap: constants (version, model architectures, error codes, flags), structs (`moonshine_option_t`, `transcript_t`, `transcript_line_t`, `transcript_word_t`, `speaker_span_t`, `moonshine_speech_clip_t`), and functions for loading transcribers (`moonshine_load_transcriber_from_files()`), streaming (`moonshine_create_stream()`, `moonshine_transcribe_add_audio_to_stream()`, `moonshine_transcribe_stream()`), embeddings, speech clips, text to speech (`moonshine_text_to_speech()`), grapheme to phonemes and model download manifests. Use when calling Moonshine from C or C++, writing or debugging a language binding, or checking an error code.'
---

# C API

Compact reference for the Moonshine C API in [`core/moonshine-c-api.h`](https://github.com/moonshine-ai/moonshine/blob/main/core/moonshine-c-api.h), the portable ABI that Python, Swift, Java/Android, JavaScript/WASM and the C++ wrapper (`moonshine-cpp.h`) all call into. Use it directly when writing a new binding, embedding Moonshine in C or C++, or when you need the lowest-level control over handles, buffers and model loading. Application code should prefer the bindings ([classes](../classes/SKILL.md)). Full argument tables are in [references/api-c-api.md](references/api-c-api.md).

## Conventions

- **Thread-safe.** Work on one transcriber is serialized: concurrent calls on the same handle queue behind each other.
- **Handles** are opaque `int32_t`: non-negative on success, negative error codes on failure. Other calls return `0` / `MOONSHINE_ERROR_NONE` on success. Convert any code with `moonshine_error_to_string()`.
- **Versioning:** pass `MOONSHINE_HEADER_VERSION` as `moonshine_version` to loaders so a newer shared library emulates the header you compiled against. `moonshine_get_version()` returns the loaded library's version.
- **Options** are `moonshine_option_t` arrays of string name/value pairs, plus a count. Keys are in [options](../options/SKILL.md).
- **Audio** in: mono float PCM in -1.0..1.0 at any `sample_rate` (16 kHz internally, so capture at 16 kHz to avoid resampling). Audio out of transcripts: 16 kHz mono.
- **Freeing a freed handle's id:** freed transcriber and stream ids may be reused by later creates; drop all references after freeing.

### Memory ownership

| Memory | Owner / release |
| --- | --- |
| `transcript_t` from `moonshine_transcribe_stream()` / `moonshine_transcribe_without_streaming()` | Transcriber. Valid until the next call on that transcriber or until it is freed. Copy what you keep. |
| `tts_chunk_t` from `moonshine_tts_next_chunk()` | Synthesizer. Valid until the next call on it. Do not free. |
| String from `moonshine_transcript_to_string()` | Library. Valid until the next call to it. |
| `out_audio_data` (TTS), `out_phonemes`, every `out_*_json`, `moonshine_speech_clip_t.audio_data` / `.transcript` | malloc'd: release with `moonshine_free_buffer()` (never the C runtime `free`: on Windows the host may use a different CRT heap). NULL-safe. |
| `out_embedding` | Release with `moonshine_free_embedding()`. |
| Model buffers passed to `*_from_memory*` loaders | Not copied (must outlive the transcriber / synthesizer / phonemizer), except `moonshine_create_embedding_model_from_memory()`, which copies. |

## Constants

| Constant | Value |
| --- | --- |
| `MOONSHINE_HEADER_VERSION` | `30000` (3.0.0; `MAJOR * 10000 + MINOR * 100 + PATCH`) |
| `MOONSHINE_FROM_MEMORY_REMOVED_VERSION` | `30000` |
| `MOONSHINE_MODEL_ARCH_TINY` / `_BASE` | `0` / `1` |
| `MOONSHINE_MODEL_ARCH_TINY_STREAMING` / `_BASE_STREAMING` | `2` / `3` |
| `MOONSHINE_MODEL_ARCH_SMALL_STREAMING` / `_MEDIUM_STREAMING` | `4` / `5` |
| `MOONSHINE_EMBEDDING_MODEL_ARCH_GEMMA_300M` | `0` |
| `MOONSHINE_ERROR_NONE` / `_UNKNOWN` / `_INVALID_HANDLE` / `_INVALID_ARGUMENT` / `_BUSY` | `0` / `-1` / `-2` / `-3` / `-4` |
| `MOONSHINE_TTS_NEED_TEXT` / `_END_OF_STREAM` / `_CANCELLED` | `1` / `2` / `3` (positive: streaming-synthesis statuses, not errors) |
| `MOONSHINE_FLAG_FORCE_UPDATE` | Ignore the ~200ms caching window in `moonshine_transcribe_stream()`. |
| `MOONSHINE_FLAG_SPELLING_MODE` | Alphanumeric-spelling fusion on completed lines (needs a spelling model; otherwise ignored). Line `text` becomes the resolved character, e.g. `"a"` or `"$"`. |

## Data structures

**`transcript_t`**: `lines` (`transcript_line_t *`), `line_count`. Reset whenever a stream starts fresh or a one-shot transcription runs.

**`transcript_line_t`** (one speech segment; may be updated many times while the user talks):

| Member | Meaning |
| --- | --- |
| `text` | UTF-8 text. `""` = speech detected, nothing transcribed. |
| `audio_data`, `audio_data_count` | The phrase's audio, 16 kHz mono. |
| `start_time`, `duration` | Seconds. |
| `id` | Stable random 64-bit id. Don't rely on ordering. |
| `is_complete` | Set once the segment ends; then text and timing never change. |
| `is_updated`, `is_new`, `has_text_changed` | Dirty flags from the last update call. Prefer binding events over polling them. |
| `have_speakers_changed` | Speaker spans revised (can be set on completed lines). |
| `speaker_spans`, `speaker_span_count` | NULL unless `identify_speakers` is on. |
| `last_transcription_latency_ms` | End of speech → final transcript, in ms. |
| `words`, `word_count` | NULL / 0 unless `word_timestamps` is on. |

Streaming guarantees: lines are only added, never removed; only the last line may be incomplete; line indexes are stable.

**`transcript_word_t`**: `text`, `start`, `end` (seconds), `confidence` (0..1). Needs `word_timestamps` (implied by `identify_speakers`).

**`speaker_span_t`**: `start_time`, `duration`, `speaker_id` (`uint64_t`, stable per speaker within a stream), `speaker_index` (order of first appearance, from 0), `start_char` / `end_char` (UTF-8 byte offsets into the line text; both zero when not yet aligned). Spans within `diarization_cluster_window_sec` (default 120s) can still move, merge, split or change speaker; older ones are frozen.

**`moonshine_speech_clip_t`**: `audio_data` (16 kHz mono, NULL unless complete), `audio_length`, `start_time`, `speech_duration`, `is_complete`, `transcript` (set when clone ASR refined the clip).

**`moonshine_option_t`**: `name`, `value` (both `const char *`).

**`tts_chunk_t`**: `audio_data`, `audio_data_count`, `sample_rate`, `text`, `utterance_id` (from 1), `is_final` (last chunk of the utterance).

## Utilities

| Function | Notes |
| --- | --- |
| `int32_t moonshine_get_version(void)` | Loaded library version. |
| `const char *moonshine_error_to_string(int32_t error)` | Human-readable error. |
| `void moonshine_free_buffer(void *ptr)` | Free library-allocated buffers. |
| `const char *moonshine_transcript_to_string(const struct transcript_t *transcript)` | Debug string. |

## Speech to text

| Function | Notes |
| --- | --- |
| `moonshine_load_transcriber_from_files(path, model_arch, options, options_count, moonshine_version)` | `path` = model directory. Returns a transcriber handle. |
| `moonshine_load_transcriber_from_memory_files(filenames, memory, memory_sizes, file_count, model_arch, options, options_count, moonshine_version)` | In-memory assets keyed by canonical filename. A NULL / zero-size entry loads that filename from disk. Unknown names → `MOONSHINE_ERROR_INVALID_ARGUMENT`; extra recognized files are fine, so a whole model directory works. |
| `moonshine_load_transcriber_from_memory(...)` | **Deprecated**, non-streaming only; refused for `moonshine_version >= MOONSHINE_FROM_MEMORY_REMOVED_VERSION`. |
| `void moonshine_free_transcriber(transcriber_handle)` | |
| `moonshine_transcriber_set_keyterms(transcriber_handle, const char *keyterms)` | Comma-separated; NULL/empty turns biasing off. Streaming archs only. Applies from the next transcribe call. |
| `moonshine_transcriber_set_context(transcriber_handle, const char *context, int32_t max_terms)` | Terms picked from a passage; `max_terms` 0 = 200. Streaming archs only. |
| `moonshine_transcribe_without_streaming(transcriber_handle, audio_data, audio_length, sample_rate, flags, struct transcript_t **out_transcript)` | Whole buffer at once (files). Only flag: `MOONSHINE_FLAG_SPELLING_MODE`. |

Required model files by architecture:

- Non-streaming (TINY, BASE): `encoder_model.ort`, `decoder_model_merged.ort`, `tokenizer.bin`; plus `decoder_with_attention.ort` (or `alignment_model.ort`) for `word_timestamps`.
- Streaming (`*_STREAMING`): `frontend.ort` (or `frontend.model.ort` + `frontend.weights.ort`), `encoder.ort`, `adapter.ort`, `cross_kv.ort`, `decoder_kv.ort`, `streaming_config.json`, `tokenizer.bin`; plus `decoder_kv_with_attention.ort` for `word_timestamps`.
- Either: optional `spelling_cnn.ort` (and `spelling_cnn_meta.json`); `segmentation.ort` and `embedding.ort` are required with `identify_speakers` (get them via `moonshine_get_diarization_dependencies()`).
- Models must be ORT format; `.onnx` can't be loaded (convert with `scripts/convert-models-to-ort.py`).

## Streaming speech to text

One transcriber can own several streams (one per audio source). Add audio as often as the capture thread likes (`add_audio` only buffers, so it is safe on time-critical threads); call `moonshine_transcribe_stream()` on your own schedule.

```c
int32_t transcriber_handle = moonshine_load_transcriber_from_files(
    "path/to/models", MOONSHINE_MODEL_ARCH_BASE, NULL, 0,
    MOONSHINE_HEADER_VERSION);
int32_t stream_handle = moonshine_create_stream(transcriber_handle, 0);
moonshine_start_stream(transcriber_handle, stream_handle);

float *latest_audio_data;
size_t latest_audio_data_length;
while (get_audio_from_microphone(&latest_audio_data, &latest_audio_data_length)) {
  moonshine_transcribe_add_audio_to_stream(
      transcriber_handle, stream_handle, latest_audio_data,
      latest_audio_data_length, microphone_sample_rate, 0);
  transcript_t *partial_transcript = NULL;
  moonshine_transcribe_stream(
      transcriber_handle, stream_handle, 0, &partial_transcript);
  print_transcript(partial_transcript);
}
moonshine_stop_stream(transcriber_handle, stream_handle);

transcript_t *final_transcript = NULL;
moonshine_transcribe_stream(
    transcriber_handle, stream_handle, 0, &final_transcript);
print_transcript(final_transcript);

moonshine_free_stream(transcriber_handle, stream_handle);
moonshine_free_transcriber(transcriber_handle);
```

| Function | Notes |
| --- | --- |
| `moonshine_create_stream(transcriber_handle, flags)` | Returns a stream handle. Flags: pass 0. |
| `moonshine_free_stream(transcriber_handle, stream_handle)` | |
| `moonshine_start_stream(transcriber_handle, stream_handle)` | Before any `moonshine_transcribe_stream()`. Start/stop allow fresh starts after a break (e.g. mute). |
| `moonshine_stop_stream(transcriber_handle, stream_handle)` | Rejects further audio but keeps unanalyzed audio. Then call `moonshine_transcribe_stream()` to drain it: all lines complete, no force flag needed. |
| `moonshine_transcribe_add_audio_to_stream(transcriber_handle, stream_handle, new_audio_data, audio_length, sample_rate, flags)` | Buffers only. Flags: pass 0. |
| `moonshine_transcribe_stream(transcriber_handle, stream_handle, flags, struct transcript_t **out_transcript)` | Full analysis only after >200ms of new audio unless `MOONSHINE_FLAG_FORCE_UPDATE`. Updated lines are at the end. |

## Embeddings

| Function | Notes |
| --- | --- |
| `moonshine_create_embedding_model(model_path, model_arch, model_variant)` | Directory with the `.ort` and `tokenizer.bin`. `model_variant` `"q4"` (NULL default) or `"q8"`. |
| `moonshine_create_embedding_model_from_memory(model_arch, model_variant, filenames, filenames_count, memory, memory_sizes, options, options_count, moonshine_version)` | Keys like `model_q4.ort`, `tokenizer.bin`. Bytes are copied. Single self-contained `.ort`. |
| `void moonshine_free_embedding_model(handle)` | |
| `moonshine_calculate_embedding(handle, sentence, float **out_embedding, uint64_t *out_embedding_size, model_name)` | `model_name` picks the prompt template (NULL = default). |
| `void moonshine_free_embedding(float *embedding)` | |
| `moonshine_calculate_embedding_distance(handle, embedding_a, embedding_b, embedding_size, float *out_similarity)` | Cosine similarity in [-1, 1]. |

## Speech clips (voice cloning reference)

`moonshine_extract_speech_clip(audio_data, audio_length, sample_rate, tts_synthesizer_handle, options, options_count, struct moonshine_speech_clip_t *out_clip)`: finds the best short speech window (VAD only, cheap). Output is always 16 kHz mono. Success with `is_complete == 0` means not enough speech yet: record more and call again.

## Text to speech

| Function | Notes |
| --- | --- |
| `moonshine_create_tts_synthesizer_from_files(language, filenames, filenames_count, options, options_count, moonshine_version)` | `language` e.g. `"en_us"`. Files resolve relative to `g2p_root`. Pass `voice` etc. in `options`. |
| `moonshine_create_tts_synthesizer_from_memory(language, filenames, filenames_count, memory, memory_sizes, options, options_count, moonshine_version)` | Keys like `kokoro/prosody.model.ort`, `kokoro/voices/af_heart.kokorovoice`, `piper/onnx`, `zipvoice/vocoder.ort`; clone clip as `zipvoice/clone_audio`. NULL entry = load from disk. |
| `void moonshine_free_tts_synthesizer(handle)` | |
| `moonshine_text_to_speech(handle, text, options, options_count, float **out_audio_data, uint64_t *out_audio_data_size, int32_t *out_sample_rate)` | Whole utterance. Only `speed` is honored per call. Returns `MOONSHINE_ERROR_BUSY` while a stream is in flight. |
| `moonshine_phonemes_to_speech(handle, phonemes, options, options_count, out_audio_data, out_audio_data_size, out_sample_rate)` | From an IPA string (as from `moonshine_text_to_phonemes()`), e.g. to fix a name's pronunciation. |
| `moonshine_tts_split_utterances(text, options, options_count, char **out_utterances_json)` | JSON array of the units the synthesizer speaks separately. Options: `language`, `split_on_colon`, `min_codepoints`. |
| `moonshine_get_tts_dependencies(languages, options, options_count, char **out_dependencies_json)` | Merged G2P + vocoder manifest (`groups`). ZipVoice adds a `"role":"clone_asr"` group to download under `g2p_root/clone_asr/`. |
| `moonshine_get_tts_voices(languages, options, options_count, char **out_voices_json)` | `{lang: [{"id": ..., "state": "found" \| "missing"}]}`. Set `g2p_root` for accurate state. |

### Streaming synthesis

No stream object: the calls act on the synthesizer, which speaks one thing at a time. Pull-based and synchronous; threading belongs to the bindings.

```c
int32_t moonshine_tts_push_text(int32_t tts_synthesizer_handle, const char *text);
int32_t moonshine_tts_flush(int32_t tts_synthesizer_handle);
int32_t moonshine_tts_end_input(int32_t tts_synthesizer_handle);
int32_t moonshine_tts_cancel(int32_t tts_synthesizer_handle);
int32_t moonshine_tts_is_streaming(int32_t tts_synthesizer_handle);
int32_t moonshine_tts_next_chunk(int32_t tts_synthesizer_handle, uint32_t flags,
                                 const struct tts_chunk_t **out_chunk);
```

- `push_text` buffers until a complete unit forms (same rules as `moonshine_tts_split_utterances()`); `flush` makes the buffer synthesizable anyway; `end_input` flushes and closes the generation; `cancel` drops buffered text and pending audio (safe when idle).
- `next_chunk` returns `MOONSHINE_ERROR_NONE` (chunk ready), `MOONSHINE_TTS_NEED_TEXT` (push more or flush), `MOONSHINE_TTS_END_OF_STREAM`, or `MOONSHINE_TTS_CANCELLED` (sent once, only if something was discarded).

## Grapheme to phonemes

| Function | Notes |
| --- | --- |
| `moonshine_create_grapheme_to_phonemizer_from_files(language, filenames, filenames_count, options, options_count, moonshine_version)` | Keys like `en_us/dict_filtered_heteronyms.tsv`, `en_us/oov/model.ort`, resolved under `g2p_root` (or the working directory). ORT models only. |
| `moonshine_create_grapheme_to_phonemizer_from_memory(language, filenames, filenames_count, memory, memory_sizes, options, options_count, moonshine_version)` | Register every file the engine needs. Buffers not copied. |
| `void moonshine_free_grapheme_to_phonemizer(handle)` | |
| `moonshine_text_to_phonemes(handle, text, options, options_count, const char **out_phonemes, uint64_t *out_phonemes_count)` | IPA string; free with `moonshine_free_buffer()`. |
| `moonshine_get_g2p_dependencies(languages, options, options_count, char **out_dependencies_json)` | Despite the name, a **comma-separated list** of asset keys. |

## Model download manifests

Ask the library which CDN files a model needs instead of hardcoding layouts. All write a malloc'd JSON string (free with `moonshine_free_buffer()`; NULL on failure).

| Function | Notes |
| --- | --- |
| `moonshine_get_stt_dependencies(language, options, options_count, out_dependencies_json)` | `language` code or English name (not empty). `{"groups":[{"base_url", "files":[{name, url, size, checksum, checksum_type}]}]}`. Options that change files: `model_arch`, `word_timestamps`, `include_spelling`, `spelling_model_path`. |
| `moonshine_get_embedding_dependencies(model_name, options, options_count, out_dependencies_json)` | NULL/empty = default (e.g. `embeddinggemma-300m`). `variant` option. Lists `model_<variant>.ort` and `tokenizer.bin`. |
| `moonshine_get_diarization_dependencies(out_dependencies_json)` | Two files, about 8.2 MB. Required for `identify_speakers` (no longer compiled into the library); point `diarization_model_dir` at them. |
| `moonshine_get_stt_catalog(out_catalog_json)` | `{"languages":[{"code", "english_name", "models":[{"model_arch", "download_url", "is_default"}]}]}` |
| `moonshine_get_embedding_catalog(out_catalog_json)` | `{"models":[{"name", "english_name", "download_url", "variants", "default_variant"}]}` |

## Source docs

Verbatim copies, for details not covered above:

- [api/c-api.md](references/api-c-api.md)
