"""Calypso: a voice-controlled assistant built on Moonshine Voice.

Say "Calypso" to get her attention, and she answers "Yes?". Then ask one of
the questions in ANSWERS below; any phrasing with the same meaning works.
She speaks the answer in a British voice and prints the conversation.

She waits until you've finished your sentence, so you can stop to think:
TypeSafe's Jev judges whether what you've said so far is finished. If you go
quiet mid-sentence she asks "And...?", and a little later she lets it go.

Run with `uv run main.py`, with TYPESAFE_API_KEY set for Jev. The first run
downloads the speech models.
"""

import threading
import time
from datetime import datetime
from functools import partial

from moonshine_voice import (
    AgentFlow,
    CachedEmbeddings,
    EmbeddingModel,
    MicTranscriber,
    PhraseMatcher,
    TextToSpeech,
    TranscriptEventListener,
    get_embedding_model,
)
from typesafe_sdk import Noul, NoulCriteria, TypeSafeClient

NAME = "Calypso"  # Her name is also her wake word.
NUDGE_AFTER = 4  # Seconds of silence before she asks "And...?".
GIVE_UP_AFTER = 7  # Seconds of silence before she drops an unfinished sentence.
FINISHED_THRESHOLD = 0.7  # How sure Jev must be that you've finished.


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


jev = TypeSafeClient()  # Reads TYPESAFE_API_KEY.

# The one judgment we ask Jev for. A Noul answers with the probability of yes.
FINISHED = Noul(
    instructions=(
        "Has the user finished saying what they want, so the assistant can act on it? "
        "The text comes from live speech recognition, so ignore its punctuation."
    ),
    criteria=NoulCriteria(
        true="A complete question or request, such as 'what time is it'",
        false="Cut off or trailing off mid-sentence, such as 'what's the' or 'can you tell me'",
    ),
)


def is_finished(sentence):
    """Ask Jev whether the user has finished their sentence."""
    response = jev.system_one(state=sentence, questions={"finished": FINISHED})
    finished = response.nouls["finished"].noul
    print(f"Jev: {finished:.0%} finished")
    return finished > FINISHED_THRESHOLD


class Patience(TranscriptEventListener):
    """Gives the user time to finish a sentence.

    Started when Jev says the sentence isn't finished: after NUDGE_AFTER
    seconds of silence Calypso asks "And...?", and after GIVE_UP_AFTER she
    drops the sentence. Stopped as soon as the user starts talking again.

    AgentFlow doesn't enforce the timeouts of ask() yet (moonshine-voice
    0.1.6), so we time the silence ourselves.
    """

    def __init__(self, agent):
        self.agent = agent
        self.timers = []

    def start(self):
        self.stop()
        self.timers = [
            threading.Timer(NUDGE_AFTER, self.agent.say, ["And...?"]),
            threading.Timer(GIVE_UP_AFTER, self.give_up),
        ]
        for timer in self.timers:
            timer.start()

    def stop(self):
        for timer in self.timers:
            timer.cancel()

    def give_up(self):
        self.agent.say("Ok, call me if you need something else.")
        self.agent.cancel()  # Drops the unfinished sentence.

    def on_line_started(self, event):
        self.stop()  # The user is talking again.


def converse(d, patience, questions):
    """Flow started by the wake word: listen until the user has finished, then answer."""
    sentence = yield d.ask("Yes?")
    while not is_finished(sentence):
        patience.start()
        rest = yield d.ask("")  # Keep listening, without a word.
        sentence = f"{sentence} {rest}"

    question = questions.match(sentence)
    if question is None:
        # Nothing in ANSWERS matched. An LLM would take over here later.
        yield d.say("Sorry, I can't help with that yet.")
        return
    yield d.say(ANSWERS[question]())


def main():
    # We bring our own synthesizer because AgentFlow.language() sets the
    # language for both listening and speaking. We listen in "en" but speak en_gb.
    voice = TextToSpeech().language("en_gb").voice("kokoro_bf_isabella")
    voice.load()

    # Our own microphone, so Patience hears when you start talking again, and
    # our own phrase model, so converse can match your whole sentence. The
    # agent shares both instead of opening its own.
    mic = MicTranscriber().language("en")
    mic.load()
    embedding_model = EmbeddingModel(*get_embedding_model())
    meaning = CachedEmbeddings(fallback=embedding_model)

    agent = (
        AgentFlow()
        .language("en")
        .use_text_to_speech(voice)
        .use_mic_transcriber(mic)
        .use_cached_embeddings(meaning)
        .on_heard(lambda text: print(f"You: {text}"))
        .on_said(lambda text: print(f"{NAME}: {text}"))
    )
    patience = Patience(agent)
    mic.add_listener(patience)
    # Matched by meaning, the way d.choose() matches a single line.
    questions = PhraseMatcher(meaning, {q: [q] for q in ANSWERS})
    agent.listen_for(NAME, partial(converse, patience=patience, questions=questions))

    agent.load()
    agent.start_listening()
    print(f'Say "{NAME}" to wake her up. Press Ctrl+C to stop.')

    try:
        while True:
            time.sleep(0.1)  # Speech is handled on the audio thread.
    except KeyboardInterrupt:
        pass
    finally:
        patience.stop()
        agent.close()
        # The agent doesn't close what it didn't create.
        mic.close()
        embedding_model.close()
        voice.close()
        jev.close()


if __name__ == "__main__":
    main()
