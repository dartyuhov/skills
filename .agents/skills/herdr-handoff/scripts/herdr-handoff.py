#!/usr/bin/env python3
"""Deliver a stdin handoff to a sibling OpenCode pane without creating files.

Run from the repository being handed off, not the skill directory.
"""

import json
import os
import re
import subprocess
import sys
import time
import uuid


class HandoffError(Exception):
    pass


def call(*args, timeout=15):
    """Keep raw terminal/process output private; callers receive parsed data."""
    try:
        result = subprocess.run(
            ["herdr", *args], capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise HandoffError("herdr_unavailable_or_timed_out") from None
    try:
        data = json.loads(result.stdout or result.stderr)
    except ValueError:
        raise HandoffError("invalid_herdr_response") from None
    if result.returncode or "error" in data:
        # Error messages and process details may contain sensitive arguments.
        raise HandoffError(data.get("error", {}).get("code", "herdr_failed"))
    return data["result"]


def screen(pane):
    try:
        result = subprocess.run(
            ["herdr", "pane", "read", pane, "--source", "recent-unwrapped",
             "--lines", "35"], capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise HandoffError("screen_read_failed") from None
    if result.returncode:
        raise HandoffError("screen_read_failed")
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", result.stdout)


def shell_ready(pane):
    info = call("pane", "process-info", "--pane", pane)["process_info"]
    processes = info.get("foreground_processes", [])
    # A running direnv child can share the shell's process group. Require the
    # shell itself, with no foreground children, plus a visible prompt.
    if not processes or any(p.get("pid") != info.get("shell_pid") for p in processes):
        return False
    lines = [line.strip() for line in screen(pane).splitlines() if line.strip()]
    return bool(lines and re.search(r"[❯➜→➤›❱$%#>]", lines[-1]))


def wait_shell(pane, deadline):
    stable = 0
    while time.monotonic() < deadline:
        stable = stable + 1 if shell_ready(pane) else 0
        if stable >= 2:
            return
        time.sleep(0.5)
    raise HandoffError("shell_not_ready_within_10_seconds")


def wait_input(name, pane):
    deadline = time.monotonic() + 10
    stable = 0
    while time.monotonic() < deadline:
        agent = call("agent", "get", name)["agent"]
        state = agent.get("agent_status")
        if state == "blocked":
            raise HandoffError("receiver_blocked_requires_user")
        if state == "working":
            raise HandoffError("receiver_already_working")
        text = screen(pane)
        ready = (
            agent.get("interactive_ready") and state in {"idle", "done"}
            and "Ask anything" in text
            and ("tab agents" in text or "ctrl+p commands" in text)
        )
        stable = stable + 1 if ready else 0
        if stable >= 2:
            return
        time.sleep(0.5)
    raise HandoffError("opencode_input_not_ready")


def deliver(message, report):
    if os.environ.get("HERDR_ENV") != "1":
        raise HandoffError("direct_handoff_requires_herdr")
    if not message.strip():
        raise HandoffError("empty_handoff")
    pane = call(
        "pane", "split", "--current", "--direction", "right",
        "--cwd", os.getcwd(), "--no-focus",
    ).get("pane", {}).get("pane_id")
    if not isinstance(pane, str) or not pane:
        raise HandoffError("split_returned_no_pane_id")
    report["pane_id"] = pane
    name = "handoff_" + uuid.uuid4().hex[:16]
    report["agent_name"] = name
    deadline = time.monotonic() + 10
    wait_shell(pane, deadline)
    for attempt in range(2):
        try:
            call(
                "agent", "start", name, "--kind", "opencode", "--pane", pane,
                "--timeout", "30000", "--", "--auto", timeout=35,
            )
            break
        except HandoffError as error:
            if str(error) != "agent_pane_busy" or attempt:
                raise
            wait_shell(pane, deadline)
    wait_input(name, pane)
    report["submission_attempted"] = True
    try:
        # Wait for the turn to start, not for the receiver's task to finish.
        call(
            "agent", "prompt", name, message, "--wait", "--until", "working",
            "--timeout", "10000", timeout=15,
        )
        report.update(status="accepted", evidence="herdr_observed_working")
    except HandoffError:
        # A timeout does not mean the prompt was lost. Never paste it twice.
        agent = call("agent", "get", name)["agent"]
        if agent.get("agent_status") == "working":
            report.update(status="accepted", evidence="receiver_working_after_submission")
        else:
            raise HandoffError("prompt_acceptance_unconfirmed_do_not_resend") from None


def main():
    report = {"status": "failed", "submission_attempted": False}
    try:
        deliver(sys.stdin.read(), report)
    except HandoffError as error:
        report["error"] = str(error)
    except (KeyError, TypeError):
        report["error"] = "unexpected_herdr_response_shape"
    print(json.dumps(report))
    return 0 if report["status"] == "accepted" else 1


if __name__ == "__main__":
    sys.exit(main())
