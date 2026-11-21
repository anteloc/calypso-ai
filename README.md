# Calypso

A voice-controlled assistant, built on [Moonshine Voice](https://github.com/moonshine-ai/moonshine) and [TypeSafe's Jev](https://docs.typesafe.ai/).

Most voice assistants guess you've finished talking when you pause, so they act on half a sentence when you stop to think. Calypso waits until you've *really* finished: Jev judges whether what you've said so far is a finished sentence.

Speech recognition and her voice run on your machine. Only the text of what you ask her, after "Yes?", is sent to Jev.

## Run it

```bash
export TYPESAFE_API_KEY=...   # from https://console.typesafe.ai/keys
uv sync
uv run main.py
```

The first run downloads about 550 MB of speech models; after that, speech works offline. On macOS, allow your terminal to use the microphone when asked.

## Talk to her

1. Say **"Calypso"**. She replies "Yes?".
2. Ask one of these, in your own words:
   - "What time is it?"
   - "What's the date today?"
   - "Who are you?"
3. She speaks the answer and prints the conversation.

You can pause mid-sentence ("What's the… date today?"): she waits for the rest. If you go quiet for about 4 seconds she asks "And...?". After about 7 seconds she says "Ok, call me if you need something else" and drops the unfinished sentence.

Anything else gets "Sorry, I can't help with that yet." Say "cancel" to stop a question halfway.

## How it works

All the code is in [main.py](main.py), built on Moonshine's `AgentFlow`:

- `listen_for("Calypso", converse)` starts the `converse` flow when the wake word is heard.
- `converse` asks "Yes?" and collects what you say until `is_finished` says you're done. `is_finished` asks Jev one yes/no question (a `Noul`) and acts when Jev is more than 70% sure.
- While you haven't finished, `Patience` times the silence: "And...?" after 4 seconds, giving up after 7. It stops as soon as you start talking again.
- Once you've finished, your whole sentence is matched by meaning against `ANSWERS`, with Moonshine's `PhraseMatcher`.
- Replies are spoken with `TextToSpeech`, using language `en_gb` and voice `kokoro_bf_isabella`.

The timings and Jev's threshold are constants at the top of [main.py](main.py). To teach her something new, add a question and a reply function to `ANSWERS`.

## Next steps

- An LLM to answer open questions, where `converse` finds no match in `ANSWERS`.
- Patience right after "Yes?": if you say nothing at all, she still waits indefinitely.
