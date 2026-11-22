# Calypso

A voice-controlled assistant, built on [Moonshine Voice](https://github.com/moonshine-ai/moonshine) and [TypeSafe's Jev](https://docs.typesafe.ai/).

Most voice assistants guess you've finished talking when you pause, so they act on half a sentence when you stop to think. Calypso waits until you've *really* finished: Jev judges whether what you've said so far is a finished sentence. Then she runs the command that does what you asked for.

Speech recognition and her voice run on your machine. Only the text of what you ask her, once she's awake, is sent to Jev.

## Run it

```bash
export TYPESAFE_API_KEY=...   # from https://console.typesafe.ai/keys
uv sync
uv run calypso-cli assistant  # or: uv run main.py
```

The first run downloads about 550 MB of speech models; after that, speech works offline. On macOS, allow your terminal to use the microphone when asked.

To see what she makes of what you say, run `uv run calypso-cli --debug assistant` (or `uv run main.py --debug`). She then plays a "got it" tone whenever she has understood you, and a "didn't get that" tone when she hasn't. Each of Jev's judgments is printed too, e.g. `Jev on 'Search on the Internet': 42% finished, 4% quitting, best command 98%: …`.

Three of the commands run macOS Shortcuts: "Calypso - Play Spotify", "Calypso - Search on the Internet" and "Calypso - Date and Time". They must exist in the Shortcuts app.

## Set her up

```bash
uv run calypso-cli config  # or: uv run main.py --config
```

It walks you through her settings, which it saves at the top of [calypso.toml](calypso.toml). Press Enter to keep a value, or Ctrl+C to quit without saving.

| Setting | What it is | Default |
| --- | --- | --- |
| `user_name` | Your name, optional | none |
| `user_language` | The language you speak, which she listens in | `en` |
| `assistant_name` | Her name | `Calypso` |
| `assistant_language` | The language she speaks | `en-gb` |
| `assistant_voice` | Her voice: you hear each kokoro voice for her language, saying her answers, and pick one | `kokoro_bf_isabella` |
| `trigger` | What you say to wake her up, such as "Wake up $assistant_name" | `$assistant_name` |
| `quit_intent` | Examples of what you say to call a request off, in your language. Jev recognizes anything that means the same | `["nah, forget it", "leave it be", "better don't do anything"]` |
| `trigger_ack` | What she answers when woken, such as "How can I help, $user_name?" | `["Yes?"]` |
| `nudge` | What she says when you go quiet mid-sentence, such as "So, $user_name...?" | `["And...?"]` |
| `goodbye` | What she says when she stops waiting for the rest | `["Ok, call me if you need something else."]` |
| `quit_ack` | What she says when you call it off | `["Sure! We'll leave it here."]` |
| `dont_know` | What she says when no command does what you asked | `["I don't know how to do that."]` |

Her phrases, the last five, are lists: give several and she picks one at random each time. In any setting, and in the commands' `ack`, `$user_name` and `$assistant_name` stand for the names, anywhere in the text (write `${user_name}` when letters follow right after). In a command's `run`, they're shell variables, like `$speech`.

Last, it tests the trigger: you say it 3 times, and for each try you see what she heard and whether she woke up. If she missed any, test it again or pick another trigger. Uncommon names are often misheard, and a trigger she doesn't recognize leaves her deaf to you.

## Talk to her

1. Say her trigger, **"Calypso"** unless you've changed it. She replies "Yes?", or one of the answers you gave her.
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

These are her default phrases; you can give her your own (see [Set her up](#set-her-up)).

## Teach her something new

Add a command to [calypso.toml](calypso.toml):

```toml
[[commands]]
run = "open -a calculator"          # a shell command line; "$speech" is what you said
ack = "Opening calculator"          # what she says first; blank for nothing
description = "to perform basic and advanced arithmetic operations, ..."
```

Jev matches your requests against the `description` alone, so describe what the command is *for*. What you said reaches the command only as the `speech` variable: quote it, `"$speech"`. It's data, never run as code.

### Her voice and ears in commands: calypso-cli

`uv sync` installs `calypso-cli`, so commands can talk to you and listen to you, with her settings from [calypso.toml](calypso.toml):

```bash
calypso-cli say "Hello world"                            # say a text with her voice
echo "Hello world" | calypso-cli say                     # ...or what comes in on stdin
calypso-cli transcribe "What should I write down?"       # say the prompt, listen, print what you said
```

`transcribe` needs no trigger. It listens until you've finished your sentence, the way she does: if you pause mid-sentence, she nudges you ("And...?") and waits for the rest. It prints the sentence to stdout and exits 0. If you call it off, or go quiet, it prints nothing and exits 1, so `&&` stops there. Everything else, like what she hears and says, goes to stderr.

For example, a command that takes notes:

```toml
[[commands]]
run = 'calypso-cli transcribe "What should I write down?" >> ~/notes.txt && calypso-cli say "Noted."'
ack = ""
description = "to take a note, writing down what someone dictates"
```

Give `transcribe` its prompt rather than running `calypso-cli say` before it: it says the prompt once it's listening, so your first words aren't lost while it starts up. A prompt also helps Jev judge whether you've finished: "milk and eggs" is a finished answer to "What should I write down?".

Outside Calypso, run it with `uv run calypso-cli ...`. Add `--debug` (`calypso-cli --debug transcribe`) to see Jev's judgments.

## How it works

The assistant is in [main.py](main.py), built on Moonshine's `AgentFlow`. Her settings, and the `--config` mode, are in [config.py](config.py).

- `listen_for(TRIGGER, converse)` starts the `converse` flow when her trigger is heard. Like Moonshine's other phrase matching, this goes by meaning, so it needn't be word for word.
- `converse` answers with one of the `trigger_ack` phrases, and `listen` collects what you say, asking `judge` about it after each pause. `calypso-cli transcribe` ([cli.py](cli.py)) uses the same `listen`, with a judgment for dictation instead of requests.
- `judge` asks Jev, in one request, one yes/no question (a `Noul`) per thing it needs to know: have you finished, do you want to quit, and, for each command, would it do what you ask? Calypso acts on an answer when Jev is more than 60% sure. Among the commands, the best fit wins.
- If you quit, she leaves it. If you haven't finished, she keeps listening, however well what you've said so far fits a command. Each new piece is joined to what came before, and the whole sentence is judged again. Your answer to a nudge ("And...?") always finishes it.
- Once you've finished: if a command fits, she says its `ack`, the conversation ends, and `run` starts the command in the background, with your whole sentence in `$speech`. If none fits, she says one of `dont_know` and the conversation ends.
- While she keeps listening, `Patience` times the silence: a `nudge` after 4 seconds, a `goodbye` 7 seconds after that. It stops as soon as you start talking again.
- She listens with a `MicTranscriber` in `user_language`, and speaks with a `TextToSpeech` in `assistant_language`, with `assistant_voice`.
- The `--config` trigger test builds its agent the same way, so she recognizes the trigger there exactly as she will when running.

The timings and Jev's threshold are constants at the top of [main.py](main.py). The question that matches commands, and the 0.6 threshold, come from calypso-fmr, where they were tuned on labelled requests.

## Next steps

- An LLM for requests no command does, where `converse` finds no command.
- Patience right after she answers the trigger: if you say nothing at all, she still waits indefinitely. So does `calypso-cli transcribe`.
- Calypso keeps listening while a command runs, so she also hears what `calypso-cli` says and what you dictate to it. That's harmless unless it sounds like her trigger.