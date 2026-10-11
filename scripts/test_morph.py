#!/usr/bin/env python3
"""Test harness demonstrating smooth ANSI TrueColor emotional phase transitions."""
import asyncio
import os
import sys

if os.name == "nt":
    os.system("")
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

sys.path.insert(0, os.path.abspath("."))

from api.data.portraits.ascii_cache import morph_portrait, show_portrait


async def run_sequence():
    transitions = [
        ("cooperative", "deflecting"),
        ("deflecting", "nervous"),
        ("nervous", "hostile"),
        ("hostile", "confessing"),
    ]
    for from_state, to_state in transitions:
        print(f"\n=== EMOTION SHIFT: {from_state.upper()} -> {to_state.upper()} ===")
        await morph_portrait(from_state, to_state, frames=10, delay=0.035)
        await asyncio.sleep(0.4)


if __name__ == "__main__":
    asyncio.run(run_sequence())
