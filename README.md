# Calypso

A voice-controlled assistant, built on [Moonshine Voice](https://github.com/moonshine-ai/moonshine) and [TypeSafe's Jev](https://docs.typesafe.ai/).

Most voice assistants guess you've finished talking when you pause, so they act on half a sentence when you stop to think. Calypso waits until you've *really* finished: Jev judges whether what you've said so far is a finished sentence. Then she runs the command that does what you asked for.

Speech recognition and her voice run on your machine. Once she is awake, Jev judges your transcribed requests against the command descriptions. On follow-up turns it receives the current question and your answer so far.

## Run it

```bash
export TYPESAFE_API_KEY=...   # from https://console.typesafe.ai/keys
uv sync
uv run calypso-cli assistant  # or: uv run main.py
```

The first run downloads about 550 MB of speech models; after that, speech works offline. On macOS, allow your terminal to use the microphone when asked.

To see what she makes of what you say, run `uv run calypso-cli --debug assistant` (or `uv run main.py --debug`). She then plays a "got it" tone whenever she has understood you, and a "didn't get that" tone when she hasn't. The log shows Jev’s completion and cancellation scores, plus the best matching description for an opening request.

The bundled commands use macOS. Search uses `jq` and `open`, Spotify uses its configured player executable, and Date and Time runs the “Calypso - Date and Time” shortcut in the Shortcuts app.

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

Give her several phrases for a response and she picks one at random. In spoken text, `$user_name` and `$assistant_name` stand for the configured names. Use `${user_name}` when letters follow immediately afterward.

In `nudge`, `goodbye`, `quit_ack`, and `dont_know`, `$speech` holds what you have said on the current turn. In `trigger_ack` it is empty.

Last, it tests the trigger: you say it 3 times, and for each try you see what she heard and whether she woke up. If she missed any, test it again or pick another trigger. Uncommon names are often misheard, and a trigger she doesn't recognize leaves her deaf to you.

## Talk to her

1. Say her trigger, **"Calypso"** unless you've changed it. She replies "Yes?", or one of the answers you gave her.
2. Ask, in your own words, for something one of her commands does:
   - Do some maths ("What's 12 times 34?") or open the calculator.
   - Check or plan your days ("What do I have on Friday?"): opens the calendar.
   - Play music from Spotify ("Play some jazz").
   - Search the Internet ("Search on the internet"). She asks what you want to search for.
   - Tell you the date or time ("What time is it?").
   - Show you what you just said.
3. She follows the matched command. For example, she says “Opening calculator” and opens it. For search, she asks for a query and waits for your answer.

> **You** — Calypso.
>
> **Calypso** — Yes?
>
> **You** — Search on the internet.
>
> **Calypso** — What do you want me to search for?
>
> **You** — I’d like to… to… find nice spots for a vacation!
>
> **Calypso** — A second...

She opens Google with the complete answer as Moonshine transcribed it, including hesitations and corrections that appeared in the transcript. She then listens for her wake word again.

After four seconds without a first word, she repeats her question once. If you pause partway through a sentence, she uses your configured nudge. When you continue, Jev judges the whole sentence again. After seven more seconds of silence, she says goodbye and drops the conversation.

You can call it off in your own words (“nah, forget it”) or use Moonshine’s “cancel”. A finished opening request with no matching command gets the configured `dont_know` response.

## Teach her something new

Each `[[commands]]` entry in [calypso.toml](calypso.toml) has a `description` and a nonempty `steps` list. Describe what the command does so Jev can recognize when someone asks for it.

| Step | What happens |
| --- | --- |
| `ask` with `save_as` | Speak a question and wait for a finished answer. Its name is available immediately to every following step. |
| `say` | Speak the text with the available variables filled in. |
| `run` | Run a shell line or multiline script with `/bin/sh`. Calypso mutes her microphone during the script and continues on success. A failure is reported in the terminal and ends the command. |

The search command asks for a query, then opens the result in your browser.

```toml
[[commands]]
description = "Search the internet for information."
steps = [
    { ask = "What do you want me to search for?", save_as = "query" },
    { say = "A second..." },
    { run = '''
        encoded=$(printf '%s' "$query" | jq -sRr @uri) &&
            open "https://www.google.com/search?q=$encoded"
    ''' },
]
```

You can ask several questions in a row. Here, an answer of “Menorca” makes the next question “When would you like to visit Menorca?” The final script receives all three answers.

```toml
[[commands]]
description = "Save an idea for a trip I want to take."
steps = [
    { ask = "Where would you like to go?", save_as = "destination" },
    { ask = "When would you like to visit $destination?", save_as = "dates" },
    { ask = "What would you like to do there?", save_as = "activities" },
    { run = '''
        printf 'Destination: %s\nDates: %s\nActivities: %s\n\n' \
            "$destination" "$dates" "$activities" >> "$HOME/trip-ideas.txt"
    ''' },
    { say = "I've saved your trip idea." },
]
```

Choose a unique `save_as` name starting with a lowercase letter, followed by lowercase letters, digits, or underscores. The names `speech`, `user_name`, and `assistant_name` are reserved. Throughout a command, `$speech` holds the opening request. Quote shell variables such as `"$query"` to pass the whole answer as one argument. Calypso supplies the values through the script’s environment. Saved answers expire at the end of the command.

### Standalone speech and dictation

`uv sync` installs `calypso-cli`, so commands can talk to you and listen to you, with her settings from [calypso.toml](calypso.toml):

```bash
calypso-cli say "Hello world"                            # say a text with her voice
echo "Hello world" | calypso-cli say                     # ...or what comes in on stdin
calypso-cli transcribe "What should I write down?"       # say the prompt, listen, print what you said
```

`transcribe` needs no trigger. It listens until you've finished your sentence, the way she does: if you pause mid-sentence, she nudges you ("And...?") and waits for the rest. It prints the sentence to stdout and exits 0. If you call it off, or go quiet, it prints nothing and exits 1, so `&&` stops there. Everything else, like what she hears and says, goes to stderr.

In a command Calypso runs, `$speech` in what `say` or `transcribe` says is your request, even inside single quotes: `calypso-cli say 'You asked: $speech'`.

A prompt helps Jev judge a short answer. For example, “milk and eggs” is a finished answer to “What should I write down?”.

Outside Calypso, run it with `uv run calypso-cli ...`. Add `--debug` (`calypso-cli --debug transcribe`) to see Jev's judgments.

## How it works

The assistant is in [main.py](main.py), built on Moonshine's `AgentFlow`. Her settings, and the `--config` mode, are in [config.py](config.py).

- `listen_for(TRIGGER, converse)` starts the `converse` flow when her trigger is heard. Like Moonshine's other phrase matching, this goes by meaning, so it needn't be word for word.
- `converse` answers with one of the `trigger_ack` phrases, and `listen` collects what you say, asking `judge` about it after each pause. `calypso-cli transcribe` ([cli.py](cli.py)) uses the same `listen`, with a judgment for dictation instead of requests.
- `judge` asks Jev, in one request, one yes/no question (a `Noul`) per thing it needs to know: have you finished, do you want to quit, and, for each command, would it do what you ask? Calypso acts on an answer when Jev is more than 60% sure. Among the commands, the best fit wins.
- Each `ask` uses the same `listen` as the opening request, with a Jev judgment for dictation. The active Moonshine `Dialog` speaks every prompt and receives every reply using the same microphone and voice.
- While the dialog waits for a fragment, `Patience` times the silence. Speaking, finishing the turn, or abandoning it clears its timer.
- She listens with a `MicTranscriber` in `user_language`, and speaks with a `TextToSpeech` in `assistant_language`, with `assistant_voice`.
- The `--config` trigger test builds its agent the same way, so she recognizes the trigger there exactly as she will when running.

The timings and Jev's threshold are constants at the top of [main.py](main.py). The question that matches commands, and the 0.6 threshold, come from calypso-fmr, where they were tuned on labelled requests.

## Next steps

- An LLM for requests no command does, where `converse` finds no command.
