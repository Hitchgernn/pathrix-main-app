import pytest
from langchain_deepseek import ChatDeepSeek

from app.agent.llm import AIMLAPI_API_BASE, UnsupportedLLMProviderError, get_llm
from app.config import Settings


def _settings(**overrides: str) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_get_llm_raises_when_provider_unset():
    with pytest.raises(UnsupportedLLMProviderError):
        get_llm(_settings())


def test_get_llm_raises_for_unknown_provider():
    with pytest.raises(UnsupportedLLMProviderError):
        get_llm(_settings(llm_provider="nonsense"))


def test_get_llm_deepseek_uses_deepseeks_own_default_endpoint():
    llm = get_llm(_settings(llm_provider="deepseek", llm_model="deepseek-chat", llm_api_key="k"))
    assert isinstance(llm, ChatDeepSeek)
    assert llm.api_base == "https://api.deepseek.com/v1"
    assert llm.model_name == "deepseek-chat"


def test_get_llm_aimlapi_points_chatdeepseek_at_the_aimlapi_gateway():
    llm = get_llm(
        _settings(
            llm_provider="aimlapi",
            llm_model="deepseek/deepseek-v4-flash",
            llm_api_key="k",
        )
    )
    assert isinstance(llm, ChatDeepSeek)
    assert llm.api_base == AIMLAPI_API_BASE
    assert llm.model_name == "deepseek/deepseek-v4-flash"
    assert llm.api_key is not None
    assert llm.api_key.get_secret_value() == "k"


def test_get_llm_aimlapi_defaults_to_v4_flash_when_model_unset():
    llm = get_llm(_settings(llm_provider="aimlapi", llm_api_key="k"))
    assert llm.model_name == "deepseek/deepseek-v4-flash"
