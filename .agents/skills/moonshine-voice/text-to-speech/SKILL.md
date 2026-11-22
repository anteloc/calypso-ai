---
name: text-to-speech
description: 'Speech synthesis with Moonshine Voice `TextToSpeech`: choosing a language and voice (Kokoro, Piper, ZipVoice, Phonon voices via `kokoro_`, `piper_`, `zipvoice_`, `phonon_` ids), speaking or synthesizing text, streaming text in as it is generated (`push_text()`, `end_input()`), zero-shot voice cloning (`cloning()`, `clone_from()`), voice samples, and converting graphemes to phonemes (IPA) with `GraphemeToPhonemizer`. Use when making an app speak, generating WAV audio from text, cloning a voice, getting phonemes, or running `moonshine-voice tts` / `moonshine-voice g2p`.'
---

# Text to Speech

Make an app speak with Moonshine's `TextToSpeech`: pick a language and voice, speak or synthesize text, stream an LLM's reply as it is written, clone a voice from a short clip, or get IPA phonemes with `GraphemeToPhonemizer`. It is self-contained, so it works without the transcription and agent modules. Installing the library is covered in the [root skill](../SKILL.md).

## Speak text

Configure with chainable setters, `load()` to fetch and open the voice, then `say()`:

```python
from moonshine_voice import TextToSpeech

tts = TextToSpeech().language("fr")
tts.load()
tts.say("Bonjour, mon ami")
tts.wait()  # block until playback finishes
```

- `load()` blocks, since the first call may download a voice. Drive a progress bar with `on_progress()`:

  ```python
  tts = TextToSpeech().language("fr").on_progress(lambda fraction, file: print(f"{fraction:.0%}"))
  tts.load()
  ```

- `say()` returns immediately and queues the text. Utterances play in order, and the next one is pre-synthesized while the current one plays. It also takes a list of strings.
- `stop()` cancels remaining utterances and halts playback. `is_talking()` polls playback state. `wait()` blocks until everything has played.
- `say()` on Python needs `pip install numpy sounddevice`. Choose a playback device with `output_device()`.

```python
tts.say(["One.", "Two.", "Three."])
tts.stop()  # cancel remaining utterances and halt playback
```

From the command line:

```bash
moonshine-voice tts --language en_us --text "Hello world"
```

## Get audio samples instead of playing

On a machine without audio output, or for further processing, use `synthesize()`. It returns mono float samples and their sample rate:

```python
from moonshine_voice import TextToSpeech

tts = TextToSpeech().language("en-us")
tts.load()
audio_data, sample_rate = tts.synthesize("Howdy, partner")
```

## Languages and voices

```python
from moonshine_voice import list_tts_languages
list_tts_languages()

['ar-msa', 'de-de', 'en-gb', 'en-us', 'es-ar', 'es-es', 'es-mx', 'fr-fr', 'hi-in', 'it-it', 'ja-jp', 'ko-kr', 'nl-nl', 'pt-br', 'pt-pt', 'ru-ru', 'tr-tr', 'uk-ua', 'vi-vn', 'zh-hans']
```

```python
from moonshine_voice import list_tts_voices

list_tts_voices("ru")

{'present': [], 'downloadable': ['piper_ru_RU-denis-medium', 'piper_ru_RU-dmitri-medium', 'piper_ru_RU-irina-medium', 'piper_ru_RU-ruslan-medium']}
```

A `downloadable` voice passed to `voice()` is downloaded to a cache automatically, then works offline. The voice id's prefix picks the engine:

| Engine | Ids | Character |
| --- | --- | --- |
| Kokoro | `kokoro_af_heart`, `kokoro_am_adam`, `kokoro_bf_emma`, `kokoro_bm_george`, ... | 82M-parameter open-weight model; American and British, female and male (`af_`, `am_`, `bf_`, `bm_`). |
| Piper | `piper_ru_RU-denis-medium`, ... (from `list_tts_voices()`) | Over a hundred lightweight voices across every supported language. Samples: [Piper voice samples](https://rhasspy.github.io/piper-samples/). |
| ZipVoice | `zipvoice_american_female`, `zipvoice_english_male`, `zipvoice_indian_female`, ... | Flow-matching model with on-device cloning and more realistic speech; much slower to generate than Kokoro or Piper. |
| Phonon | `phonon_zoey`, `phonon_hugh`, `phonon_the_snow_queen`, ... (37 English voices) | 31M-parameter streaming model from [Gradium](https://gradium.ai), Apache 2.0. Streaming starts after a few hundred ms of audio. |

Full voice lists with audio samples are in the verbatim source doc ([references/using-text-to-speech.md](references/using-text-to-speech.md)).

Phonon specifics:

- It reads text directly, so it does not use Moonshine's G2P.
- Sampling is stochastic: `phonon_temperature` defaults to 0.3; set `0` for a deterministic render.
- Speed is a conditioning signal, not a time-stretch: approximate, and it saturates past about 0.7x–1.4x.
- Moonshine cannot clone into a Phonon voice on the device. A `.safetensors` voice made with [Gradium Studio](https://studio.gradium.ai/) loads unchanged: pass the bare voice name `phonon` and the file as the `phonon_voice_file` option. Such voices fall under Gradium's terms, not Apache 2.0.

Engine-specific tuning options (`speed`, Piper noise, ZipVoice steps, Phonon seed, ...) are in [options](../reference/options/SKILL.md).

## Stream text in (LLM replies)

Don't wait for a whole LLM reply before speaking. Push text as it arrives and get audio as soon as there is enough to say:

```python
tts = TextToSpeech().language("en-us")
tts.load()

for chunk in tts.stream(llm_tokens()):
    print(f"{len(chunk.samples) / chunk.sample_rate:.2f}s: {chunk.text}")
```

To play the chunks instead, use `say_stream()`, which feeds the same playback queue as `say()`:

```python
with tts.say_stream() as speech:
    for token in llm_tokens():
        tts.push_text(token)
    tts.end_input()
    speech.wait()
```

`AgentFlow` has the same method (see [voice-agent](../voice-agent/SKILL.md)):

```python
with agent.say_stream() as push:
    for token in llm.stream(prompt):
        push(token)
```

How streaming works:

- There is no stream object to open or close. A synthesizer speaks one thing at a time: pushing text starts a reply, ending input finishes it.
- `stream(text)` pushes and ends the text for you. To drive it yourself, call `push_text()` from another thread and iterate `stream()` with no argument.
- Text is held until a complete sentence or phrase arrives, because prosody depends on where a clause ends. `flush()` synthesizes what is buffered anyway; `end_input()` says no more text is coming; `cancel_stream()` abandons an interrupted reply.
- While a reply is in progress, `say()` and `synthesize()` refuse until it finishes or is cancelled.
- Each chunk has the samples, sample rate, the text it covers, an utterance id (numbered from one), and whether it ends that utterance. A chunk covering acoustic frames rather than a span of characters has empty text.
- Other bindings: `pushText` / `flush` / `endInput` / `cancelStream` with an `onChunk` consumer in TypeScript, Swift and Java, plus an async iterator in TypeScript and an `AsyncThrowingStream` in Swift.
- Streamed loudness is levelled per voice instead of by peak normalization, so it lands within a decibel or two of `say()`.

Most of the latency win is from not waiting on the model: for a four-sentence reply written at fifty tokens a second, first audio arrives in well under a second streamed, against a little over two seconds otherwise.

## Clone a voice

On-device cloning uses [ZipVoice](https://github.com/k2-fsa/ZipVoice). Call `cloning()` before `load()`, then `clone_from()` with a `.wav` path or a `(pcm, sample_rate)` pair of mono float samples:

```python
from moonshine_voice import TextToSpeech
import importlib.resources;

clone_path = importlib.resources.files("moonshine_voice.assets").joinpath("clone-test.wav")
clone_transcript = "Ever tried. Ever failed. No matter. Try Again. Fail again. Fail better."

tts = TextToSpeech().language("en-us").cloning()
tts.load()
tts.clone_from(clone_path, transcript=clone_transcript)
tts.say("Ask not what your country can do for you, but what you can do for your country")
tts.wait()
```

- `transcript` (the text spoken in the clip) is optional. Without it, Moonshine auto-transcribes the clip first (a few extra seconds on first use).
- `cloning()` makes `load()` fetch ZipVoice and its clone-ASR assets up front, so `clone_from()` only swaps the reference clip. Without `cloning()`, `clone_from()` / `start_cloning()` raise a clear error.
- Catalog voices and cloning are mutually exclusive: `voice()` clears cloning and `cloning()` clears the catalog voice.
- Use a voice only with its speaker's consent.

Clone from the microphone with `start_cloning()`, which returns a `VoiceClone` that listens until it has enough usable speech:

```python
clone = tts.start_cloning()
clone.on_ready(lambda: print("Got it, you can stop talking."))
clone.from_microphone()
tts.clone_from(clone)
```

`from_microphone()` blocks until the clip is ready or 20 seconds pass. `on_progress()` reports recording time and speech found. Clip selection uses the built-in voice-activity detector, so nothing is downloaded for that step.

From the command line (transcript optional):

```bash
curl -O -L 'https://github.com/moonshine-ai/moonshine/raw/refs/heads/main/language-bindings/python/src/moonshine_voice/assets/clone-test.wav'

python3 -m moonshine_voice.tts \
  --clone clone-test.wav \
  --text "I am so excited about Moonshine Voice's text to speech"
```

## Graphemes to phonemes (IPA)

Kokoro and Piper voices are driven by phonemes. Instead of GPL-licensed espeak-ng, Moonshine uses its own MIT-licensed G2P engine ([core/moonshine-tts](https://github.com/moonshine-ai/moonshine/blob/main/core/moonshine-tts)), so it can be linked into iOS and Android apps. Use it on its own without synthesis:

```python
from moonshine_voice import GraphemeToPhonemizer

g2p = GraphemeToPhonemizer("en-us")
g2p.to_ipa("Hello world")

'həlˈoʊ wˈɝld'
```

Or from the command line: `moonshine-voice g2p`.

The engine is new and still being tuned. Intelligibility (character error rate) is close to the reference for Spanish, Turkish and English, but notably worse for some languages, e.g. `vi_vn` 79.0% vs 36.5%, `pt_pt` 43.8% vs 24.6%, `ja_jp` 38.1% vs 16.8%. The full table is in the verbatim source doc.

## Pitfalls

- Calling `clone_from()` without `cloning()` before `load()`: raises.
- Calling `say()` or `synthesize()` while a streamed reply is in progress: refused until it ends or `cancel_stream()`.
- Errors: `MoonshineTtsLanguageError` (bad language tag), `MoonshineTtsVoiceError` (unknown or missing voice), `MoonshineAudioOutputError` (playback; lists output devices). See [classes](../reference/classes/SKILL.md).
- Bundling or pre-fetching voices for offline use: see [downloading-models](../downloading-models/SKILL.md).

## Source docs

Verbatim copies, for details not covered above:

- [using/text-to-speech.md](references/using-text-to-speech.md)
