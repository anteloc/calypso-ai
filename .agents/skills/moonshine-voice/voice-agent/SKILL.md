---
name: voice-agent
description: 'Building spoken conversational agents with `AgentFlow` and `Dialog`: registering semantically matched conversation starters with `listen_for()`, generator-based multi-step and branching flows, `yield d.say(...)`, asking questions with `d.ask(...)`, yes/no confirmations with `d.confirm(...)`, spelled input, error handling, speaking a reply while it is written with `d.say_stream(...)`, and agent setup with `start_listening()`. Use when building a voice assistant, voice commands or intent recognition, a spoken multi-step flow (like the wifi-setup example), piping transcripts to an LLM, or running `moonshine-voice agent`.'
---

# Voice Agent

Build spoken conversational agents with `AgentFlow` and `Dialog`. You register conversation starters (trigger phrases) and write each conversation as an ordinary Python generator function. `AgentFlow` opens the microphone, speech recognition, phrase matching and speech synthesis for you, and routes what the user says to the right flow. Matching is semantic, so users don't have to say the exact words. Installing the library is covered in the [root skill](../SKILL.md).

## Try it

```bash
moonshine-voice agent
```

or, equivalently, the built-in example:

```bash
python -m moonshine_voice.agent_flow
```

It runs a spoken wifi-setup conversation: it listens for a trigger phrase, asks questions, and confirms the answers.

## 1. Write a flow

A flow is a generator function that takes a `Dialog`. Every `Dialog` method returns a prompt; you `yield` it, and the runner speaks it, waits for the user if needed, and resumes your function with the result. `yield` hands control back while the user is answering, so nothing blocks.

A simple flow (from [pi-help-bot](https://github.com/moonshine-ai/pi-help-bot)):

```python
    def report_ip_address(d: Dialog):
        ip = _find_local_ip()
        if ip is None:
            yield d.say("Sorry, I couldn't find a local IP address.")
            return
        speech_ip = re.sub(r"(\d)", r"\1 ", ip.replace(".", " dot "))
        yield d.say([
            f"Okay. Your local IP address is {speech_ip}. ",
            f"To repeat, that's {speech_ip}."
        ])

    agent_flow.listen_for("What is my IP address?", report_ip_address)
```

`listen_for()` calls `report_ip_address()` whenever the user says anything similar in meaning to "What is my IP address?" ("Tell me your IP address", "Can you tell me the local IP address?"). Register as many conversation starters as you like; the closest in meaning wins.

Write text the way it should be spoken: here the IP address is split into digits with explicit "dot"s, so 192.178.4.72 is read "1 9 2 dot 1 7 8 dot 4 dot 72".

## 2. Register flows and go live

```python
    agent_flow = (
        AgentFlow()
        .language("en")
        .listen_for("What is my IP address?", report_ip_address)
        .listen_for("Connect to Wi-Fi", connect_to_wifi)
    )

    agent_flow.start_listening()
```

- Every configuration method returns the runner and has a working default.
- `start_listening()` downloads and opens whatever is missing on first use (the embedding model for matching, the speech to text model for the language, a synthesizer), then returns as soon as the microphone is live. Speech arrives on the audio thread and drives the flows, so your code can sleep, run a UI, or anything else.
- To load at a time you choose, call `load()` first, with an `on_progress()` callback to report download progress.
- Call `close()` when finished to release everything the runner opened.
- "Cancel" and "start over" work inside any flow without registration. Outside a flow they are ordinary speech, so a dictation interface keeps them. Use `always()` to register your own phrase that is live at every moment.

## Dialog prompts

| Prompt | Flow receives | Use |
| --- | --- | --- |
| `yield d.say(text)` | `None` | Speak. `text` may be a list of strings. |
| `yield d.ask(prompt)` | `str` | Ask and get what the user said. |
| `yield d.ask(prompt, mode=SPELLED)` | `str` | Character-by-character input (passwords, codes). |
| `yield d.confirm(prompt)` | `bool` | Yes/no, matched semantically ("okay", "affirmative", "go ahead" are yes). |
| `yield d.say_stream(pieces)` | `None` | Speak text still being produced (an LLM reply). |

`d.choose()`, `d.cancel()`, `d.restart()`, `d.replay_last_prompt()`, the `ask()` modes `DIGITS` and `PHRASE`, timeouts, retries and the `NoInputError` / `NoMatchError` exceptions are in [classes](../reference/classes/SKILL.md).

## Multi-step flows

Branches, loops and exception handlers are plain Python. The wifi-setup flow:

```python
    def connect_to_wifi(d: Dialog):
        input_ssid = yield d.ask("What's the name of your Wi-Fi network? Say list if you want to pick from a list or spell if you want to spell out the start of the name")
        input_ssid = input_ssid.strip()

        networks = _scan_wifi_networks()

        if input_ssid.lower().strip(string.punctuation) == "list":
            yield d.say("Say yes to the network you want to connect to.")
            for network in networks:
                if (yield d.confirm(f"{network}?")):
                    input_ssid = network
                    break
        elif input_ssid.lower().strip(string.punctuation) == "spell":
            input_ssid = yield d.ask("Spell out the start of the network name.", mode=SPELLED)

        found_ssid = fuzzy_match_network(input_ssid, networks)
        if found_ssid is None:
            yield d.say(f"Sorry, I couldn't find a matching network for {input_ssid}.")
            return

        password = yield d.ask(
            f"Please spell the Wi-Fi password for {found_ssid} one character at a time, and say done when finished.",
            mode=SPELLED,
        )

        yield d.say(f"Connecting to {found_ssid}.")

        try:
            result = subprocess.run(
                ["sudo", "nmcli", "device", "wifi",
                    "connect", found_ssid, "password", password],
                capture_output=True, text=True, timeout=30,
            )
        except FileNotFoundError:
            yield d.say("Sorry, network manager was not found on this system.")
            return
        except subprocess.TimeoutExpired:
            yield d.say("Sorry, the connection attempt timed out.")
            return

        if result.returncode == 0:
            yield d.say(f"Connected to {found_ssid}.")
        else:
            print(f"[ERROR] nmcli stderr: {result.stderr}", file=sys.stderr)
            yield d.say(
                f"Sorry, I wasn't able to connect to {found_ssid}. "
                "Please check the network name and password and try again."
            )

    agent_flow.listen_for("Connect to Wi-Fi", connect_to_wifi)
```

What it shows:

- **Questions:** `yield d.ask(...)` returns the user's reply as a string.
- **Confirmations:** looping over options with `if (yield d.confirm(...))` (note the parentheses around the `yield`).
- **Spelled input:** `mode=SPELLED` asks for one character at a time and uses a fine-tuned model to recognize each. It understands "aitch", "capital zee", the NATO alphabet ("alpha", "bravo") and phrases like "E as in elephant". It repeats back what it heard, lets the user delete mistakes, and ends when the user says "done".
- **Error handling:** ordinary `try` / `except`, with a spoken message and `return` to end the flow.

## Speaking an LLM reply as it is written

Don't wait for a language model to finish before speaking. Inside a flow, yield the fragments:

```python
    def answer_question(d):
        question = yield d.ask("What would you like to know?")
        yield d.say_stream(llm.stream(question))
```

Outside a flow, push them through the runner's context manager:

```python
    with flow.say_stream() as push:
        for token in llm.stream(question):
            push(token)
```

- Playback starts as soon as the first sentence is complete (with Kokoro, even before that sentence has finished decoding).
- The microphone stays muted and self-capture suppressed for the whole passage, as with `say()`. The block exits only after playback finishes; the flow resumes after the last piece is spoken.
- If the text source raises part way through, what arrived is spoken and the error goes to `on_error()` instead of killing the flow.

For a full mic-to-LLM example, see [`ollama_voice.py`](https://github.com/moonshine-ai/moonshine/blob/main/examples/python/ollama-voice/ollama_voice.py) in the examples listed in the [root skill](../SKILL.md).

## Tuning and testing

Useful runner setters (full list in [classes](../reference/classes/SKILL.md)):

| Setter | Default | Use |
| --- | --- | --- |
| `trigger_threshold()` | `0.7` | Raise if triggers fire on unrelated speech; lower if genuine attempts don't fire. |
| `voice()` / `speech_options()` | | Pick the synthesis voice and TTS options (see [text-to-speech](../text-to-speech/SKILL.md)). |
| `microphone(False)` + `handle_utterance(text)` | `True` | Drive flows from text instead of a mic. |
| `use_embeddings(False)` | `True` | Substring matching with no model download, for offline tests. |
| `barge_in()` | off | Let the user interrupt. Only with reliable echo cancellation. |
| `log_io()` / `debug()` | off | Log the dialogue / trace internal stages to stderr. |
| `otherwise(handler)` | | Receive speech nothing else matched (dictation). |
| `use_mic_transcriber()` | | Listen to an existing transcriber, e.g. a `Transcriber` fed from a file. |

`Dialog` does no I/O, so a flow can be unit-tested by building a `Dialog`, calling the flow function, and driving the generator by hand with `.send()`.

## Pitfalls

- Forgetting `yield` before a `Dialog` call: the prompt is created but never runs.
- A flow that raises is torn down; without an `on_error()` handler the runner prints the error to stderr and carries on.
- `ask()`'s `bias_terms` is currently ignored. For vocabulary biasing, set `keyterms` on the transcriber (see [domain-customization](../domain-customization/SKILL.md)).

## Source docs

Verbatim copies, for details not covered above:

- [using/conversational-agent.md](references/using-conversational-agent.md)
