---
name: options
description: 'Reference for the Moonshine Voice option keys and their defaults: shared options (`log_api_calls`, `ort_providers`, `coreml_cache_dir`, `g2p_root`), speech to text options (`vad_threshold`, `vad_max_segment_duration`, `transcription_interval`, `word_timestamps`, `identify_speakers`, `diarization_*`, `keyterms`, `context`, `max_tokens_per_second`, `save_input_wav_path`, `return_audio_data`), text to speech options (`voice`, `speed`, Kokoro, Piper, ZipVoice and Phonon overrides), grapheme to phoneme, embedding and speech-clip options, and the download manifest options. Use when setting or tuning an option passed to a transcriber, TTS, G2P or CLI `--options`.'
---

# Options

Catalog of the option keys Moonshine constructors accept. Options are a string-to-string map: a Python dict, a `moonshine_option_t` array in C, name/value pairs (`TranscriberOption`) elsewhere. Values are always strings at the ABI; bindings may accept bools and numbers and stringify them. On the CLI, pass them as `--options='key=value'`. The full text of every key, including the long tail of G2P overrides, is in [references/api-options.md](references/api-options.md).

Where each group is passed:

| Group | Passed to |
| --- | --- |
| Speech to text | `Transcriber(..., options=…)`, `MicTranscriber.options()`, `moonshine_load_transcriber_from_files()` / `_from_memory_files()` / deprecated `_from_memory()` |
| Text to speech | `TextToSpeech.options()`, `AgentFlow.speech_options()`, `moonshine_create_tts_synthesizer_from_files()` / `_from_memory()`; also `moonshine_get_tts_dependencies()` / `moonshine_get_tts_voices()` |
| Grapheme to phonemes | `GraphemeToPhonemizer(..., options=…)`, `moonshine_create_grapheme_to_phonemizer_*`, `moonshine_get_g2p_dependencies()` |
| Speech clip extract | `moonshine_extract_speech_clip()` (and the Python `VoiceClone` capture path) |

## Shared options

| Key | Accepted by | Description |
| --- | --- | --- |
| `log_api_calls` | Transcriber, TTS, G2P, speech-clip extract, other C entry points | Log C API entry points and arguments to stderr/console. |
| `ort_providers` (alias `ort_provider`) | Transcriber, TTS, G2P | Comma-separated, ordered ONNX Runtime execution providers, e.g. `CoreML,CPU`. Case-insensitive; short or full names. Unset = CPU-only (recommended). Mobile libraries are CPU-only: requesting another provider there is an error. |
| `coreml_cache_dir` | Transcriber, TTS, G2P | CoreML compiled-model cache on macOS; only with `CoreML` in `ort_providers`. |
| `log_profiling` | TTS, G2P | Log profiling information. |
| `g2p_root` (aliases `path_root`, `model_root`; `tts_root` for TTS) | TTS, G2P, TTS dependency/voice listing | Asset root for G2P and TTS files. Empty = process working directory. |

## Speech to text

| Key | Default | Description |
| --- | --- | --- |
| `skip_transcription` | false | Run VAD/segmentation only; use each line's audio buffer yourself. |
| `max_tokens_per_second` | `6.5` | Truncate pathological decoder loops. Use about `13.0` for many non-Latin languages. |
| `use_speculative_decoding` | true | Streaming: verify the previous hypothesis and continue from the first mismatch. False = greedy redecode from BOS. |
| `keyterms` | (none) | Comma-separated bias terms (streaming only). Runtime: `set_keyterms` / `moonshine_transcriber_set_keyterms()`. |
| `keyterm_boost` | `2.0` | Biasing strength. Towards 4.0 favors the list, towards 1.0 the other words. Broken above 4.0. |
| `context` | (none) | Passage to pick key terms from (streaming only); added to `keyterms`. Runtime: `set_context` / `moonshine_transcriber_set_context()`. |
| `context_max_terms` | `200` | Most terms taken from `context`. Keep modest. |
| `transcription_interval` | `0.5` | Seconds between automatic transcription passes (Python `update_interval`). |
| `vad_threshold` | `0.5` | VAD sensitivity. Lower → longer segments, higher → shorter. `0` disables VAD (audio still chunked by `vad_max_segment_duration`). |
| `vad_window_duration` | `0.5` | Seconds of VAD scores averaged. |
| `vad_hop_size` | `512` | VAD hop size in samples. |
| `vad_look_behind_sample_count` | `8192` | Samples prepended when speech starts (at 16 kHz). |
| `vad_max_segment_duration` | `15` | Max line length in seconds before a forced complete. |
| `save_input_wav_path` | (none) | Folder: save received audio as 16 kHz mono WAVs. |
| `log_ort_run` | false | Log ONNX Runtime runs and timings. |
| `log_output_text` | false | Log STT text to the console. |
| `word_timestamps` | false | Fill each line's `words`. Needs the attention decoder asset. Implied by `identify_speakers`. |
| `decode_incomplete_lines` | true | Decode in-progress lines so text updates while someone talks. False waits for the line to complete. |
| `identify_speakers` | false | Diarization and `speaker_spans`. Needs diarization models ([details](https://github.com/moonshine-ai/moonshine/blob/main/docs/diarization-models.md)). |
| `diarization_model_dir` | (none) | Directory with `segmentation.ort` and `embedding.ort`, when constructing a transcriber directly. |
| `diarization_cluster_cadence` | `2.0` | Min seconds of new audio between re-clustering passes. |
| `diarization_analyze_cadence` | `0` (= `1.0`) | Sliding-window step for segmentation/embedding. |
| `diarization_cluster_window_sec` | `120` | Max recent history for streaming clustering; `0` = unlimited. |
| `return_audio_data` | true | Include per-line PCM in results. |
| `spelling_model_path` | (none) | Spelling-CNN `.ort` for `MOONSHINE_FLAG_SPELLING_MODE`. |

Also accepts the shared `log_api_calls`, `ort_providers`, `coreml_cache_dir`.

## Text to speech

| Key (aliases) | Description |
| --- | --- |
| `voice` | Catalog voice id. Prefix `kokoro_`, `piper_`, `zipvoice_` or `phonon_` selects the vocoder (e.g. `kokoro_af_heart`, `phonon_zoey`). |
| `speed` | Speaking-rate multiplier. The only per-call override honored by `say()` / `synthesize()` / `moonshine_text_to_speech()` / `moonshine_phonemes_to_speech()`. |
| `lang` / `language` | Language tag (usually set via the constructor / `language()`). |
| `normalize_audio` / `piper_normalize_audio` | Peak-normalize then gain/clip (default true). |
| `output_volume` / `piper_output_volume` | Linear gain after normalize (default `1`). |
| `kokoro_dir`, `kokoro_model` / `kokoro_model_onnx`, `kokoro_config` / `kokoro_config_json` | Kokoro directory, model and config overrides. |
| `piper_onnx` / `piper_model_onnx` / `piper_model`, `piper_onnx_json` / ..., `piper_voices_dir` / `voices_dir`, `piper_voices_json_dir` / `voices_json_dir` | Piper model (`.ort`), JSON sidecar and voice directory overrides. |
| `piper_noise_scale`, `piper_noise_w` (and `_override` forms) | Piper inference noise. |
| `zipvoice_clone_sample_rate` / `clone_sample_rate` | Sample rate of a caller-supplied clone clip (default `24000`). |
| `zipvoice_clone_transcript` / `clone_transcript` | Transcript for that clip. |
| `zipvoice_model` / `zipvoice_model_name`, `zipvoice_distill` | `zipvoice` vs distilled (distilled defaults, default true). |
| `zipvoice_num_step` / `num_step` | Diffusion steps; `<=0` → model default. |
| `zipvoice_guidance_scale` / `guidance_scale` | `<0` → model default. |
| `zipvoice_t_shift` / `t_shift` | Default `0.5`. |
| `phonon_temperature` / `temperature` | `0` deterministic; `<0` → default `0.3`. |
| `phonon_seed` / `seed` | Sampling noise seed (default `0`). |
| `phonon_duration_delta` / `duration_delta` | Duration conditioning (positive = slower); replaces the `speed` mapping when set. |
| `phonon_normalize_text` | Typography and number normalization before tokenizing (default true). |
| `phonon_voice_file` / `phonon_voice` | Phonon voice `.safetensors` for the bare `phonon` voice. |
| `output` / `o` | Default WAV path for CLI tooling (default `out.wav`). |
| `engine` / `vocoder_engine` | Accepted but ignored (the `voice` prefix picks the engine). |

Also accepts shared root aliases and ORT keys. Unknown TTS keys are forwarded to the G2P parser. In-memory creation uses file-map keys (e.g. `kokoro/prosody.model.ort`, `zipvoice/clone_audio`, `phonon/voice`) instead of option names; see [c-api](../c-api/SKILL.md).

## Grapheme to phonemes

| Key | Description |
| --- | --- |
| `g2p_root` / `path_root` / `model_root` | Asset root. |
| `use_cuda` | CUDA for G2P ORT sessions. |
| `oov_onnx_override`, `oov_onnx_config` | Override the English OOV model and its `onnx-config.json`. |
| `allow_builtin_g2p_data` | Deprecated; ignored. |
| `<language>_dict_path` (e.g. `english_dict_path`, `german_dict_path`, `japanese_dict_path`) | Lexicon path overrides per language. |
| `chinese_onnx_model_dir`, `japanese_onnx_model_dir`, `arabic_onnx_model_dir`, `french_csv_dir` | Model bundle directory overrides. |
| `<language>_with_stress`, `<language>_vocoder_stress`, `<language>_expand_cardinal_digits`, `french_liaison`, ... | Language feature flags (bools, generally default `true`; `portuguese_keep_syllable_dots` defaults false). |

Also accepts `ort_providers`, `coreml_cache_dir`, `log_profiling`, `log_api_calls`. TTS-only keys are ignored when listing G2P dependencies. Exact key lists per language are in the verbatim copy.

## Embeddings

`moonshine_create_embedding_model()` takes `model_variant` as an argument, not an option: `q4` (default) or `q8`. `fp32`, `fp16` and `q4f16` are no longer supported. Create-from-memory accepts an options array but ignores it. For `moonshine_get_embedding_dependencies()`, `variant` (alias `model_variant`) picks which file goes in the manifest.

## Speech clip extract

| Key | Default | Description |
| --- | --- | --- |
| `clip_duration_seconds` | `4` | Length of the window to extract. |
| `minimum_speech_seconds` | `2` | Minimum speech in the window for `is_complete`. |
| `vad_threshold` | `0.5` | Speech probability threshold. |
| `tail_pad_seconds` | `0` | Extra audio after the VAD window. |

Also accepts `log_api_calls`.

## Download manifests

`moonshine_get_stt_dependencies()` takes the same options as loading the model; only these change the file list:

| Key | Description |
| --- | --- |
| `model_arch` | Decimal string of a `MOONSHINE_MODEL_ARCH_*` constant; omitted → language default. |
| `word_timestamps` | Include the attention decoder. |
| `include_spelling` / `spelling` | Include the spelling-CNN group when published. |
| `spelling_model_path` | Non-empty → same as including the spelling group. |

TTS and G2P listing (`moonshine_get_tts_dependencies()`, `moonshine_get_tts_voices()`, `moonshine_get_g2p_dependencies()`) use the TTS and G2P keys above (`voice`, `g2p_root`, ...).

## Source docs

Verbatim copies, for details not covered above:

- [api/options.md](references/api-options.md)
