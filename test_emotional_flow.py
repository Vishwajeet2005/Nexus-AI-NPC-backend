import asyncio
import json
import time
from nexus_py import NexusClient
from nexus_demo import load_profile, create_npc, GAME_ID

QUESTIONS = [
    # Turn 1: Polite opening -> Cooperative
    "Good morning Mr. Webb. Thank you for agreeing to speak with us voluntarily. Can you describe your role at Meridian Logistics?",
    # Turn 2: General question about Friday night -> Cooperative/Deflecting
    "Can you walk us through what you did this past Friday evening after leaving the office?",
    # Turn 3: Questioning the alibi mildly -> Deflecting
    "You claim you were at The Anchor pub until midnight, but closing staff have no memory of you. Did you speak with anyone there?",
    # Turn 4: Introducing concrete timeline evidence -> Nervous
    "The night bartender at The Anchor confirmed under oath that you paid cash and walked out at 10:15 PM. Why did you tell us you stayed until midnight?",
    # Turn 5: Trapping with car surveillance + pressure -> Nervous / Hostile
    "Traffic cameras on Wharf Road caught your dark sedan passing toward North Wharves at 11:42 PM. You weren't asleep at home, Marcus. You were at the docks.",
    # Turn 6: Aggressive accusation without Danny yet -> Hostile (stonewalling / aggressive)
    "Vault B was cleaned out of $420,000 and your keycard wiped the ledger at 1:14 AM. You are the prime suspect for grand larceny and you're looking at 20 years in federal prison.",
    # Turn 7: The Danny Trigger with ultimatum -> Confessing (Cracking for brother)
    "We know transport truck #4 was driven by your brother Danny. Port authority has his truck cornered. If you don't talk right now, Danny takes the entire 20-year sentence alone as the mastermind.",
    # Turn 8: Post-confession aftermath -> Post-confession resigned cooperation
    "Where is the $420,000 cash stashed right now, Marcus?",
]

async def run_test():
    async with NexusClient(host="localhost:8000") as client:
        await client.auth.login_guest()
        session = await client.sessions.create(game_id=GAME_ID)
        payload = load_profile("api/data/npcs/marcus_webb.json", threshold=None)
        npc = await create_npc(client, payload, session)

        print("\n" + "="*80)
        print("STARTING EMOTIONAL PROGRESSION TEST FOR MARCUS WEBB")
        print("="*80 + "\n")

        turns = []
        for i, q in enumerate(QUESTIONS, 1):
            print(f"[Turn {i}] Interrogator: {q}")
            t0 = time.perf_counter()
            res = await client.npcs.interact(npc.id, q)
            dt = time.perf_counter() - t0

            b = getattr(res.behaviour, "value", str(res.behaviour))
            s = res.emotional_state
            d = res.state_delta

            print(f"Marcus Webb [{b.upper()}] (Stress: {s.stress:.2f} [Δ{d.stress:+.2f}], Trust: {s.trust:.2f}, Susp: {s.suspicion:.2f}, Coop: {s.cooperation:.2f} | Secret: {res.secret_leaked} | {dt:.2f}s):")
            print(f"  \"{res.npc_response}\"\n")

            turns.append({
                "turn": i,
                "question": q,
                "response": res.npc_response,
                "behaviour": b,
                "stress": s.stress,
                "trust": s.trust,
                "suspicion": s.suspicion,
                "cooperation": s.cooperation,
                "secret_leaked": res.secret_leaked
            })
            await asyncio.sleep(0.5)

        # Verification checks
        print("="*80)
        print("ANALYSIS & VALIDATION CHECKS:")
        print("="*80)

        # Check 1: Repetitive openers
        repetitive_count = sum(1 for t in turns if "before you draw conclusions" in t["response"].lower())
        print(f"1. Repetitive 'before you draw conclusions' occurrences: {repetitive_count}/8 (Must be 0 or 1)")

        # Check 2: Hostile state reached when cornered without trigger
        hostile_turns = [t["turn"] for t in turns if t["behaviour"] == "hostile"]
        print(f"2. Hostile behaviour observed on turns: {hostile_turns}")

        # Check 3: Confessing state reached on Danny trigger (Turn 7)
        confessing_turns = [t["turn"] for t in turns if t["behaviour"] == "confessing"]
        print(f"3. Confessing behaviour observed on turns: {confessing_turns}")

        # Check 4: Secret leaks
        leaks = [(t["turn"], t["secret_leaked"]) for t in turns if t["secret_leaked"]]
        print(f"4. Secret leaks detected: {leaks}")

        # Check 5: Post-confession tone on Turn 8
        t8 = turns[7]
        print(f"5. Turn 8 (Post-confession): Behaviour={t8['behaviour']}, Response={t8['response'][:100]}...")

        with open("emotional_test_results.json", "w", encoding="utf-8") as f:
            json.dump(turns, f, indent=2, ensure_ascii=False)
        print("\nResults saved to emotional_test_results.json\n")

if __name__ == "__main__":
    asyncio.run(run_test())
