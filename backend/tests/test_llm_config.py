"""Regression tests for the LiteLLM-backed client: provider/model mapping, roles, tracing."""

from __future__ import annotations

from types import SimpleNamespace

import laboratree.core.llm as llm_mod
from laboratree.core.config import settings
from laboratree.core.llm import LLMClient, azure_resource_root


def _fake_response(content: str = "ok"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2, total_tokens=5),
    )


def test_azure_resource_root_strips_v1_route():
    assert azure_resource_root("https://x.openai.azure.com/openai/v1") == "https://x.openai.azure.com"
    assert azure_resource_root("https://x.openai.azure.com/openai/v1/") == "https://x.openai.azure.com"
    # already a resource root -> unchanged
    assert azure_resource_root("https://x.openai.azure.com") == "https://x.openai.azure.com"


def test_azure_mapping_and_completion_params(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "azure")
    monkeypatch.setattr(settings, "azure_openai_api_key", "k")
    monkeypatch.setattr(settings, "azure_openai_v1_endpoint", "https://res.openai.azure.com/openai/v1")
    monkeypatch.setattr(settings, "azure_openai_deployment_name", "gpt-5.4")
    monkeypatch.setattr(settings, "reasoning_model", "")
    monkeypatch.setattr(settings, "generation_model", "")

    seen: dict = {}

    def _fake_completion(**kwargs):
        seen.update(kwargs)
        return _fake_response("hello")

    monkeypatch.setattr(llm_mod.litellm, "completion", _fake_completion)
    client = LLMClient()
    out = client.complete("hi", system="sys")

    assert out == "hello"
    assert seen["model"] == "azure/gpt-5.4"                       # litellm azure provider
    assert seen["api_base"] == "https://res.openai.azure.com"     # resource root, not /openai/v1
    assert seen["api_version"] == settings.azure_openai_api_version
    assert seen["messages"][0] == {"role": "system", "content": "sys"}
    assert seen["num_retries"] >= 1


def test_openai_compatible_base_url_qualifies_bare_models(monkeypatch):
    # Hermes via OpenRouter: base_url + bare model id -> litellm openai-compatible route
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "k")
    monkeypatch.setattr(settings, "openai_base_url", "https://openrouter.ai/api/v1")
    monkeypatch.setattr(settings, "openai_model", "nousresearch/hermes-4-70b")
    monkeypatch.setattr(settings, "reasoning_model", "nousresearch/hermes-4-405b")
    monkeypatch.setattr(settings, "generation_model", "")

    seen: dict = {}

    def _fake_completion(**kwargs):
        seen.update(kwargs)
        return _fake_response()

    monkeypatch.setattr(llm_mod.litellm, "completion", _fake_completion)
    client = LLMClient()

    client.complete("hi")                                          # default role
    assert seen["model"] == "openai/nousresearch/hermes-4-70b"
    assert seen["api_base"] == "https://openrouter.ai/api/v1"
    assert "api_version" not in seen

    client.complete("hi", role="reasoning")                        # role override
    assert seen["model"] == "openai/nousresearch/hermes-4-405b"

    # an already-qualified id is left alone
    monkeypatch.setattr(settings, "reasoning_model", "anthropic/claude-sonnet-5")
    client2 = LLMClient()
    client2.complete("hi", role="reasoning")
    assert seen["model"] == "anthropic/claude-sonnet-5"


def test_embed_mapping_handles_dict_and_object_items(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "k")
    monkeypatch.setattr(settings, "openai_base_url", "")
    monkeypatch.setattr(settings, "openai_embedding_model", "text-embedding-3-small")

    def _fake_embedding(**kwargs):
        assert kwargs["model"] == "text-embedding-3-small"
        return SimpleNamespace(
            data=[{"embedding": [0.1, 0.2]}, SimpleNamespace(embedding=[0.3, 0.4])],
            usage=SimpleNamespace(prompt_tokens=2, completion_tokens=0, total_tokens=2),
        )

    monkeypatch.setattr(llm_mod.litellm, "embedding", _fake_embedding)
    vectors = LLMClient().embed(["a", "b"])
    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
