"""Pluggable LLM client — the agents' brain, routed through the LiteLLM gateway.

One ``LLMClient`` interface (``complete``/``embed``/``model_for``/``configured``) over any
provider LiteLLM speaks: Azure OpenAI, OpenAI, and every OpenAI-compatible host (OpenRouter →
Hermes, DeepSeek, Together, self-hosted vLLM), plus natively non-OpenAI providers (Anthropic,
Gemini, Bedrock) by model id. Provider choice stays a config flip; per-call observability
(``record_llm_call``) is preserved — every completion/embedding lands in the llm_calls ledger.
"""

from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Any

import litellm

from ..config import settings
from .observability import record_llm_call

log = logging.getLogger(__name__)

# Unsupported params (e.g. gpt-5.x reasoning models rejecting a non-default temperature) are
# dropped per-provider instead of failing the call.
litellm.drop_params = True
litellm.suppress_debug_info = True

DEFAULT_NUM_RETRIES = 2

_KNOWN_PREFIXES = ("openai/", "azure/", "openrouter/", "anthropic/", "gemini/", "bedrock/",
                   "vertex_ai/", "mistral/", "groq/", "deepseek/")


def azure_resource_root(endpoint: str) -> str:
    """LiteLLM's Azure provider wants the resource root — strip a trailing /openai/v1 route."""
    return endpoint.rstrip("/").removesuffix("/openai/v1")


def _response_cost(response: Any) -> float | None:
    """Real per-model cost from LiteLLM's pricing map; None when the model is unknown to it."""
    if response is None:
        return None
    hidden = getattr(response, "_hidden_params", None) or {}
    cost = hidden.get("response_cost")
    if cost is None:
        try:
            cost = litellm.completion_cost(completion_response=response)
        except Exception:  # unknown/custom model — the flat-price fallback still applies
            return None
    return round(float(cost), 6) if cost else None


class LLMClient:
    """Minimal provider-agnostic client implementing the SDK ``LLM`` protocol."""

    def __init__(self) -> None:
        self.provider = settings.llm_provider.lower()
        if self.provider == "azure":
            self._api_key = settings.azure_openai_api_key
            self._api_base: str | None = azure_resource_root(settings.azure_openai_v1_endpoint)
            self._api_version: str | None = settings.azure_openai_api_version
            self._chat_model = f"azure/{settings.azure_openai_deployment_name}"
            self._embed_model = f"azure/{settings.azure_openai_embedding_deployment}"
            self._temperature: float | None = settings.azure_openai_temperature
        else:
            self._api_key = settings.openai_api_key
            self._api_base = settings.openai_base_url or None
            self._api_version = None
            self._chat_model = self._qualify(settings.openai_model)
            self._embed_model = self._qualify(settings.openai_embedding_model)
            self._temperature = None

    def _qualify(self, model: str) -> str:
        """Route bare model ids at a custom base_url through LiteLLM's openai-compatible path."""
        if self.provider == "azure":
            return model if model.startswith("azure/") else f"azure/{model}"
        if self._api_base and not model.startswith(_KNOWN_PREFIXES):
            return f"openai/{model}"
        return model

    def model_for(self, role: str = "default") -> str:
        """Role-specific model override, falling back to the default chat model."""
        if role == "generation" and settings.generation_model:
            return self._qualify(settings.generation_model)
        if role == "reasoning" and settings.reasoning_model:
            return self._qualify(settings.reasoning_model)
        return self._chat_model

    def _provider_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"api_key": self._api_key, "num_retries": DEFAULT_NUM_RETRIES}
        if self._api_base:
            kwargs["api_base"] = self._api_base
        if self._api_version:
            kwargs["api_version"] = self._api_version
        return kwargs

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        role: str = "default",
        **kw: Any,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        params: dict[str, Any] = {
            "model": self.model_for(role), "messages": messages, **self._provider_kwargs(),
        }
        if self._temperature is not None:
            params["temperature"] = self._temperature
        params.update(kw)
        start = time.perf_counter()
        try:
            resp = litellm.completion(**params)
        except Exception as exc:
            self._trace(params.get("model", ""), role, None,
                        (time.perf_counter() - start) * 1000, "error", str(exc))
            raise
        self._trace(params["model"], role, getattr(resp, "usage", None),
                    (time.perf_counter() - start) * 1000, "ok", None, response=resp)
        return resp.choices[0].message.content or ""

    def embed(self, texts: list[str]) -> list[list[float]]:
        start = time.perf_counter()
        try:
            resp = litellm.embedding(model=self._embed_model, input=texts,
                                     **self._provider_kwargs())
        except Exception as exc:
            self._trace(self._embed_model, "embed", None,
                        (time.perf_counter() - start) * 1000, "error", str(exc))
            raise
        self._trace(self._embed_model, "embed", getattr(resp, "usage", None),
                    (time.perf_counter() - start) * 1000, "ok", None, response=resp)
        return [item["embedding"] if isinstance(item, dict) else item.embedding
                for item in resp.data]

    def _trace(self, model, role, usage, latency_ms, status, error, response=None) -> None:
        pt = int(getattr(usage, "prompt_tokens", 0) or 0)
        ct = int(getattr(usage, "completion_tokens", 0) or 0)
        tt = int(getattr(usage, "total_tokens", 0) or (pt + ct))
        try:
            record_llm_call(provider=self.provider, model=model or "", role=role, prompt_tokens=pt,
                            completion_tokens=ct, total_tokens=tt, latency_ms=latency_ms,
                            status=status, error=error, cost_usd=_response_cost(response))
        except Exception as exc:
            # fail-open: LLM tracing must never break a completion/embedding call.
            log.debug("LLM call tracing failed (non-fatal): %s", exc)

    def configured(self) -> bool:
        """Whether an API key is present (agents can run)."""
        if self.provider == "azure":
            return bool(settings.azure_openai_api_key and settings.azure_openai_v1_endpoint)
        return bool(settings.openai_api_key)


@lru_cache
def get_llm() -> LLMClient:
    return LLMClient()
