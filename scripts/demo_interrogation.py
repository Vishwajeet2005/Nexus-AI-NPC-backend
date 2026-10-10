import asyncio
import sys
import os

# Ensure we can import the local SDK
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../sdk/python")))

from nexus_py import NexusClient

MARCUS_WEBB_DATA = {
    "name": "Marcus Webb",
    "personality": {
        "traits": ["calculated", "defensive", "prideful"],
        "motivation": "Protect his brother",
        "fear": "Going back to prison",
        "background": "Ex-con who got pulled back into the underworld.",
        "speech_style": "clipped, guarded, occasionally sarcastic",
        "tells": {
            "cooperative": "Leans back slightly, answers directly.",
            "deflecting": "Answers a question with a question.",
            "nervous": "Avoids eye contact, stutters slightly.",
            "hostile": "Crosses arms, speaks in short, clipped sentences."
        }
    },
    "secrets": [
        {
            "id": "money_location",
            "content": "I buried the money behind the old sawmill.",
            "reveal_trigger": "confronted with concrete proof about the shovel receipt",
            "reveal_threshold": 0.85
        }
    ],
    "initial_emotional_state": {
        "stress": 0.2,
        "trust": 0.2,
        "suspicion": 0.6,
        "cooperation": 0.1
    },
    "confession_threshold": 0.85,
    "memory_scope": "session"
}


async def main():
    print("🚀 Initializing Echoes of Truth Backend...")
    # Initialize the client (assumes local backend is running on 8000)
    async with NexusClient(host="localhost:8000") as client:
        
        # 1. Login anonymously as a guest
        print("🔐 Logging in as guest...")
        await client.auth.login_guest()
        
        # 2. Create and join a session
        print("🎮 Creating game session...")
        session = await client.sessions.create(game_id="echoes_of_truth")
        await client.sessions.join(session.id)
        
        # 3. Spawn Marcus Webb
        print("👤 Spawning NPC: Marcus Webb...")
        npc_data = dict(MARCUS_WEBB_DATA)
        npc_data["session_id"] = session.id
        
        npc = await client.npcs.create(npc_data)
        
        print("\n" + "="*50)
        print(f"🕵️  INTERROGATION BEGUN: {npc.name}")
        print("Type your questions below. Type 'quit' to exit.")
        print("="*50 + "\n")
        
        # 4. Core Interrogation Loop
        while True:
            try:
                user_input = input("\nPlayer: ")
                if user_input.strip().lower() in ["quit", "exit"]:
                    break
                if not user_input.strip():
                    continue
                
                # Interact with the NPC via the SDK
                response = await client.npcs.interact(npc.id, user_input)
                
                # Extract interesting metadata
                reply = response.npc_response
                stress = response.emotional_state.stress
                stress_delta = response.state_delta.stress
                behaviour = response.behaviour.value.upper()
                secret = response.secret_leaked
                
                # Print the response + dynamic state data
                print(f"\nMarcus: \"{reply}\"")
                print(f"   ► [BEHAVIOUR: {behaviour}]")
                print(f"   ► [STRESS: {stress:.2f} ({stress_delta:+.2f})]")
                
                if secret:
                    print(f"   🚨 [SECRET REVEALED: {secret}] 🚨")
                    
            except Exception as e:
                print(f"\n❌ Error during interaction: {e}")
                break
                
        print("\n🛑 Interrogation ended.")


if __name__ == "__main__":
    # Ensure Windows asyncio loop runs cleanly
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExited.")
