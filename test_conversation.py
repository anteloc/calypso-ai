"""Drive the real Moonshine dialog with text, a manual clock and local Jev decisions."""

import os
import unittest
from contextlib import contextmanager
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

with patch.dict(os.environ, TYPESAFE_API_KEY="offline-test"):
    import main
    import cli
import config


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.timers = []
        self.spoken = []
        self.errors = []
        self.mic_muting = []
        self.steps = [{"run": "true"}]
        self.agent = (
            main.CalypsoAgent().microphone(False).speech(False).use_embeddings(False).beeps(False)
            .speak_with(self.spoken.append).on_error(self.errors.append)
        )
        self.patience = main.Patience(self.agent)
        self.agent.listen_for("Calypso", partial(main.converse, patience=self.patience, mute=self.mic_muting.append))
        self.addCleanup(self.agent.close)
        self.addCleanup(self.agent.cancel)
        self.enterContext(patch("main.CONFIG", config.DEFAULTS))
        self.enterContext(patch("main.threading.Timer", side_effect=self.timer))
        self.command = {"description": "Test command", "steps": self.steps}
        self.enterContext(patch("main.COMMANDS", [self.command]))
        self.jev = self.enterContext(patch.object(main.jev, "system_one", side_effect=self.score))

    def timer(self, seconds, callback):
        # fire() may be called after cancel() to exercise a callback already in flight.
        timer = SimpleNamespace(seconds=seconds, fire=callback, start=lambda: None, cancel=lambda: None)
        self.timers.append(timer)
        return timer

    def score(self, *, state, questions):
        self.command["steps"] = self.steps
        latest = state["latest"]
        probabilities = {key: 0.0 for key in questions if key != "restart"}
        probabilities["finished"] = float(not latest.endswith("...") and latest != "Search on the")
        probabilities["quits"] = float(latest == "forget it")
        if "command 0" in questions:
            probabilities["command 0"] = float(state["said"] != "unmatched request")
        if "coherent" in questions:
            probabilities["coherent"] = float(latest != "word salad")
        restart = {"start over": "conversation", "let me say that again": "answer"}.get(latest, "neither")
        return SimpleNamespace(
            nouls={key: SimpleNamespace(noul=p) for key, p in probabilities.items()},
            choices={"restart": SimpleNamespace(choice=restart, probabilities={restart: 1.0})},
        )

    def hear(self, *lines):
        for line in lines:
            self.patience.on_line_started(None)
            self.agent.handle_utterance(line)
            self.assertEqual(self.errors, [])

    def test_consecutive_questions_and_ordered_scripts(self):
        self.steps = [
            {"ask": "Where?", "save_as": "destination"},
            {"ask": "When for $destination?", "save_as": "dates"},
            {"ask": "What activity?", "save_as": "activity"},
            {"run": '''printf '%s' "$activity" > "$out"'''},
            {"ask": "Anything else for $dates?", "save_as": "note"},
            {"run": '''printf '|%s|%s' "$note" "$speech" >> "$out"'''},
            {"say": "Saved $destination for $dates."},
        ]
        with TemporaryDirectory() as directory:
            out = Path(directory) / "trip"
            self.enterContext(patch.dict(os.environ, out=str(out)))
            self.hear("Calypso", "save a trip", "Menorca")
            self.assertEqual(self.spoken[-1], "When for Menorca?")
            self.hear("I'd like...")
            self.timers[-1].fire()
            self.hear("to travel...")
            state = self.jev.call_args.kwargs["state"]
            self.assertEqual(state["asked"], "When for Menorca?")
            self.assertEqual(state["earlier"], "I'd like...")
            self.assertEqual(state["latest"], "to travel...")
            self.assertFalse(out.exists())
            self.assertNotIn("What activity?", self.spoken)
            self.hear("next June")
            self.assertEqual(self.spoken[-1], "What activity?")
            activity = """R&D "walks" + 50%? #café $(echo unexpected) $speech"""
            self.hear(activity)
            self.assertEqual(out.read_text(), activity)
            self.assertEqual(self.spoken[-1], "Anything else for I'd like... to travel... next June?")
            self.hear("open the calendar")
            self.assertEqual(out.read_text(), activity + "|open the calendar|save a trip")
            self.assertEqual(self.spoken[-1], "Saved Menorca for I'd like... to travel... next June.")
            self.assertEqual(sum("command 0" in call.kwargs["questions"] for call in self.jev.call_args_list), 1)
            self.assertEqual(self.mic_muting, [True, False, True, False])
            self.assertFalse(self.agent.is_active)

    def test_silence_before_and_during_an_answer(self):
        self.steps = [
            {"ask": "First?", "save_as": "first"},
            {"ask": "Second?", "save_as": "second"},
            {"say": "Done"},
        ]
        self.hear("Calypso")
        wake = self.spoken[-1]
        reminder = self.timers[-1]
        self.assertEqual(reminder.seconds, 4)
        reminder.fire()
        self.assertEqual(self.spoken, [wake, wake])
        expired = self.timers[-1]
        self.assertEqual(expired.seconds, 7)
        self.hear("ask me", "one")
        expired.fire()
        self.assertEqual(self.spoken[-1], "Second?")
        self.hear("part...")
        self.timers[-1].fire()
        self.assertEqual(self.spoken[-1], main.one_of("nudge", "part..."))
        self.timers[-1].fire()
        self.assertEqual(self.spoken[-1], main.one_of("goodbye", "part..."))
        self.assertFalse(self.agent.is_active)
        self.assertNotIn("Done", self.spoken)

    def test_a_matching_opening_fragment_waits_for_completion(self):
        self.steps = [{"ask": "Search for what?", "save_as": "query"}]
        self.hear("Calypso", "Search on the")
        self.assertNotIn("Search for what?", self.spoken)
        self.timers[-1].fire()
        self.hear("internet")
        self.assertEqual(self.jev.call_args.kwargs["state"]["said"], "Search on the internet")
        self.assertEqual(self.spoken[-1], "Search for what?")
        self.timers[-1].fire()
        self.assertEqual(self.spoken[-2:], ["Search for what?", "Search for what?"])
        self.timers[-1].fire()
        self.assertFalse(self.agent.is_active)
        self.assertEqual(self.jev.call_count, 2)

    def test_quit_and_restart_discard_answers(self):
        self.steps = [
            {"ask": "Where?", "save_as": "place"},
            {"ask": "When for $place?", "save_as": "date"},
            {"say": "Saved $place $date"},
        ]
        self.hear("Calypso", "plan", "Rome", "forget it")
        self.assertEqual(self.spoken[-1], main.one_of("quit_ack", "forget it"))
        self.assertFalse(self.agent.is_active)
        self.hear("Calypso", "plan", "Paris", "start over")
        self.assertEqual(self.spoken[-2:], [main.one_of("restart_ack"), main.one_of("trigger_ack")])
        self.hear("plan", "London", "tomorrow")
        self.assertEqual(self.spoken[-1], "Saved London tomorrow")
        self.assertFalse(self.agent.is_active)

    def test_rephrasing_and_garbled_replies_retry_only_the_current_question(self):
        self.steps = [
            {"ask": "Where?", "save_as": "place"},
            {"ask": "When for $place?", "save_as": "date"},
            {"say": "Saved $place $date"},
        ]
        self.hear("Calypso", "plan", "Paris", "I might...", "let me say that again")
        self.assertEqual(self.spoken[-2:], [main.one_of("rephrase_ack"), "When for Paris?"])
        self.hear("garbled...")
        self.assertNotIn("earlier", self.jev.call_args.kwargs["state"])
        self.assertNotIn("coherent", self.jev.call_args.kwargs["questions"])
        stale = self.timers[-1]
        self.hear("word salad")
        self.assertEqual(self.spoken[-1], main.one_of("ask_again"))
        stale.fire()
        self.hear("tomorrow")
        self.assertEqual(self.jev.call_args.kwargs["state"]["asked"], "When for Paris?")
        self.assertNotIn("earlier", self.jev.call_args.kwargs["state"])
        self.assertEqual(self.spoken[-1], "Saved Paris tomorrow")

    def test_garbled_opening_retries_without_another_wake_word(self):
        self.steps = [{"say": "Heard $speech"}]
        self.hear("Calypso", "garbled...", "word salad")
        self.assertTrue(self.agent.is_active)
        self.assertEqual(self.spoken[-1], main.one_of("ask_again"))
        self.hear("another request")
        self.assertEqual(self.spoken[-1], "Heard another request")

    def test_standalone_dictation_finishes_after_restarts_and_a_garbled_pair(self):
        @contextmanager
        def assistant(debug):
            dispatch = self.agent.handle_utterance

            def dictate(trigger):
                dispatch(trigger)
                for text in ("start over", "let me say that again", "garbled...", "word salad", "fresh text"):
                    self.patience.on_line_started(None)
                    dispatch(text)
                    self.assertEqual(self.errors, [])

            with patch.object(self.agent, "start_listening"), patch.object(self.agent, "handle_utterance", dictate):
                yield self.agent, self.patience, self.mic_muting.append

        with patch.object(main, "assistant", assistant):
            self.assertEqual(cli.transcribe("What text?", False), "fresh text")
        self.assertEqual(self.spoken, [
            "What text?", main.one_of("restart_ack"), "What text?",
            main.one_of("rephrase_ack"), "What text?", main.one_of("ask_again"),
        ])

    def test_blank_recognition_resumes_the_current_deadline(self):
        self.hear("Calypso")
        self.timers[-1].fire()
        self.patience.on_line_started(None)
        self.patience.on_line_completed(SimpleNamespace(line=SimpleNamespace(text=" ")))
        self.assertEqual(self.timers[-1].seconds, 7)
        self.timers[-1].fire()
        self.assertFalse(self.agent.is_active)

    def test_no_match_and_script_failure(self):
        self.hear("Calypso", "unmatched request")
        self.assertEqual(self.spoken[-1], main.one_of("dont_know", "unmatched request"))
        self.steps = [{"run": "exit 23"}, {"say": "Done"}]
        with self.assertLogs("calypso", level="ERROR") as logged:
            self.hear("Calypso", "try it")
        self.assertIn("run step 1", logged.output[0])
        self.assertIn("23", logged.output[0])
        self.assertEqual(self.mic_muting, [True, False])
        self.assertNotIn("Done", self.spoken)
        self.assertFalse(self.agent.is_active)


class ConfigTests(unittest.TestCase):
    def test_existing_config_gets_recovery_defaults_and_saves_custom_phrase_lists(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "calypso.toml"
            path.write_text('assistant_name = "Calypso"\n')
            with patch.object(config, "PATH", path):
                settings = config.load()
                self.assertIn("let me say that again", settings["restart_intent"])
                self.assertEqual(settings["ask_again"], ["I don't get it, could you say it again?"])
                settings["restart_intent"] = ["from the top", "I'll reword it"]
                settings["ask_again"] = ["One more time?", "I heard $speech. Say it again?"]
                config.save(settings)
                saved = config.load()
                self.assertEqual(saved["restart_intent"], settings["restart_intent"])
                self.assertEqual(saved["ask_again"], settings["ask_again"])
                with patch("config.random.choice", return_value=saved["ask_again"][1]):
                    self.assertEqual(config.one_of(saved, "ask_again", "noise"), "I heard noise. Say it again?")

    def test_unknown_ambiguous_and_legacy_steps(self):
        ask = {"ask": "Where?", "save_as": "place"}
        for steps in ([], [{"ask": "Where?"}], [ask, ask], [{"say": "$later"}],
                      [{"say": "Hello", "run": "true"}], [ask | {"save_as": "speech"}],
                      [ask | {"save_as": "PATH"}]):
            with self.subTest(steps=steps), self.assertRaisesRegex(SystemExit, "command 1"):
                config.validate_commands([{"description": "Trip", "steps": steps}])
        with self.assertRaisesRegex(SystemExit, "move command-level ack and run into steps"):
            config.validate_commands([{"description": "Trip", "run": "true", "ack": "OK"}])


if __name__ == "__main__":
    unittest.main()
