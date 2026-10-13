#!/usr/bin/env python3
"""Nexus terminal demo: interrogate Marcus Webb and watch his mind move.

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

# Load photorealistic fine ASCII portraits and smooth Bayer dithering morph engine
try:
    from api.data.portraits.ascii_cache import (
        PORTRAITS,
        get_portrait_lines,
        get_morph_frames,
        render_ascii_lines,
        show_portrait,
        morph_portrait,
        set_portrait_style,
    )
except Exception:
    PORTRAITS = {}

    def get_portrait_lines(behaviour):
        return []

    def get_morph_frames(from_b, to_b, frames=10):
        return []

    def render_ascii_lines(grid):
        return []

    def show_portrait(behaviour):
        pass

    async def morph_portrait(from_b, to_b, frames=10, delay=0.035):
        pass

    def set_portrait_style(style):
        pass

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
    os.system("")  # switches on ANSI colours in Windows consoles

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
    """Read a field from a dict or a Pydantic model."""
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


def bar(value, width=14, high_is_bad=True):
    v = max(0.0, min(1.0, float(value)))
    filled = round(v * width)
    danger = v if high_is_bad else 1.0 - v
    colour = GREEN if danger < 0.4 else YELLOW if danger < 0.7 else RED
    return f"{colour}{'█' * filled}{DIM}{'░' * (width - filled)}{RESET}"


def behaviour_badge(behaviour):
    name = str(getattr(behaviour, "value", behaviour)).lower()
    return f"{BOLD}{BEHAVIOUR_COLOURS.get(name, WHITE)}[ {name.upper()} ]{RESET}"


def say(who, text):
    """Print a reply wrapped to the terminal width."""
    width = max(40, shutil.get_terminal_size((100, 20)).columns - 2)
    prefix = f"{who}: "
    wrapped = textwrap.fill(text, width=width, initial_indent=prefix, subsequent_indent=" " * len(prefix))
    print(f"{BOLD}{wrapped[:len(prefix)]}{RESET}{wrapped[len(prefix):]}")


def show_state(state, delta):
    now, change = as_dict(state), as_dict(delta)
    for label, key, high_is_bad in STATE_ROWS:
        if key in now:
            print(f"  {label:<10}{bar(now[key], high_is_bad=high_is_bad)} {now[key]:.2f}  ({change.get(key, 0.0):+.2f})")


def render_hud(face_lines, behaviour, state, delta, history, latency=None, secret=None, status_msg=None):
    """Render the single unified HUD layout with persistent face on left and live metrics + transcript on right."""
    term_w = shutil.get_terminal_size((100, 30)).columns
    face_w = 46
    b_name = str(getattr(behaviour, "value", behaviour)).lower()
    b_color = BEHAVIOUR_COLOURS.get(b_name, WHITE)
    badge = f"{BOLD}{b_color}[ {b_name.upper()} ]{RESET}"

    if term_w >= 92:
        right_w = max(42, term_w - face_w - 4)
        r_lines = []
        r_lines.append(f"{BOLD}NEXUS INTERROGATION ROOM: MARCUS WEBB{RESET}")
        lat_str = f" {DIM}({latency:.2f}s){RESET}" if latency is not None else ""
        stat_line = f"Status: {badge}{lat_str}"
        if status_msg:
            stat_line += f"  {DIM}{status_msg}{RESET}"
        r_lines.append(stat_line)
        r_lines.append(f"{DIM}{'─' * (right_w - 2)}{RESET}")

        # Live emotional state bars
        st = as_dict(state)
        dt = as_dict(delta)
        for label, key, high_is_bad in STATE_ROWS:
            if key in st:
                d_val = dt.get(key, 0.0)
                d_str = f"({d_val:+.2f})" if d_val != 0.0 else "      "
                r_lines.append(f"{label:<10} {bar(st[key], width=12, high_is_bad=high_is_bad)} {st[key]:.2f} {d_str}")

        if secret:
            r_lines.append(f"{BOLD}{RED}🚨 CRACKED: {secret} 🚨{RESET}")
        else:
            r_lines.append(f"{DIM}{'─' * (right_w - 2)}{RESET}")

        r_lines.append(f"{BOLD}TRANSCRIPT:{RESET}")

        # Available rows for the transcript
        avail_rows = max(4, len(face_lines) - len(r_lines))

        # Format turns from newest to oldest so we never slice a turn in half
        formatted_turns = []
        total_rows_used = 0
        for speaker, text in reversed(history):
            color = CYAN if speaker.lower() == "player" else WHITE
            prefix = f"{BOLD}{color}{speaker}:{RESET} "
            indent = " " * (len(speaker) + 2)
            w_text = textwrap.fill(text, width=right_w - 2, initial_indent=prefix, subsequent_indent=indent)
            turn_lines = w_text.split("\n")
            needed = len(turn_lines) + (1 if formatted_turns else 0)
            if total_rows_used + len(turn_lines) > avail_rows:
                break
            if formatted_turns:
                turn_lines.append("")  # blank line spacer between turns
            formatted_turns.append(turn_lines)
            total_rows_used += needed

        transcript_lines = []
        for turn_lines in reversed(formatted_turns):
            transcript_lines.extend(turn_lines)

        # Pad transcript so lines sit cleanly inside transcript area
        while len(transcript_lines) < avail_rows:
            transcript_lines.insert(0, "")

        r_lines.extend(transcript_lines)

        # Pad to match face height (26 rows)
        while len(r_lines) < len(face_lines):
            r_lines.append("")

        combined = []
        for i in range(len(face_lines)):
            f_l = face_lines[i]
            r_l = r_lines[i] if i < len(r_lines) else ""
            combined.append(f"{f_l} {DIM}│{RESET} {r_l}\033[K")

        divider = f"{DIM}{'─' * (face_w + 3 + right_w)}{RESET}\033[K"
        combined.append(divider)
        return "\n".join(combined)
    else:
        # Stacked layout for narrower terminals (< 92 cols)
        out = []
        out.append(f"{BOLD}NEXUS INTERROGATION: MARCUS WEBB  {badge}{RESET}\033[K")
        for f_l in face_lines:
            out.append(f"{f_l}\033[K")
        st = as_dict(state)
        dt = as_dict(delta)
        for label, key, high_is_bad in STATE_ROWS:
            if key in st:
                d_val = dt.get(key, 0.0)
                d_str = f"({d_val:+.2f})" if d_val != 0.0 else "      "
                out.append(f"  {label:<10} {bar(st[key], width=12, high_is_bad=high_is_bad)} {st[key]:.2f} {d_str}\033[K")
        if secret:
            out.append(f"  {BOLD}{RED}🚨 CRACKED: {secret} 🚨{RESET}\033[K")
        out.append(f"{DIM}{'─' * min(term_w, 60)}{RESET}\033[K")
        for speaker, text in history[-3:]:
            color = CYAN if speaker.lower() == "player" else WHITE
            out.append(f"  {BOLD}{color}{speaker}:{RESET} {text}\033[K")
        out.append(f"{DIM}{'─' * min(term_w, 60)}{RESET}\033[K")
        return "\n".join(out)


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
        sys.exit(f"Profile not found: {p}\nRun from repo root, or pass --profile <path>.")
    payload = json.loads(p.read_text(encoding="utf-8"))
    if threshold is not None:
        for secret in payload.get("secrets", []):
            if isinstance(secret, dict) and "reveal_threshold" in secret:
                secret["reveal_threshold"] = threshold
        print(f"{DIM}(demo pacing: every secret's reveal_threshold set to {threshold}){RESET}")
    return payload


async def create_npc(client, payload, session):
    body = dict(payload)
    session_id = val(session, "id", None)
    if session_id:
        body["session_id"] = session_id
    try:
        return await client.npcs.create(body)
    except Exception as err:
        if "session_id" not in body:
            raise
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
    set_portrait_style(getattr(args, "style", "ascii"))
    payload = load_profile(args.profile, args.threshold)
    log_path = Path(f"demo_run_{datetime.now():%Y%m%d_%H%M%S}.jsonl")
    scripted = iter(SCRIPTED_LINES) if args.auto else None
    latencies, turns, cracked_at = [], 0, None
    secret_cracked = None

    async with NexusClient(host=args.host) as client:
        await client.auth.login_guest()
        session = await client.sessions.create(game_id=GAME_ID)
        npc = await create_npc(client, payload, session)
        npc_id = val(npc, "id", None)
        name = val(npc, "name", None) or payload.get("name") or "Marcus"

        previous_behaviour = "cooperative"
        curr_state = {"stress": 0.20, "trust": 0.50, "suspicion": 0.25}
        curr_delta = {"stress": 0.0, "trust": 0.0, "suspicion": 0.0}
        history = []

        # Clear screen and draw initial persistent HUD
        if not args.no_face:
            sys.stdout.write("\033[2J\033[H")
            face_lines = get_portrait_lines(previous_behaviour)
            hud = render_hud(face_lines, previous_behaviour, curr_state, curr_delta, history)
            sys.stdout.write(hud + "\n\033[J")
            sys.stdout.flush()
        else:
            print(f"\n{BOLD}--- INTERROGATION: {name} ---{RESET}")

        if args.auto:
            await asyncio.sleep(1.0)

        while True:
            # 1) Player's line
            prompt_line = f"{BOLD}{CYAN}Player:{RESET} "
            if args.auto:
                line = next(scripted, None)
                if line is None:
                    break
                sys.stdout.write(f"\r\033[K{prompt_line}")
                sys.stdout.flush()
                await type_out(line, args.type_delay)
            else:
                sys.stdout.write(f"\r\033[K{prompt_line}")
                sys.stdout.flush()
                line = (await asyncio.to_thread(input)).strip()
                if line.lower() in ("quit", "exit"):
                    break
                if not line:
                    continue

            # 2) Live thinking status on the single persistent HUD
            if not args.no_face:
                face_lines = get_portrait_lines(previous_behaviour)
                hud = render_hud(face_lines, previous_behaviour, curr_state, curr_delta, history, secret=secret_cracked, status_msg="thinking...")
                sys.stdout.write("\033[H" + hud + "\n\033[J")
                sys.stdout.flush()
            else:
                sys.stdout.write(f"{DIM}  ...{RESET}")
                sys.stdout.flush()

            started = time.perf_counter()
            try:
                res = await client.npcs.interact(npc_id, line)
            except Exception as err:
                print(f"\r\033[K{RED}  Error: {err}{RESET}")
                continue
            latency = time.perf_counter() - started

            # 3) Process backend response
            turns += 1
            latencies.append(latency)
            curr_behaviour = str(getattr(res.behaviour, "value", res.behaviour)).lower()
            curr_state = res.emotional_state
            curr_delta = res.state_delta
            if res.secret_leaked:
                cracked_at = cracked_at or turns
                secret_cracked = res.secret_leaked

            # 4) If emotion changed, smoothly morph the single face in place!
            if not args.no_face:
                if previous_behaviour and previous_behaviour != curr_behaviour:
                    for frame_grid in get_morph_frames(previous_behaviour, curr_behaviour, frames=args.morph_frames):
                        frame_lines = render_ascii_lines(frame_grid)
                        hud = render_hud(frame_lines, curr_behaviour, curr_state, curr_delta, history, latency=latency, secret=secret_cracked)
                        sys.stdout.write("\033[H" + hud + "\n\033[J")
                        sys.stdout.flush()
                        await asyncio.sleep(args.morph_delay)

                # Add new conversation turn to history
                history.append(("Player", line))
                history.append((name, res.npc_response))
                previous_behaviour = curr_behaviour

                # Redraw persistent HUD with updated transcript
                hud = render_hud(get_portrait_lines(curr_behaviour), curr_behaviour, curr_state, curr_delta, history, latency=latency, secret=secret_cracked)
                sys.stdout.write("\033[H" + hud + "\n\033[J")
                sys.stdout.flush()
            else:
                sys.stdout.write("\r\033[K")
                say("Player", line)
                say(name, res.npc_response)
                print(f"  {behaviour_badge(res.behaviour)}  {DIM}{latency:.1f}s{RESET}")
                show_state(curr_state, curr_delta)
                if res.secret_leaked:
                    print(f"\n  {BOLD}{RED}!!  SECRET CRACKED: {res.secret_leaked}  !!{RESET}")

            log_turn(log_path, turns, line, res, latency)

            if args.auto:
                await asyncio.sleep(args.pause)

    if not args.no_face:
        # Move cursor to end of screen after interrogation finishes
        sys.stdout.write("\n" * 2)
    print_summary(turns, cracked_at, latencies, log_path)


def main():
    parser = argparse.ArgumentParser(description="Nexus terminal demo: interrogate Marcus Webb.")
    parser.add_argument("--host", default="localhost:8000", help="Nexus API host:port (default: localhost:8000)")
    parser.add_argument("--profile", default="api/data/npcs/marcus_webb.json", help="path to NPC profile JSON")
    parser.add_argument("--auto", action="store_true", help="type scripted lines automatically")
    parser.add_argument("--no-face", action="store_true", help="disable detailed ASCII portrait rendering")
    parser.add_argument("--morph-frames", type=int, default=10, help="frames for emotional morph transitions (default: 10)")
    parser.add_argument("--morph-delay", type=float, default=0.035, help="seconds per morph transition frame (default: 0.035)")
    parser.add_argument("--threshold", type=float, help="override reveal_threshold for secrets (demo pacing)")
    parser.add_argument("--style", default="ascii", help="portrait style ('ascii')")
    parser.add_argument("--pause", type=float, default=2.5, help="seconds to linger on each reply in --auto mode")
    parser.add_argument("--type-delay", type=float, default=0.03, help="seconds per typed character in --auto mode")
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
