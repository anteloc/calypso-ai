---
name: transcription
description: 'Speech to text with Moonshine Voice: live microphone transcription with `MicTranscriber` (`language()`, `on_text()`, `on_line()`, `on_progress()`, `model_arch()`, `models_from()`, `load()`, `start()`, `stop()`, `close()`), and feeding your own audio (WAV files, custom capture, multiple streams) with `Transcriber`, `Stream` and `TranscriptEventListener`, plus the transcript event flow (line started, updated, text changed, completed) and transcript lines, word timestamps and speaker IDs. Use when transcribing a microphone, a file or an audio stream, handling partial versus final lines, or running `moonshine-voice mic` / `moonshine-voice transcribe`.'
---

# Transcription

Turn live or recorded speech into text with Moonshine Voice. Use `MicTranscriber` to transcribe the system microphone with two callbacks, or the base `Transcriber` to feed audio yourself (WAV files, a custom capture pipeline, several streams) and react to transcript events. Installing the library and the cross-language naming are in the [root skill](../SKILL.md).

## Live microphone: `MicTranscriber`

Create a `MicTranscriber`, attach callbacks, call `load()` to fetch and open the model, then `start()` to listen:

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

- `on_text()` fires whenever the in-progress line changes. Use it to show live text.
- `on_line()` fires once per finished segment with the final line (fields in [c-api](../reference/c-api/SKILL.md), struct `transcript_line_t`).
- `load()` blocks on first use while it downloads the language's recommended model into a local cache. Later launches reuse the cache and run offline.
- `stop()` ends listening. `close()` (or a context manager) releases the microphone and model.

Drive a progress bar during the first download with `on_progress()`. Attaching a handler also silences the default terminal progress bars:

```python
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

Choosing the model:

- The default is the catalog's recommended model for the language (medium streaming for English). Most languages publish only one model.
- `model_arch()` picks a specific size. See [choosing-a-model](../choosing-a-model/SKILL.md).
- `models_from()` points at a directory of models you already have. See [downloading-models](../downloading-models/SKILL.md).

From the command line: `moonshine-voice mic --language en` (live mic) and `moonshine-voice transcribe` (a WAV file, optionally with speaker IDs or word timestamps).

`MicTranscriber` also supports `add_listener()` (below) when you need line ids, speaker spans, word timings, or the moment a line starts. Every other setter (`update_interval()`, `options()`, `device()`, `mute()`, ...) is listed in [classes](../reference/classes/SKILL.md).

## Feeding your own audio: `Transcriber`

Use the base `Transcriber` for audio you capture yourself. [Download the model files](../downloading-models/SKILL.md) first, put them where the app can find them, and pass the path in:

```python
transcriber = Transcriber(model_path=model_path, model_arch=model_arch)
```

If the model isn't found, or anything else goes wrong, the constructor throws an exception describing the problem. The core library also logs to `stderr` (or your system's equivalent).

### 1. Attach a listener

Put your app logic in a `TranscriptEventListener` subclass and register it:

```python
class TestListener(TranscriptEventListener):
    def on_line_started(self, event):
        print(f"Line started: {event.line.text}")

    def on_line_text_changed(self, event):
        print(f"Line text changed: {event.line.text}")

    def on_line_completed(self, event):
        print(f"Line completed: {event.line.text}")

listener = TestListener()
transcriber.add_listener(listener)
```

### 2. Start a session, add audio, stop

Here a WAV file is fed in chunks to simulate a live source:

```python
    audio_data, sample_rate = load_wav_file(wav_path)

    transcriber.start()

    # Loop through the audio data in chunks to simulate live streaming
    # from a microphone or other source.
    chunk_duration = 0.1
    chunk_size = int(chunk_duration * sample_rate)
    for i in range(0, len(audio_data), chunk_size):
        chunk = audio_data[i: i + chunk_size]
        transcriber.add_audio(chunk, sample_rate)

    transcriber.stop()
```

- `load_wav_file()` is a convenience function in the Moonshine library that returns mono audio data and its sample rate.
- Call `start()` before adding audio. It activates processing.
- Chunks can be any length and any sample rate; the library handles conversion. The audio must be **mono**; otherwise feed it as-is.
- Listeners are called as audio is added.
- In a real app, call `add_audio()` from the audio handler that receives data from your source.

### Sessions and the transcript

- `start()` / `stop()` begin and end a session. Each session has one transcript, started fresh on every `start()`. Copy any transcript data you need before calling `start()` again.
- You rarely need the transcript structure itself: the events tell you when something important happens. To inspect the current state, call `update_transcription()`, which returns a transcript object for the whole session.
- For audio from the past (a file, a recording), `transcribe_without_streaming()` is simpler.

### Update interval

The transcriber analyses speech every 500ms of input by default. Change it with the `update_interval` constructor argument (or `MicTranscriber.update_interval()`). For streaming models most work happens as audio is added, and a pass runs automatically at the end of each phrase, so changing it usually does not change workload or latency much.

The interval is a floor, not a fixed cadence: a pass must cover at least as much audio as the previous pass took to compute, up to ten intervals' worth. A machine that can't keep up transcribes in larger batches instead of falling further behind.

## Transcript event flow

Listeners receive five event types:

| Event | Listener method | When |
| --- | --- | --- |
| `LineStarted` | `on_line_started()` | A new speech segment begins. It may have no text yet, and its text will likely change. |
| `LineUpdated` | `on_line_updated()` | Anything about the line changes: duration, audio data, text. |
| `LineTextChanged` | `on_line_text_changed()` | Only the text changed. A subset of `LineUpdated`; use it to refresh displayed text. |
| `LineSpeakersChanged` | `on_line_speakers_changed()` | Speaker spans changed. Only with the opt-in `identify_speakers` option. Can fire for already completed lines. |
| `LineCompleted` | `on_line_completed()` | The speaker paused and the segment ended. Text and duration are final. |

Guarantees:

- `LineStarted` fires exactly once per segment, and `LineCompleted` exactly once after it.
- `LineUpdated` and `LineTextChanged` only fire between those two. They are not guaranteed to fire at all (a very large `update_interval` effectively disables them).
- Only one line is active at a time per stream.
- After `LineCompleted`, the line's text, timing and audio never change. The exception is speaker spans with `identify_speakers` enabled: diarization re-clusters a sliding window of recent speech and signals revisions with `LineSpeakersChanged`. Assignments for audio older than `diarization_cluster_window_sec` are frozen.
- Calling `stop()` on a transcriber or stream completes any active line (`LineCompleted` fires).
- Each line has a 64-bit `lineId`, unique enough to avoid collisions, and stable from its first `LineStarted` onwards.

## Speakers, word timestamps and other options

Pass advanced options as a string-keyed map (`options` on `Transcriber`, `options()` on `MicTranscriber`). Commonly needed keys: `identify_speakers` (diarization, fills speaker spans), `word_timestamps` (fills each line's `words`), `vad_threshold` and `vad_max_segment_duration` (how speech is segmented into lines), `keyterms` / `context` (vocabulary biasing, see [domain-customization](../domain-customization/SKILL.md)). Defaults and the full list are in [options](../reference/options/SKILL.md).

## Pitfalls

- Feeding stereo audio: the input must be mono.
- Reading the transcript after a new `start()`: it has been reset. Copy what you need first.
- Calling `MicTranscriber.start()` before `load()` raises.
- Poor accuracy with no errors: save the audio the transcriber actually receives and listen to it. See [debugging](../debugging/SKILL.md).

## Source docs

Verbatim copies, for details not covered above:

- [using/transcription.md](references/using-transcription.md)
