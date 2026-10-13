"""
api/services/llm/groq_provider.py
──────────────────────────────────
Groq provider implementation using the official `groq` async client.

Groq is the DEFAULT provider (LLM_PROVIDER=groq) because llama-3.1-8b-instant
delivers sub-second latency on Groq's LPU hardware — critical for an
interrogation game where response delays break immersion.

Configuration (from environment / pydantic Settings):
  GROQ_API_KEY   — required
  GROQ_MODEL     — default: llama-3.1-8b-instant

JSON enforcement:
  Uses `response_format={"type": "json_object"}` (supported by Groq for
  llama-3.1 models). Also appends JSON_INSTRUCTION to the system prompt
  to ensure correct key names.

Timeout:
  asyncio.wait_for wraps the API call with LLM_TIMEOUT_SECONDS (10s).
  On TimeoutError → returns LLMResponse.timeout().

Error handling:
  All exceptions are caught and logged. Callers always receive a valid LLMResponse.
"""

from __future__ import annotations

import asyncio
import logging

from api.services.llm.base import BaseLLMProvider, LLMResponse, LLM_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class GroqProvider(BaseLLMProvider):
    """LLM provider backed by Groq Chat Completions API."""

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.1-8b-instant",
    ) -> None:
        """
        Args:
            api_key: Groq API key (GROQ_API_KEY).
            model:   Groq model to use. Default: llama-3.1-8b-instant.
                     Also works with: llama-3.1-70b-versatile, mixtral-8x7b-32768.
        """
        try:
            from groq import AsyncGroq
        except ImportError as exc:
            raise ImportError(
                "Groq provider requires the `groq` package. "
                "Install it with: pip install groq"
            ) from exc

        self._client = AsyncGroq(api_key=api_key)
        self._model = model
        logger.info(
            "llm.provider.groq.init",
            extra={"model": self._model},
        )

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
    ) -> LLMResponse:
        """
        Call Groq Chat Completions with robust JSON mode, 429 retry, and model failover.
        """
        full_system = f"{system_prompt}\n\n{self.JSON_INSTRUCTION}"

        # Candidate models to try in order of preference
        models = [self._model]
        for fallback in ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
            if fallback not in models:
                models.append(fallback)

        last_error = None
        for model in models:
            for attempt in range(2):
                try:
                    kwargs = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": full_system},
                            {"role": "user", "content": user_message},
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1500,
                        "response_format": {"type": "json_object"},
                    }
                    raw_response = await asyncio.wait_for(
                        self._client.chat.completions.create(**kwargs),
                        timeout=LLM_TIMEOUT_SECONDS,
                    )
                    raw_content = raw_response.choices[0].message.content or ""
                    data = self._extract_json(raw_content)
                    result = LLMResponse.from_dict(data, raw=raw_content)
                    logger.debug(
                        "llm.groq.success",
                        extra={
                            "model": model,
                            "behaviour": result.behaviour.value,
                            "secret_leaked": result.secret_leaked,
                        },
                    )
                    return result
                except asyncio.TimeoutError:
                    logger.warning("llm.groq.timeout", extra={"model": model, "attempt": attempt})
                    break  # Try next model if timed out
                except Exception as exc:
                    err_str = str(exc).lower()
                    last_error = exc
                    # If rate-limited (HTTP 429), pause briefly before retry
                    if "429" in err_str or "rate_limit" in err_str:
                        logger.warning("llm.groq.rate_limited", extra={"model": model, "attempt": attempt})
                        await asyncio.sleep(1.2)
                        continue
                    # If constrained JSON mode failed, try unconstrained JSON once
                    if "json_validate_failed" in err_str or "validate json" in err_str:
                        try:
                            kwargs.pop("response_format", None)
                            raw_response = await asyncio.wait_for(
                                self._client.chat.completions.create(**kwargs),
                                timeout=LLM_TIMEOUT_SECONDS,
                            )
                            raw_content = raw_response.choices[0].message.content or ""
                            data = self._extract_json(raw_content)
                            return LLMResponse.from_dict(data, raw=raw_content)
                        except Exception:
                            pass
                    break  # Try next model

        logger.error("llm.groq.all_models_failed", extra={"last_error": str(last_error)})
        return LLMResponse.error()
