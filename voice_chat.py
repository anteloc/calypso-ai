"""Talk to an agent through Calypso. Run with uv run voice_chat.py."""

import argparse
import json
import re
import shutil
import string
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_DIR = Path(__file__).resolve().parent
CALYPSO = ["uv", "run", "calypso-cli"]
CODEX = [
    "codex", "exec", "--json", "--ignore-user-config",
    "-c", 'sandbox_mode="read-only"',
    "-c", 'approval_policy="never"',
]
CLAUDE = [
    "claude", "--print", "--safe-mode", "--strict-mcp-config",
    "--permission-mode", "plan", "--tools", "Read,Glob,Grep",
]
COPILOT = [
    "copilot", "--no-auto-update", "--no-color", "--disable-builtin-mcps",
    "--available-tools", "view", "grep", "glob", "--allow-tool", "read",
    "--deny-tool", "shell", "write", "--stream", "off", "--silent",
]
VOICE_INSTRUCTIONS = (
    "We are having a live voice conversation. Answer in concise, natural, "
    "plain text suitable for reading aloud. Avoid Markdown formatting."
)


def agent_prompt(utterance, thread_id):
    if thread_id:
        return utterance
    return f"{VOICE_INSTRUCTIONS}\n\nThe user says:\n{utterance}"


def run_agent(command, *, prompt=None, timeout=None):
    return subprocess.run(
        command, cwd=PROJECT_DIR, input=prompt,
        stdin=subprocess.DEVNULL if prompt is None else None,
        capture_output=True, text=True, timeout=timeout,
    )


def check_agent(agent, result, error=""):
    if result.returncode or error:
        details = error or result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(details or f"{agent} exited with status {result.returncode}.")


def check_reply(agent, thread_id, reply):
    if not thread_id or not reply:
        raise RuntimeError(f"{agent} returned no session ID or reply.")
    return thread_id, reply


def model_option(model):
    return [f"--model={model}"] if model else []


def ask_codex(utterance, thread_id, model):
    """Send one utterance and return the session ID and finished reply."""
    prompt = agent_prompt(utterance, thread_id)
    command = [*CODEX, *model_option(model)]
    if thread_id:
        command.extend(["resume", thread_id])

    result = run_agent([*command, "-"], prompt=prompt)
    reply = error = ""
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        match event["type"]:
            case "thread.started":
                thread_id = event["thread_id"]
            case "item.completed" if event["item"]["type"] == "agent_message":
                reply = event["item"]["text"].strip()
            case "turn.failed":
                error = event["error"]["message"]

    check_agent("Codex", result, error)
    return check_reply("Codex", thread_id, reply)


def ask_claude(utterance, thread_id, model):
    prompt = agent_prompt(utterance, thread_id)
    command = [*CLAUDE, "--output-format", "json", *model_option(model)]
    if thread_id:
        command.extend(["--resume", thread_id])

    result = run_agent(command, prompt=prompt)
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError:
        check_agent("Claude Code", result)
        raise RuntimeError("Claude Code returned an invalid JSON reply.") from None
    reply = response.get("result", "").strip()
    error = (reply or response.get("subtype", "Request failed.")) if response.get("is_error") else ""
    check_agent("Claude Code", result, error)
    return check_reply("Claude Code", response.get("session_id"), reply)


def ask_copilot(utterance, thread_id, model):
    prompt = agent_prompt(utterance, thread_id)
    command = [*COPILOT, *model_option(model), f"--prompt={prompt}"]
    if thread_id:
        result = run_agent([*command, "--resume", thread_id])
    else:
        # The local export provides the exact ID even on Copilot versions without JSON output.
        with TemporaryDirectory(prefix="calypso-copilot-") as directory:
            export = Path(directory) / "session.md"
            result = run_agent([*command, "--share", str(export)])
            if export.is_file():
                session = re.search(r"^> \*\*Session ID:\*\* `([\w-]+)`$", export.read_text(encoding="utf-8"), re.M)
                if session:
                    thread_id = session.group(1)

    check_agent("GitHub Copilot", result)
    reply = result.stdout.strip().removeprefix("● ")
    return check_reply("GitHub Copilot", thread_id, reply)


def list_codex_models():
    result = run_agent(["codex", "debug", "models"], timeout=20)
    check_agent("Codex", result)
    return [
        (model["slug"], model["display_name"])
        for model in json.loads(result.stdout)["models"]
        if model["visibility"] == "list"
    ]


def list_claude_models():
    request = {
        "type": "control_request", "request_id": "list-models",
        "request": {"subtype": "initialize"},
    }
    result = run_agent(
        [*CLAUDE, "--input-format", "stream-json", "--output-format", "stream-json", "--verbose"],
        prompt=json.dumps(request) + "\n", timeout=20,
    )
    check_agent("Claude Code", result)
    for line in result.stdout.splitlines():
        event = json.loads(line)
        if event["type"] == "control_response" and event["response"]["request_id"] == "list-models":
            response = event["response"]
            if response["subtype"] == "success":
                return [(model["value"], model["displayName"]) for model in response["response"]["models"]]
            raise RuntimeError(response.get("error") or "Claude Code could not list models.")
    raise RuntimeError("Claude Code returned no model catalog.")


def list_copilot_models():
    result = run_agent(["copilot", "--no-auto-update", "--help"], timeout=20)
    check_agent("GitHub Copilot", result)
    option = re.search(r"^  --model\b[^\n]*(?:\n {8,}[^\n]+)*", result.stdout, re.M)
    choices = re.search(r"\(choices:\s*([^)]*)\)", option.group()) if option else None
    if not choices:
        raise RuntimeError("This Copilot version does not list IDs in --help. Run /model inside copilot.")
    return [(model, "") for model in re.findall(r'"([^"]+)"', choices.group(1))]


AGENTS = {
    "codex": ("Codex", ask_codex, list_codex_models),
    "claude": ("Claude Code", ask_claude, list_claude_models),
    "copilot": ("GitHub Copilot", ask_copilot, list_copilot_models),
}


def main():
    parser = argparse.ArgumentParser(description="Have a spoken conversation through Calypso.")
    parser.add_argument("--agent", choices=AGENTS, default="codex", help="agent to use (default: codex)")
    parser.add_argument("--model", help="model ID for the selected agent (see --list-models)")
    listing = parser.add_mutually_exclusive_group()
    listing.add_argument("--list-agents", action="store_true", help="list supported agents and installation status")
    listing.add_argument("--list-models", action="store_true", help="list model IDs for the selected agent")
    args = parser.parse_args()

    if args.list_agents:
        for name, (label, _, _) in AGENTS.items():
            status = "installed" if shutil.which(name) else "not on PATH"
            print(f"{name:<8} {label} ({status})")
        return 0

    if not shutil.which(args.agent):
        parser.error(f"{args.agent} is not on PATH. Run --list-agents to see installed options.")
    label, ask, list_models = AGENTS[args.agent]
    if args.list_models:
        if args.agent == "copilot":
            print("Models advertised by the installed Copilot CLI. Account access may vary.")
        for model_id, display_name in list_models():
            print(f"{model_id}  {display_name}" if display_name else model_id)
        return 0

    selection = f"{label} ({args.model})" if args.model else label
    print(f'Talking to {selection}. Wait for "Go ahead," then speak.', flush=True)
    print('Say "end voice chat" or press Ctrl+C to stop.', flush=True)
    thread_id = None

    while True:
        heard = subprocess.run(
            [*CALYPSO, "transcribe", "Go ahead."], cwd=PROJECT_DIR,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True,
        )
        if heard.returncode == 1:
            print("Calypso returned no transcript. Voice chat ended.")
            return 1
        heard.check_returncode()

        utterance = heard.stdout.strip()
        if utterance.casefold().strip(string.punctuation + " ") == "end voice chat":
            print("Voice chat ended.")
            return 0
        if not utterance:
            continue

        print("Thinking…", flush=True)
        thread_id, reply = ask(utterance, thread_id, args.model)
        print(f"{label}: {reply}", flush=True)
        # Calypso's say command treats single dollar signs as template syntax.
        subprocess.run(
            [*CALYPSO, "say"], cwd=PROJECT_DIR, input=reply.replace("$", "$$"),
            text=True, check=True,
        )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nVoice chat ended.")
        raise SystemExit(130) from None
    except (OSError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Voice chat: {exc}") from None
