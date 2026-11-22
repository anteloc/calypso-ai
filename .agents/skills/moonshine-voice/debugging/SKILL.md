---
name: debugging
description: 'Diagnosing Moonshine Voice problems: reading the console logs and exceptions from the core library, saving the audio a transcriber receives to WAV files with the `save_input_wav_path` option, and tracing the call timeline with the `log_api_calls` option (e.g. `moonshine-voice transcribe --options=''log_api_calls=true''`). Use when transcription quality is poor, audio input seems wrong, calls fail, or ordering and timing issues need investigating.'
---

# Debugging

Find out why Moonshine Voice isn't behaving as expected: read the core library's logs, check the audio the transcriber actually receives, and trace the order of API calls. General setup is in the [root skill](../SKILL.md).

## 1. Read the console logs

Look at the console first. Whenever the core library hits a failure point or an exception, it logs a message explaining what went wrong (to `stderr` or your system's equivalent). Bindings also turn core errors into exceptions in your language, but the logs often carry more detail.

## 2. Check the input audio: `save_input_wav_path`

No errors, but transcription quality is poor? Rule out a problem with the audio first. Set the `save_input_wav_path` option to a folder when creating the transcriber, and every bit of audio it receives is saved there as WAV (16 kHz mono):

```bash
moonshine-voice transcribe --options='save_input_wav_path=.'
```

This runs test audio through a transcriber and writes what it received to `input_1.wav` in the current directory. Additional streams produce `input_2.wav` and so on. The files hold only the latest session and are overwritten each time a session starts. Listen to them to confirm the input isn't distorted or corrupted.

In Python, pass it like any transcriber option:

```python
transcriber = Transcriber(model_path=model_path, model_arch=model_arch,
                          options={"save_input_wav_path": "."})
```

## 3. Trace the call timeline: `log_api_calls`

For errors that depend on ordering or timing, the `log_api_calls` option prints the underlying C API calls (and their arguments) to the console as they happen:

```bash
moonshine-voice transcribe --options='log_api_calls=true'
```

`log_api_calls` is a shared option: transcriber, TTS, G2P and other entry points accept it.

## Related options

Other logging switches (`log_ort_run`, `log_output_text`, `log_profiling`) and their scope are in [options](../reference/options/SKILL.md). For agents, `AgentFlow` has `log_io()` and `debug()`; for speech synthesis, `TextToSpeech.debug()` (see [classes](../reference/classes/SKILL.md)).

If the transcript drops or repeats words in a non-Latin language, see the `max_tokens_per_second` note in [choosing-a-model](../choosing-a-model/SKILL.md). If specific names or jargon come out wrong, see [domain-customization](../domain-customization/SKILL.md).

## Source docs

Verbatim copies, for details not covered above:

- [using/debugging.md](references/using-debugging.md)
