#!/usr/bin/env python3
"""Nexus terminal demo: interrogate Marcus Webb and watch his "mind" move.

Run from the repo root with the Nexus stack up (docker compose up -d):

    python nexus_demo.py                          # you type the lines
    python nexus_demo.py --auto                   # scripted lines, typed out for you (repeatable takes)
    python nexus_demo.py --auto --threshold 0.6   # lower secret thresholds for demo pacing

Needs the SDK installed:  pip install -e sdk/python
Every turn is appended to demo_run_<timestamp>.jsonl (reply, state, latency),
so the same run doubles as evidence for your written answers.
"""
import argparse
import asyncio
import json
import os
import shutil
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path

# Force UTF-8 on Windows consoles to render Unicode progress bars
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from nexus_py import NexusClient

GAME_ID = "8cc751bb-10fc-4a4d-ab96-b0872e97d462"

# Your side of the conversation for --auto. Edit freely: you script the player,
# but Marcus's replies and every number on screen come from the real backend.
SCRIPTED_LINES = [
    "Thanks for coming in, Mr. Webb. Take a seat. I just want to understand your night.",
    "You told us you were at the restaurant. Walk me through the evening.",
    "A minute ago you said restaurant. So why is there no record of you being there?",
    "We have you on CCTV three blocks from the warehouse at 11:42 PM.",
    "Your brother was driving that night, wasn't he? Is he who you're protecting?",
    "Your lawyer isn't coming, Marcus. Tell me what really happened at the warehouse.",
]

# ---------------------------------------------------------------- styling
if os.name == "nt":
    os.system("")  # switches on ANSI colours in older Windows consoles

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
RED, GREEN, YELLOW, MAGENTA, CYAN, WHITE = (f"\033[{c}m" for c in (91, 92, 93, 95, 96, 97))

BEHAVIOUR_COLOURS = {
    "cooperative": GREEN,
    "deflecting": YELLOW,
    "nervous": MAGENTA,
    "hostile": RED,
    "confessing": CYAN,
}

# (label, key in emotional_state, is a high value "bad"?)
STATE_ROWS = [("Stress", "stress", True), ("Trust", "trust", False), ("Suspicion", "suspicion", True)]


# ---------------------------------------------------------------- helpers
def val(obj, key, default=0.0):
    """Read a field from a dict or a Pydantic model (the SDK docstring and
    the quickstart disagree about which one emotional_state is, so handle both)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def as_dict(obj):
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return dict(vars(obj))


def bar(value, width=20, high_is_bad=True):
    v = max(0.0, min(1.0, float(value)))
    filled = round(v * width)
    danger = v if high_is_bad else 1 - v
    colour = GREEN if danger < 0.4 else YELLOW if danger < 0.7 else RED
    return f"{colour}{'█' * filled}{DIM}{'░' * (width - filled)}{RESET}"


def behaviour_badge(behaviour):
    name = str(getattr(behaviour, "value", behaviour)).lower()
    return f"{BOLD}{BEHAVIOUR_COLOURS.get(name, WHITE)}[ {name.upper()} ]{RESET}"


def say(who, text):
    """Print a reply wrapped to the terminal width (good for split-screen recording)."""
    width = max(40, shutil.get_terminal_size((100, 20)).columns - 2)
    prefix = f"{who}: "
    wrapped = textwrap.fill(text, width=width, initial_indent=prefix, subsequent_indent=" " * len(prefix))
    print(f"{BOLD}{wrapped[:len(prefix)]}{RESET}{wrapped[len(prefix):]}")


def show_state(state, delta):
    now, change = as_dict(state), as_dict(delta)
    for label, key, high_is_bad in STATE_ROWS:
        if key in now:
            print(f"  {label:<10}{bar(now[key], high_is_bad=high_is_bad)} {now[key]:.2f}  ({change.get(key, 0.0):+.2f})")


async def type_out(text, delay):
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        await asyncio.sleep(delay)
    print()


def pct(values, p):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(p / 100 * (len(ordered) - 1)))]


def load_profile(path, threshold):
    p = Path(path)
    if not p.exists():
        sys.exit(f"Profile not found: {p}\nRun from the repo root, or pass --profile <path to marcus_webb.json>.")
    payload = json.loads(p.read_text(encoding="utf-8"))
    if threshold is not None:
        for secret in payload.get("secrets", []):
            if isinstance(secret, dict) and "reveal_threshold" in secret:
                secret["reveal_threshold"] = threshold
        print(f"{DIM}(demo pacing: every secret's reveal_threshold set to {threshold}){RESET}")
    return payload


async def create_npc(client, payload, session):
    """Spawn Marcus inside the session. Tries with session_id first; if the
    backend rejects it, retries with the bare profile."""
    body = dict(payload)
    session_id = val(session, "id", None)
    if session_id:
        body["session_id"] = session_id
    try:
        return await client.npcs.create(body)
    except Exception as err:
        if "session_id" not in body:
            raise
        print(f"{DIM}(create with session_id failed: {err}; retrying without it){RESET}")
        body.pop("session_id")
        return await client.npcs.create(body)


def log_turn(path, turn, player, res, latency):
    record = {
        "turn": turn,
        "player": player,
        "npc": res.npc_response,
        "behaviour": str(getattr(res.behaviour, "value", res.behaviour)),
        "state": as_dict(res.emotional_state),
        "delta": as_dict(res.state_delta),
        "secret_leaked": res.secret_leaked,
        "latency_s": round(latency, 3),
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def print_summary(turns, cracked_at, latencies, log_path):
    if not turns:
        return
    cracked = f"on turn {cracked_at}" if cracked_at else "no"
    print(f"\n{BOLD}--- RUN SUMMARY ---{RESET}")
    print(f"  Turns: {turns}    Secret cracked: {cracked}")
    print(f"  Reply time: p50 {pct(latencies, 50):.2f}s   p95 {pct(latencies, 95):.2f}s   (log: {log_path})")


# ---------------------------------------------------------------- the demo
async def run(args):
    payload = load_profile(args.profile, args.threshold)
    log_path = Path(f"demo_run_{datetime.now():%Y%m%d_%H%M%S}.jsonl")
    scripted = iter(SCRIPTED_LINES) if args.auto else None
    latencies, turns, cracked_at = [], 0, None

    async with NexusClient(host=args.host) as client:
        await client.auth.login_guest()
        session = await client.sessions.create(game_id=GAME_ID)
        npc = await create_npc(client, payload, session)
        npc_id = val(npc, "id", None)
        name = val(npc, "name", None) or payload.get("name") or "NPC"

        print(f"\n{BOLD}--- INTERROGATION: {name} ---{RESET}")
        if args.auto:
            await asyncio.sleep(1.5)

        while True:
            # 1) the player's line
            if args.auto:
                line = next(scripted, None)
                if line is None:
                    break
                sys.stdout.write(f"\n{BOLD}Player:{RESET} ")
                sys.stdout.flush()
                await type_out(line, args.type_delay)
            else:
                line = (await asyncio.to_thread(input, f"\n{BOLD}Player:{RESET} ")).strip()
                if line.lower() in ("quit", "exit"):
                    break
                if not line:
                    continue

            # 2) ask the NPC (timed, so the run doubles as a latency measurement)
            sys.stdout.write(f"{DIM}  ...{RESET}")
            sys.stdout.flush()
            started = time.perf_counter()
            try:
                res = await client.npcs.interact(npc_id, line)
            except Exception as err:
                print(f"\r\033[K{RED}  Error: {err}{RESET}")
                continue
            latency = time.perf_counter() - started
            sys.stdout.write("\r\033[K")

            # 3) show what the audience should see
            turns += 1
            latencies.append(latency)
            say(name, res.npc_response)
            print(f"  {behaviour_badge(res.behaviour)}  {DIM}{latency:.1f}s{RESET}")
            show_state(res.emotional_state, res.state_delta)
            if res.secret_leaked:
                cracked_at = cracked_at or turns
                print(f"\n  {BOLD}{RED}!!  SECRET CRACKED: {res.secret_leaked}  !!{RESET}")
            log_turn(log_path, turns, line, res, latency)

            if args.auto:
                await asyncio.sleep(args.pause)

    print_summary(turns, cracked_at, latencies, log_path)


def main():
    parser = argparse.ArgumentParser(description="Nexus terminal demo: interrogate Marcus Webb.")
    parser.add_argument("--host", default="localhost:8000", help="Nexus API host:port (default: localhost:8000)")
    parser.add_argument("--profile", default="api/data/npcs/marcus_webb.json", help="path to the NPC profile JSON")
    parser.add_argument("--auto", action="store_true", help="type the scripted lines automatically")
    parser.add_argument("--threshold", type=float, help="override every secret's reveal_threshold (demo pacing)")
    parser.add_argument("--pause", type=float, default=2.5, help="seconds to linger on each reply in --auto mode")
    parser.add_argument("--type-delay", type=float, default=0.035, help="seconds per typed character in --auto mode")
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
