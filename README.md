# Calypso

A voice-controlled assistant, built on [Moonshine Voice](https://github.com/moonshine-ai/moonshine) and [TypeSafe's Jev](https://docs.typesafe.ai/).

Most voice assistants guess you've finished talking when you pause, so they act on half a sentence when you stop to think. Calypso waits until you've *really* finished: Jev judges whether what you've said so far is a finished sentence. Then she runs the command that does what you asked for.

Speech recognition and her voice run on your machine. Only the text of what you ask her, after "Yes?", is sent to Jev.

## Run it

```bash
export TYPESAFE_API_KEY=...   # from https://console.typesafe.ai/keys
uv sync
uv run main.py
```

The first run downloads about 550 MB of speech models; after that, speech works offline. On macOS, allow your terminal to use the microphone when asked.

Three of the commands run macOS Shortcuts: "Calypso - Play Spotify", "Calypso - Search on the Internet" and "Calypso - Date and Time". They must exist in the Shortcuts app.

## Talk to her

1. Say **"Calypso"**. She replies "Yes?".
2. Ask, in your own words, for something one of her commands does:
   - Do some maths ("What's 12 times 34?") or open the calculator.
   - Check or plan your days ("What do I have on Friday?"): opens the calendar.
   - Play music from Spotify ("Play some jazz").
   - Search the Internet ("Look up the population of Peru").
   - Tell you the date or time ("What time is it?").
   - Show you what you just said.
3. She says what she's doing ("Opening calculator") and runs the command.

She acts only once you've finished your sentence, so you can pause ("What's the… date today?"): she waits for the rest. If you go quiet for about 4 seconds she asks "And...?", and whatever you say next finishes the sentence ("Search on the…" "And...?" "…Internet" searches the Internet). If you stay quiet for 7 more seconds, she says "Ok, call me if you need something else" and drops the unfinished sentence.

Changed your mind? Say so in your own words ("nah, forget it", "leave it be") and she replies "Sure! We'll leave it here."

A finished sentence that no command does gets "I don't know how to do that." Say "cancel" to stop a question halfway.

## Teach her something new

Add a command to [calypso.toml](calypso.toml):

```toml
[[commands]]
run = "open -a calculator"          # a shell command line; "$speech" is what you said
ack = "Opening calculator"          # what she says as she runs it; blank for nothing
description = "to perform basic and advanced arithmetic operations, ..."
```

Jev matches your requests against the `description` alone, so describe what the command is *for*. What you said reaches the command only as the `speech` variable: quote it, `"$speech"`. It's data, never run as code.

## How it works

All the code is in [main.py](main.py), built on Moonshine's `AgentFlow`:

- `listen_for("Calypso", converse)` starts the `converse` flow when the wake word is heard.
- `converse` asks "Yes?" and collects what you say, asking `judge` about it after each pause.
- `judge` asks Jev, in one request, one yes/no question (a `Noul`) per thing it needs to know: have you finished, do you want to quit, and, for each command, would it do what you ask? Calypso acts on an answer when Jev is more than 60% sure. Among the commands, the best fit wins.
- If you quit, she leaves it. If you haven't finished, she keeps listening, however well what you've said so far fits a command. Each new piece is joined to what came before, and the whole sentence is judged again. Your answer to "And...?" always finishes it.
- Once you've finished: if a command fits, she says its `ack`, the conversation ends, and `run` starts the command in the background, with your whole sentence in `$speech`. If none fits, she says "I don't know how to do that." and the conversation ends.
- While she keeps listening, `Patience` times the silence: "And...?" after 4 seconds, giving up 7 seconds after that. It stops as soon as you start talking again.
- She speaks with `TextToSpeech`, using language `en_gb` and voice `kokoro_bf_isabella`.

The timings and Jev's threshold are constants at the top of [main.py](main.py). The question that matches commands, and the 0.6 threshold, come from calypso-fmr, where they were tuned on labelled requests.

## Next steps

- An LLM for requests no command does, where `converse` finds no command.
- Patience right after "Yes?": if you say nothing at all, she still waits indefinitely.
