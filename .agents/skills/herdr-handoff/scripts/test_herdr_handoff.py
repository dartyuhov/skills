"""Offline contracts for the bundled helper; never create panes or agents."""

import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "handoff", Path(__file__).with_name("herdr-handoff.py")
)
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)


class DeliveryTests(unittest.TestCase):
    def run_delivery(self, prompt_error=False, state="working", busy=False):
        calls = []

        def fake(*args, **kwargs):
            calls.append(args)
            if args[:2] == ("pane", "split"):
                self.assertIn("--no-focus", args)
                return {"pane": {"pane_id": "returned-pane"}}
            if args[:2] == ("agent", "start"):
                self.assertIn("returned-pane", args)
                self.assertEqual(args[-2:], ("--", "--auto"))
                if busy and sum(c[:2] == ("agent", "start") for c in calls) == 1:
                    raise handoff.HandoffError("agent_pane_busy")
            if args[:2] == ("agent", "prompt"):
                self.assertEqual(args[3], "literal $summary\nwith quotes")
                self.assertIn("working", args)
                if prompt_error:
                    raise handoff.HandoffError("timeout")
            if args[:2] == ("agent", "get"):
                return {"agent": {"agent_status": state}}
            return {}

        report = {}
        with patch.dict(os.environ, HERDR_ENV="1"), \
             patch.object(handoff, "call", side_effect=fake), \
             patch.object(handoff, "wait_shell") as shell, \
             patch.object(handoff, "wait_input") as input_ready:
            try:
                handoff.deliver("literal $summary\nwith quotes", report)
            except handoff.HandoffError as error:
                report["error"] = str(error)
            self.assertTrue(shell.called)
            self.assertTrue(input_ready.called)
        self.assertEqual(sum(c[:2] == ("agent", "prompt") for c in calls), 1)
        return report, calls

    def test_success_stops_after_acceptance(self):
        report, calls = self.run_delivery()
        self.assertEqual(report["status"], "accepted")
        self.assertEqual(calls[-1][:2], ("agent", "prompt"))

    def test_busy_retries_start_not_split(self):
        report, calls = self.run_delivery(busy=True)
        self.assertEqual(report["status"], "accepted")
        self.assertEqual(sum(c[:2] == ("agent", "start") for c in calls), 2)
        self.assertEqual(sum(c[:2] == ("pane", "split") for c in calls), 1)

    def test_timeout_checks_activity_without_resending(self):
        report, _ = self.run_delivery(prompt_error=True)
        self.assertEqual(report["status"], "accepted")

    def test_idle_timeout_is_not_success(self):
        report, _ = self.run_delivery(prompt_error=True, state="idle")
        self.assertEqual(report["error"], "prompt_acceptance_unconfirmed_do_not_resend")
        self.assertNotIn("status", report)

    def test_outside_herdr_does_not_create_pane(self):
        with patch.dict(os.environ, HERDR_ENV="0"), patch.object(handoff, "call") as call:
            with self.assertRaisesRegex(handoff.HandoffError, "requires_herdr"):
                handoff.deliver("summary", {})
            call.assert_not_called()

    def test_direnv_child_is_not_ready(self):
        data = {"process_info": {"shell_pid": 1, "foreground_processes": [
            {"pid": 1}, {"pid": 2},
        ]}}
        with patch.object(handoff, "call", return_value=data), \
             patch.object(handoff, "screen") as screen:
            self.assertFalse(handoff.shell_ready("pane"))
            screen.assert_not_called()

    def test_shell_requires_visible_prompt(self):
        data = {"process_info": {"shell_pid": 1, "foreground_processes": [{"pid": 1}]}}
        with patch.object(handoff, "call", return_value=data), \
             patch.object(handoff, "screen", return_value="direnv: loading environment"):
            self.assertFalse(handoff.shell_ready("pane"))
        with patch.object(handoff, "call", return_value=data), \
             patch.object(handoff, "screen", return_value="direnv: done\n➜ ~/repo git:main"):
            self.assertTrue(handoff.shell_ready("pane"))

    def test_shell_timeout_is_bounded(self):
        with patch.object(handoff.time, "monotonic", return_value=11):
            with self.assertRaisesRegex(handoff.HandoffError, "10_seconds"):
                handoff.wait_shell("pane", 10)

    def test_input_waits_for_loaded_screen_twice(self):
        agent = {"agent": {"agent_status": "idle", "interactive_ready": True}}
        with patch.object(handoff, "call", return_value=agent), \
             patch.object(handoff, "screen", side_effect=[
                 "loading", "Ask anything tab agents", "Ask anything tab agents",
             ]) as screen, patch.object(handoff.time, "sleep"):
            handoff.wait_input("receiver", "pane")
            self.assertEqual(screen.call_count, 3)

    def test_input_block_does_not_send_keys(self):
        with patch.object(handoff, "call", return_value={
            "agent": {"agent_status": "blocked"},
        }) as call:
            with self.assertRaisesRegex(handoff.HandoffError, "requires_user"):
                handoff.wait_input("receiver", "pane")
            self.assertEqual(call.call_count, 1)


if __name__ == "__main__":
    unittest.main()
