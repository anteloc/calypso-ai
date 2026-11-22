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
import sys
import threading
from functools import partial

from moonshine_voice import TextToSpeech
from typesafe_sdk import Noul, NoulCriteria

import config
import main as calypso

START = "calypso-cli transcribe"  # Fed to the agent to start listening at once.

# What we ask Jev about dictation, with what she asked (if anything) as context.
# Not Calypso's "finished" question: that one wants a complete request, and
# notes are often just "milk and eggs".
DICTATION = {
    "finished": Noul(
        instructions=(
            "Has the user finished what they're saying in `said`, rather than stopping part-way "
            "through it? It comes from live speech recognition, so ignore its punctuation."
        ),
        criteria=NoulCriteria(
            true="A complete thought, even a short one or one without a verb, such as 'call the bank' or 'tea and biscuits'",
            false="Cut off or trailing off part-way, such as 'call the' or 'tea and'",
        ),
    ),
    "quits": calypso.JUDGMENTS["quits"],
}


def judge_dictation(asked, said):
    """Ask Jev whether the user has finished what they're dictating, and whether they quit."""
    # Speech recognition ends every line with a full stop, which makes a
    # fragment like "call the plumber on." look finished to Jev.
    said = said.rstrip(". ")
    nouls = calypso.jev.system_one(state={"asked": asked, "said": said}, questions=DICTATION).nouls
    finished, quits = nouls["finished"].noul, nouls["quits"].noul
    calypso.log.debug(f"Jev on {said!r}: {finished:.0%} finished, {quits:.0%} quitting")
    return finished > calypso.JEV_THRESHOLD, quits > calypso.JEV_THRESHOLD, None


def say(text):
    """Say `text` with her voice, $user_name and $assistant_name filled in."""
    settings = calypso.CONFIG
    language, voice_id = settings["assistant_language"], settings["assistant_voice"]
    with TextToSpeech().language(language).voice(voice_id) as voice:
        voice.load()
        voice.say(config.fill(text, settings))
        voice.wait()


def transcribe(prompt, debug):
    """Say `prompt` (if any), and listen until the user has finished their sentence.

    Returns the sentence, or None if they called it off or went quiet.
    """
    prompt = config.fill(prompt, calypso.CONFIG)
    heard = []
    done = threading.Event()

    def take_down(d, patience):
        try:
            sentence, _ = yield from calypso.listen(d, patience, prompt, partial(judge_dictation, prompt))
            heard.append(sentence)
        finally:  # Also when Patience gives up and ends the flow.
            done.set()

    with calypso.assistant(debug) as (agent, patience):
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
