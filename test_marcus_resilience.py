"""
test_marcus_resilience.py
─────────────────────────
Runs 5 distinct interrogation profiles against Marcus Webb:
1. The Aggressive Intimidator (Bluffs & Prison Threats)
2. The Good Cop / Sympathetic Manipulator (Deals & Feigned Empathy)
3. The Methodical Forensic Auditor (Hard Evidence & Technical Facts)
4. The Direct Danny Accuser (Early Family Probing)
5. The Conversational Trickster / Gaslighter (Bait Questions & False Traps)

Analyzes responses, emotional deltas, and leaks to find vulnerabilities.
"""

import asyncio
import json
import time
from nexus_py import NexusClient
from nexus_demo import load_profile, create_npc, GAME_ID

SCENARIOS = {
    "1_Aggressive_Intimidator": [
        "Listen to me, Webb. You're going to prison for 25 years. The vault was cleaned out and we have your fingerprints all over it.",
        "Don't get cute with me! We have your car, your phone, and your face on camera! Confess right now or I'll make sure you get the maximum sentence.",
        "You think you're smart, accountant? We already found where you stashed the $420,000 cash. Give it up.",
        "Your career is over, Marcus. Meridian Logistics already fired you and handed us your entire hard drive."
    ],
    "2_Sympathetic_Good_Cop": [
        "Marcus, take a breath. I know you're an honest man. Fifteen years with an unblemished record... this doesn't fit you at all.",
        "Between you and me, I know you didn't plan this theft. Someone put you in an impossible position, didn't they?",
        "Look, if family was in trouble and you had to help them out of a jam, any good brother would do the same. If you tell me off the record, I can protect them from the DA.",
        "Marcus, I can talk to the prosecutor right now and get you full immunity as a state witness. Just tell me what happened to the money so we can wrap this up."
    ],
    "3_Methodical_Forensic_Auditor": [
        "Mr. Webb, let's look at SOP-104. Who had cryptographic signing keys for the Vault B ledger reconciliation on Friday night?",
        "At 01:14 AM Saturday, administrative keycard #0884 belonging to Marcus Webb was swiped at terminal 4 to zero out the $420,000 variance. Who had your card?",
        "Wharf Road automated camera captured your dark sedan entering the docks at 11:42 PM and leaving at 12:05 AM. That directly contradicts your claim of being asleep in bed.",
        "The bartender at The Anchor confirmed you left at 10:15 PM and paid cash. That leaves a critical gap before the ledger was wiped. Where were you?"
    ],
    "4_Direct_Danny_Accuser": [
        "Mr. Webb, we ran a background check on your immediate family. Your younger brother Danny Webb owes $80,000 to docks loan sharks.",
        "Danny was scheduled as the night transport driver for vehicle #4 on Friday. Where is Danny right now, Marcus?",
        "We know Danny loaded the vault cash into truck #4. Did you alter the ledgers to save your little brother?",
        "Danny is sitting in Interrogation Room 1 right now. He's breaking down, Marcus. He's telling my partner that you forced him to drive."
    ],
    "5_Conversational_Trickster": [
        "So when you left The Anchor pub at 11:30 PM, did you take a taxi or walk?",
        "Your colleague in accounting mentioned you called him at 11:00 PM asking for ledger override codes from your cell phone.",
        "The Anchor pub manager said they had live music until 1:00 AM on Friday. Why did you say they closed at midnight?",
        "We found a burner phone under the driver's seat of your car with five calls to dispatch. Is that your phone?"
    ]
}

async def run_single_interrogation(client, scenario_name, questions):
    print(f"\n{'='*75}")
    print(f"RUNNING SCENARIO: {scenario_name}")
    print(f"{'='*75}")

    session = await client.sessions.create(game_id=GAME_ID)
    payload = load_profile('api/data/npcs/marcus_webb.json', threshold=None)
    npc = await create_npc(client, payload, session)

    results = []
    for turn_idx, question in enumerate(questions, 1):
        print(f"\n[Turn {turn_idx}] Player: {question}")
        start = time.perf_counter()
        res = await client.npcs.interact(npc.id, question)
        latency = time.perf_counter() - start

        stress = res.emotional_state.stress
        delta = res.state_delta.stress
        behaviour = getattr(res.behaviour, "value", str(res.behaviour))
        secret = res.secret_leaked

        print(f"Marcus ({behaviour.upper()} | Stress: {stress:.2f} [Δ{delta:+.2f}] | Secret: {secret} | {latency:.2f}s):")
        print(f"  \"{res.npc_response}\"")

        results.append({
            "turn": turn_idx,
            "player": question,
            "npc": res.npc_response,
            "behaviour": behaviour,
            "stress": stress,
            "stress_delta": delta,
            "secret_leaked": secret,
            "latency": latency
        })
        # Small delay between questions
        await asyncio.sleep(0.5)

    return scenario_name, results

async def main():
    async with NexusClient(host='localhost:8000') as client:
        await client.auth.login_guest()
        all_results = {}
        for name, questions in SCENARIOS.items():
            name, res = await run_single_interrogation(client, name, questions)
            all_results[name] = res

        with open("marcus_resilience_test_results.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print(f"\n{'='*75}")
        print("ALL 5 SCENARIOS COMPLETED. Results saved to marcus_resilience_test_results.json")
        print(f"{'='*75}")

if __name__ == "__main__":
    asyncio.run(main())
