# Calypso

A voice-controlled assistant, built on [Moonshine Voice](https://github.com/moonshine-ai/moonshine). Everything runs on your machine, with no accounts or API keys.

The long-term goal is an assistant that knows when you've *really* finished talking, instead of guessing from a pause. This first version is a typical voice assistant to build on.

## Run it

```bash
uv sync
uv run main.py
```

The first run downloads about 550 MB of speech models, and later runs work offline. On macOS, allow your terminal to use the microphone when asked.

## Talk to her

1. Say **"Calypso"**. She replies "Yes?".
2. Ask one of these, in your own words:
   - "What time is it?"
   - "What's the date today?"
   - "Who are you?"
3. She speaks the answer and prints the conversation.

Anything else gets "Sorry, I can't help with that yet." Say "cancel" to stop a question halfway.

## How it works

All the code is in [main.py](main.py), built on Moonshine's `AgentFlow`:

- `listen_for("Calypso", converse)` starts the `converse` flow when the wake word is heard.
- `converse` asks "Yes?" and matches your question by meaning against `ANSWERS`.
- Replies are spoken with `TextToSpeech`, using language `en_gb` and voice `kokoro_bf_isabella`.

To teach her something new, add a question and a reply function to `ANSWERS`.

## Next steps

- An LLM to answer open questions, in the `except NoMatchError` branch of `converse`.
- End-of-turn detection, so she waits until you've finished your sentence.
