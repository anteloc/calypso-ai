"""calypso-cli: Calypso, and her voice and ears for the commands in calypso.toml.

    calypso-cli assistant          # run Calypso, as `uv run main.py` does
    calypso-cli config             # set her up, as `uv run main.py --config` does
    calypso-cli say "Hello world"
    calypso-cli transcribe "What should I write down?" >> ~/notes.txt

`say` speaks with her voice. `transcribe` listens, with no trigger, until
you've finished your sentence, judged just as Calypso judges it, then prints
it. All of them use the settings in calypso.toml.
"""

import argparse
import contextlib
import os
import sys
import threading
from functools import partial

from moonshine_voice import TextToSpeech

import config
import main as calypso

START = "calypso-cli transcribe"  # Fed to the agent to start listening at once.

# When Calypso runs a command, what the user asked her for: it fills in $speech
# in what calypso-cli says, even inside single quotes.
SPEECH = os.environ.get("speech", "")


def say(text):
    """Say `text` with her voice, $user_name, $assistant_name and $speech filled in."""
    settings = calypso.CONFIG
    language, voice_id = settings["assistant_language"], settings["assistant_voice"]
    with TextToSpeech().language(language).voice(voice_id) as voice:
        voice.load()
        voice.say(config.fill(text, settings, SPEECH))
        voice.wait()


def transcribe(prompt, debug):
    """Say `prompt` (if any), and listen until the user has finished their sentence.

    Returns the sentence, or None if they called it off or went quiet.
    """
    prompt = config.fill(prompt, calypso.CONFIG, SPEECH)
    heard = []
    done = threading.Event()

    def take_down(d, patience):
        try:
            judge = partial(calypso.judge_dictation, prompt)
            sentence, _ = yield from calypso.listen(d, patience, prompt, judge)
            heard.append(sentence)
        finally:  # Also when Patience gives up and ends the flow.
            done.set()

    with calypso.assistant(debug) as (agent, patience, _mute):
        agent.listen_for(START, partial(take_down, patience=patience))
        agent.load()
        # The mic opens first, so it's ready the moment she's said the prompt
        # (she mutes it while speaking). There's no trigger: START starts the flow.
        agent.start_listening()
        agent.handle_utterance(START)
        agent.on_heard(lambda text: print(f"You: {text}"))  # Set after START, to leave it out.
        done.wait()
    return heard[0] if heard else None


def main():
    parser = argparse.ArgumentParser(
        prog="calypso-cli",
        description="Calypso, and her voice and ears for the commands in calypso.toml.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="beep whenever she has understood you or not, and print Jev's judgments",
    )
    subcommands = parser.add_subparsers(dest="subcommand", required=True)
    subcommands.add_parser(
        "assistant", help="run Calypso: listen for her trigger and do what you ask"
    )
    subcommands.add_parser(
        "config", help="set her up in calypso.toml: names, languages, voice and trigger, tested live"
    )
    saying = subcommands.add_parser("say", help="say a text with her voice")
    saying.add_argument("text", nargs="?", help="what to say; read from stdin if left out")
    listening = subcommands.add_parser(
        "transcribe", help="listen until you've finished your sentence, and print it"
    )
    listening.add_argument("prompt", nargs="?", default="", help="what to say first, once listening")
    args = parser.parse_args()

    try:
        if args.subcommand == "config":
            config.configure()  # No setup(): it can fix the settings setup() rejects.
            return
        if args.subcommand == "assistant":
            calypso.run_assistant(args.debug)
            return
        calypso.setup(args.debug)
        if args.subcommand == "say":
            text = sys.stdin.read() if args.text is None else args.text
            if text.strip():
                say(text.strip())
        else:
            # Only the sentence goes to stdout, for files and pipes; everything
            # else she prints, like what she hears and says, goes to stderr.
            with contextlib.redirect_stdout(sys.stderr):
                sentence = transcribe(args.prompt, args.debug)
            if sentence is None:
                sys.exit(1)
            print(sentence)
    except KeyboardInterrupt:
        sys.exit(130)
    finally:
        calypso.jev.close()


if __name__ == "__main__":
    main()
