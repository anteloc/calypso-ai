"""Calypso: a voice-controlled assistant built on Moonshine Voice.

Say "Calypso" to get her attention, and she answers "Yes?". Then ask one of
the questions in ANSWERS below; any phrasing with the same meaning works.
She speaks the answer in a British voice and prints the conversation.

Run with `uv run main.py`. The first run downloads the speech models.
"""

import time
from datetime import datetime

from moonshine_voice import AgentFlow, NoMatchError, TextToSpeech

NAME = "Calypso"  # Her name is also her wake word.


def time_now():
    # Written the way it's said ("9 oh 5 in the morning"). Text to speech
    # misreads "9:05" and reads "AM" as the word "am".
    now = datetime.now()
    hour = now.hour % 12 or 12
    if now.minute == 0:
        minutes = "o'clock"
    elif now.minute < 10:
        minutes = f"oh {now.minute}"
    else:
        minutes = str(now.minute)
    part = "morning" if now.hour < 12 else "afternoon" if now.hour < 18 else "evening"
    return f"It's {hour} {minutes} in the {part}."


def date_today():
    today = datetime.now()
    return f"Today is {today:%A} {today.day} {today:%B}."


def introduce():
    return f"I'm {NAME}, your voice assistant."


# What Calypso can answer: a question, matched by meaning, and the function
# that writes the spoken reply. To teach her something new, add a line here.
ANSWERS = {
    "What time is it?": time_now,
    "What's the date today?": date_today,
    "Who are you?": introduce,
}


def converse(d):
    """Flow started by the wake word: ask what the user wants, then answer."""
    try:
        # Each question in ANSWERS is an option, matched by itself.
        question = yield d.choose("Yes?", {q: [] for q in ANSWERS})
    except NoMatchError:
        # Nothing in ANSWERS matched, even after the built-in retries.
        # An LLM would take over here later.
        yield d.say("Sorry, I can't help with that yet.")
        return
    yield d.say(ANSWERS[question]())


def main():
    # We bring our own synthesizer because AgentFlow.language() sets the
    # language for both listening and speaking. We listen in "en" but speak en_gb.
    voice = TextToSpeech().language("en_gb").voice("kokoro_bf_isabella")
    voice.load()

    agent = (
        AgentFlow()
        .language("en")
        .use_text_to_speech(voice)
        .on_progress(lambda fraction, name: print(f"Loading {name}... {fraction:.0%}"))
        .on_heard(lambda text: print(f"You: {text}"))
        .on_said(lambda text: print(f"{NAME}: {text}"))
        .listen_for(NAME, converse)
    )
    agent.load()
    agent.start_listening()
    print(f'Say "{NAME}" to wake her up. Press Ctrl+C to stop.')

    try:
        while True:
            time.sleep(0.1)  # Speech is handled on the audio thread.
    except KeyboardInterrupt:
        pass
    finally:
        agent.close()
        voice.close()  # The agent doesn't close a voice it didn't create.


if __name__ == "__main__":
    main()
