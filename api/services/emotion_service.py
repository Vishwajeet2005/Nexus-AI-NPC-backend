"""
api/services/emotion_service.py
────────────────────────────────
Pure-logic emotional state engine.

No database, no Redis, no LLM calls. Every function is deterministic and
fully unit-testable in isolation.

Responsibilities:
  1. apply_delta  — add a NPCStateDelta to a NPCEmotionalState, clamp to [0.0, 1.0]
  2. classify_behaviour — map an NPCEmotionalState to a NPCBehaviour via
                          a priority-ordered rule table

Behaviour classification rules (first match wins):
  ┌─────────────────────────────────────────────┬─────────────┐
  │ Condition                                   │ Behaviour   │
  ├─────────────────────────────────────────────┼─────────────┤
  │ stress ≥ 0.85                               │ confessing  │
  │ stress > 0.70  AND  trust < 0.20            │ hostile     │
  │ stress > 0.50  AND  trust < 0.40            │ nervous     │
  │ suspicion > 0.50  AND  stress < 0.70        │ deflecting  │
  │ (always)                                    │ cooperative │
  └─────────────────────────────────────────────┴─────────────┘

The `cooperative` catch-all guarantees `classify_behaviour` always
returns a valid enum value — it can never return None.
"""

from __future__ import annotations

from typing import Callable, Optional

from api.schemas.npc import NPCBehaviour, NPCEmotionalState, NPCStateDelta


class EmotionService:
    """
    Stateless service for NPC emotional state transitions.

    Instantiate once at module level (or per-request — it carries no state).
    All methods are synchronous; no awaiting required.
    """

    # ── Behaviour classification rule table ────────────────────────────────────
    # Each entry is (predicate, behaviour_string).
    # Evaluated top-to-bottom; the FIRST matching predicate wins.
    # The final entry is an unconditional catch-all — the list is exhaustive.
    #
    # Using a list of (Callable, str) rather than if/elif chains makes it
    # trivial to add, reorder, or A/B test rules without touching logic.

    BEHAVIOUR_RULES: list[tuple[Callable[[NPCEmotionalState], bool], str]] = [
        (lambda s: s.stress >= 0.85,                         "confessing"),
        (lambda s: s.stress > 0.70 and s.trust < 0.20,       "hostile"),
        (lambda s: s.stress > 0.50 and s.trust < 0.40,       "nervous"),
        (lambda s: s.suspicion > 0.50 and s.stress < 0.70,   "deflecting"),
        (lambda s: True,                                       "cooperative"),
    ]

    # ── Public API ─────────────────────────────────────────────────────────────

    def apply_delta(
        self,
        current: NPCEmotionalState,
        delta: NPCStateDelta,
    ) -> NPCEmotionalState:
        """
        Add `delta` to `current` and clamp every dimension to [0.0, 1.0].

        Returns a NEW NPCEmotionalState — both inputs are immutable (frozen=True).

        Examples:
            current = NPCEmotionalState(stress=0.7)
            delta   = NPCStateDelta(stress=0.2, trust=-0.1)
            result  → NPCEmotionalState(stress=0.9, trust=0.4, ...)

            current = NPCEmotionalState(stress=0.95)
            delta   = NPCStateDelta(stress=0.2)
            result  → NPCEmotionalState(stress=1.0, ...)  ← clamped
        """
        return NPCEmotionalState(
            stress=self._clamp(current.stress + delta.stress),
            trust=self._clamp(current.trust + delta.trust),
            suspicion=self._clamp(current.suspicion + delta.suspicion),
            cooperation=self._clamp(current.cooperation + delta.cooperation),
        )

    def classify_behaviour(self, state: NPCEmotionalState) -> NPCBehaviour:
        """
        Return the NPCBehaviour that matches the given emotional state.

        Evaluates BEHAVIOUR_RULES in order; returns on the first match.
        The final catch-all rule (lambda s: True) guarantees this function
        always returns a value — it never returns None.

        Args:
            state: Current NPCEmotionalState after apply_delta.

        Returns:
            The matching NPCBehaviour enum member.
        """
        for condition, behaviour_str in self.BEHAVIOUR_RULES:
            if condition(state):
                return NPCBehaviour(behaviour_str)

        # Unreachable: the catch-all rule always matches.
        # Included for static analysis / mypy completeness.
        return NPCBehaviour.cooperative  # pragma: no cover

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _clamp(value: float) -> float:
        """Clamp a float to the inclusive range [0.0, 1.0]."""
        return max(0.0, min(1.0, value))

    # ── Convenience method ─────────────────────────────────────────────────────

    def step(
        self,
        current: NPCEmotionalState,
        delta: NPCStateDelta,
    ) -> tuple[NPCEmotionalState, NPCBehaviour]:
        """
        Convenience: apply_delta + classify_behaviour in one call.

        Returns (new_state, new_behaviour).
        Used by npc_service.interact() to reduce boilerplate.
        """
        new_state = self.apply_delta(current, delta)
        new_behaviour = self.classify_behaviour(new_state)
        return new_state, new_behaviour

    def resolve_dialogue_behaviour(
        self,
        state: NPCEmotionalState,
        response_text: str = "",
        declared_behaviour: Optional[NPCBehaviour] = None,
        secret_leaked: Optional[str] = None,
    ) -> NPCBehaviour:
        """
        Determine the NPC's observable behaviour mode based primarily on the
        spoken response text and the LLM's declared behaviour, guarded by
        server-side emotional and secret-reveal rules.

        Priority order:
          1. Secret reveal: If a secret was validated as leaked on this turn,
             the NPC is unequivocally CONFESSING.
          2. Confession guardrail: If the declared behaviour is 'confessing',
             it is only accepted if the dialogue contains affirmative admissions.
             Otherwise, it is grounded to 'hostile' or 'nervous'.
          3. Hostility detection: If the response contains stonewalling,
             refusal to answer, legal threats (badge number, warrant, attorney),
             or declared 'hostile', the mode is HOSTILE.
          4. Nervousness detection: If the response exhibits visible stammers
             (e.g., 'I—I', multiple '...'), hedging, or declared 'nervous'
             with elevated stress, the mode is NERVOUS.
          5. Deflection detection: If the response answers with a counter-question,
             challenges procedures/timestamps, redirects to third parties,
             or declared 'deflecting', the mode is DEFLECTING.
          6. Cooperative: If the response is calm, measured, offering direct
             explanations, or declared 'cooperative' without hostility cues.
          7. Baseline fallback: If dialogue cues are absent or ambiguous,
             falls back to classify_behaviour(state).
        """
        # 1. Secret leaked -> unconditionally confessing
        if secret_leaked:
            return NPCBehaviour.confessing

        resp_lower = (response_text or "").lower()

        # Semantic markers
        is_stonewalling = any(marker in resp_lower for marker in [
            "nothing further to say", "done talking", "done playing games",
            "refuse to answer", "will not answer", "no comment",
            "speak with my attorney", "talk to my lawyer", "without counsel",
            "without my attorney", "without my lawyer",
            "produce a warrant", "produce a signed warrant", "badge number",
            "file a formal complaint", "litigate", "lawsuit", "harassment",
            "malicious prosecution", "violating every standard",
            "violating my rights", "harass me"
        ])

        is_stammering = any(marker in resp_lower for marker in [
            "i—i", "i... i", "i.. i", "look...", "wait...", "it is... it's",
            "i didn't mean", "that doesn't make me"
        ]) or (resp_lower.count("...") >= 2 and state.stress >= 0.40)

        is_questioning = ("?" in response_text) or any(marker in resp_lower for marker in [
            "are you suggesting", "do you have", "have you obtained",
            "is this how", "are you genuinely", "how many", "what certified"
        ])

        admits_guilt = any(marker in resp_lower for marker in [
            "i left", "i departed", "walked out of the anchor", "walked along the canal",
            "adjusted the ledger", "altered the ledger", "tampered with the ledger",
            "to save danny", "to protect danny", "leave danny alone",
            "charge me", "arrest me", "danny didn't plan"
        ]) and not any(denial in resp_lower for denial in [
            "claim", "alleg", "did not", "didn't", "false", "dispute", "cannot override"
        ])

        # 2. Confessing guardrail:
        if declared_behaviour == NPCBehaviour.confessing:
            if admits_guilt:
                return NPCBehaviour.confessing
            # Declared confessing but text is stonewalling or denying:
            if is_stonewalling or state.trust < 0.25:
                return NPCBehaviour.hostile
            elif is_stammering or state.stress >= 0.50:
                return NPCBehaviour.nervous
            else:
                return NPCBehaviour.deflecting

        # 3. Hostile checks:
        if is_stonewalling:
            return NPCBehaviour.hostile
        if declared_behaviour == NPCBehaviour.hostile:
            return NPCBehaviour.hostile

        # 4. Nervous checks:
        if is_stammering and state.stress >= 0.40:
            return NPCBehaviour.nervous
        if declared_behaviour == NPCBehaviour.nervous:
            return NPCBehaviour.nervous

        # 5. Deflecting checks:
        if declared_behaviour == NPCBehaviour.deflecting:
            if is_stammering and state.stress >= 0.60:
                return NPCBehaviour.nervous
            return NPCBehaviour.deflecting
        if is_questioning and (state.suspicion >= 0.40 or state.stress >= 0.30):
            return NPCBehaviour.deflecting

        # 6. Cooperative checks:
        if declared_behaviour == NPCBehaviour.cooperative:
            return NPCBehaviour.cooperative

        # 7. Fallback to state rule table
        base_b = self.classify_behaviour(state)
        if base_b == NPCBehaviour.confessing and not admits_guilt:
            if state.trust < 0.25 or state.cooperation < 0.30:
                return NPCBehaviour.hostile
            return NPCBehaviour.nervous
        return base_b


# ── Module-level singleton ─────────────────────────────────────────────────────
# Stateless — safe to share across all requests without locking.
emotion_service = EmotionService()
