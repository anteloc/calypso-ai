"""calypso.toml: Calypso's settings and commands, and the --config mode that sets them up.

In text settings, $user_name and $assistant_name stand for their values (see fill()).
"""

import queue
import random
import tomllib
from pathlib import Path
from string import Template

import langcodes
import questionary
import tomlkit
from moonshine_voice import (
    AgentFlow,
    MicTranscriber,
    TextToSpeech,
    get_tts_voice_catalog,
    supported_languages,
)

PATH = Path(__file__).with_name("calypso.toml")

# Calypso's settings, with the defaults for any that calypso.toml leaves out.
DEFAULTS = {
    "user_name": "",
    "user_language": "en",
    "assistant_name": "Calypso",
    "assistant_language": "en-gb",
    "assistant_voice": "kokoro_bf_isabella",
    "trigger": "$assistant_name",
    "quit_intent": ["nah, forget it", "leave it be", "better don't do anything"],
    "trigger_ack": ["Yes?"],
    "nudge": ["And...?"],
    "goodbye": ["Ok, call me if you need something else."],
    "quit_ack": ["Sure! We'll leave it here."],
    "dont_know": ["I don't know how to do that."],
}

# Her phrases: each setting is a list, and she says one of them, picked at random.
PHRASES = {
    "trigger_ack": "What she answers when woken:",
    "nudge": "What she says when you go quiet mid-sentence:",
    "goodbye": "What she says when she stops waiting for the rest:",
    "quit_ack": "What she says when you call it off:",
    "dont_know": "What she says when no command does what you asked:",
}

# The settings that are lists of phrases: hers, and the quit_intent examples.
LISTS = (*PHRASES, "quit_intent")
QUIT_QUESTION = "What you say to call a request off (examples, separated by |):"

TRIES = 3  # Times you say the trigger when testing it.
TRY_FOR = 15  # Seconds she waits for each try.
TRIGGER_QUESTION = "What you say to wake her up ($assistant_name is her name):"


def load():
    """calypso.toml's settings and commands, with defaults for missing settings."""
    settings = DEFAULTS | tomllib.loads(PATH.read_text())
    for key in LISTS:
        if isinstance(settings[key], str):  # A single phrase is a list of one.
            settings[key] = [settings[key]]
    return settings


def save(settings):
    """Write the settings into calypso.toml, keeping its comments and commands."""
    document = tomlkit.parse(PATH.read_text())
    for key in DEFAULTS:
        document[key] = settings[key]
    PATH.write_text(tomlkit.dumps(document))


def fill(text, settings, speech=""):
    """`text` with $user_name, $assistant_name and $speech (what the user said) filled in."""
    return Template(text).safe_substitute(
        user_name=settings["user_name"], assistant_name=settings["assistant_name"], speech=speech
    )


def one_of(settings, key, speech=""):
    """One of her phrases for `key`, such as "nudge", picked at random and filled in."""
    return fill(random.choice(settings[key]), settings, speech)


def kokoro_voices(language):
    """Moonshine's kokoro voices for a speaking language, such as "en-gb"."""
    entries = get_tts_voice_catalog().get(language, [])
    return [entry.id for entry in entries if entry.id.startswith("kokoro_")]


def configure():
    """Ask for each setting, test the trigger, and save them in calypso.toml."""
    settings = load()
    print(f"Setting up {PATH.name}. Enter keeps a value; Ctrl+C quits without saving.\n")
    try:
        settings["user_name"] = ask("Your name (optional):", settings["user_name"])
        settings["user_language"] = pick_language(
            "The language you speak:", supported_languages(), settings["user_language"]
        )
        settings["assistant_name"] = ask("Her name:", settings["assistant_name"], required=True)
        speaking = [language for language in get_tts_voice_catalog() if kokoro_voices(language)]
        settings["assistant_language"] = pick_language(
            "The language she speaks:", speaking, settings["assistant_language"]
        )
        settings["trigger"] = ask(TRIGGER_QUESTION, settings["trigger"], required=True)
        settings["quit_intent"] = ask_phrases(QUIT_QUESTION, settings["quit_intent"])
        print(
            "\nHer phrases: give several by separating them with |, and she picks one at random.\n"
            "$user_name and $assistant_name stand for the names, anywhere in a phrase."
        )
        for key, question in PHRASES.items():
            settings[key] = ask_phrases(question, settings[key])
        settings["assistant_voice"] = pick_voice(settings)
        check_trigger(settings)
    except KeyboardInterrupt:
        print("\nNothing saved.")
        return
    save(settings)
    print(
        f"\nSaved in {PATH.name}. Run `uv run calypso-cli assistant` (or `uv run main.py`) "
        f"to talk to {settings['assistant_name']}."
    )


def ask(question, default, required=False):
    """Ask for a line of text; Enter keeps `default`."""

    def valid(answer):
        return bool(answer.strip()) or not required or "This one can't be empty."

    return questionary.text(question, default=default, validate=valid).unsafe_ask().strip()


def ask_phrases(question, current):
    """Ask for one phrase or more, separated by |; Enter keeps `current`."""
    answer = ask(question, " | ".join(current), required=True)
    return [phrase.strip() for phrase in answer.split("|") if phrase.strip()] or current


def pick_language(question, languages, current):
    """Pick one of `languages` (codes such as "en-gb"), shown by name."""
    choices = [
        questionary.Choice(langcodes.Language.get(code).display_name(), value=code)
        for code in languages
    ]
    default = current if current in languages else None
    return questionary.select(question, choices, default=default).unsafe_ask()


def pick_voice(settings):
    """Let the user hear her kokoro voices saying the trigger acks, and pick one."""
    voices = kokoro_voices(settings["assistant_language"])
    voice = settings["assistant_voice"] if settings["assistant_voice"] in voices else voices[0]
    phrases = [fill(ack, settings) for ack in settings["trigger_ack"]]
    while True:
        choices = [questionary.Choice(voice_name(v), value=v) for v in voices]
        voice = questionary.select("Her voice (pick one to hear it):", choices, default=voice).unsafe_ask()
        with TextToSpeech().language(settings["assistant_language"]).voice(voice) as speaker:
            speaker.load()  # Downloads the voice the first time.
            for phrase in phrases:
                speaker.say(phrase)
            speaker.wait()
        if questionary.confirm("Keep this voice?").unsafe_ask():
            return voice


def voice_name(voice):
    """A kokoro voice id such as kokoro_bf_isabella, as "Isabella (female)".

    Kokoro ids are kokoro_<language letter><f or m>_<name>.
    """
    _, kind, name = voice.split("_", 2)
    return f"{name.title()} ({'female' if kind[1] == 'f' else 'male'})"


def check_trigger(settings):
    """Test the trigger until she wakes up every time, or the user keeps or changes it."""
    print("\nLoading speech recognition and her voice, to test the trigger...")
    mic = MicTranscriber().language(settings["user_language"])
    mic.load()
    voice = TextToSpeech().language(settings["assistant_language"]).voice(settings["assistant_voice"])
    voice.load()
    try:
        while True:
            woke = test_trigger(settings, mic, voice)
            if woke == TRIES:
                print("She woke up every time.")
                return
            print(f"She woke up {woke} of {TRIES} times, so she may not hear you.")
            next_step = questionary.select(
                "What now?", ["Test it again", "Change the trigger", "Keep it anyway"]
            ).unsafe_ask()
            if next_step == "Keep it anyway":
                return
            if next_step == "Change the trigger":
                settings["trigger"] = ask(TRIGGER_QUESTION, settings["trigger"], required=True)
    finally:
        mic.close()
        voice.close()


def test_trigger(settings, mic, voice):
    """Have the user say the trigger TRIES times; return how many times she woke up."""
    trigger = fill(settings["trigger"], settings)
    tries = queue.Queue()  # (what she heard, whether she woke up)
    heard = []

    def wake(d):
        tries.put((heard[-1], True))
        yield d.say(one_of(settings, "trigger_ack"))

    # Built like the agent in main.py, so she recognizes the trigger the same way.
    agent = (
        AgentFlow()
        .language(settings["user_language"])
        .use_text_to_speech(voice)
        .use_mic_transcriber(mic)
        .beeps(False)
        .on_heard(heard.append)
        .otherwise(lambda said: tries.put((said, False)))
        .listen_for(trigger, wake)
    )
    agent.load()
    agent.start_listening()
    print(f'\nSay "{trigger}" {TRIES} times, pausing after each.')
    woke = 0
    try:
        for _ in range(TRIES):
            try:
                said, woken = tries.get(timeout=TRY_FOR)
            except queue.Empty:
                print(f"  Heard nothing for {TRY_FOR} seconds.")
                continue
            print(f'  Heard "{said}": {"she woke up" if woken else "not her trigger"}')
            woke += woken
    finally:
        agent.close()
    return woke
