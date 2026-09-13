from langchain_core.language_models.chat_models import BaseChatModel
from langchain_deepseek import ChatDeepSeek

from app.config import Settings

AIMLAPI_API_BASE = "https://api.aimlapi.com/v1"


class UnsupportedLLMProviderError(Exception):
    pass


def get_llm(settings: Settings) -> BaseChatModel:
    """Factory seam for the chat model — see ARCHITECTURE.md §8.5 / §15.1.

    No provider is chosen by default (open question — LLM_PROVIDER unset).
    Swapping in a real one means adding one branch here plus its client
    dependency — nothing upstream should need to change.
    """
    if not settings.llm_provider:
        raise UnsupportedLLMProviderError(
            "LLM_PROVIDER is not configured — ARCHITECTURE.md §15 open question 1 is unresolved"
        )
    if settings.llm_provider == "deepseek":
        return ChatDeepSeek(
            model=settings.llm_model or "deepseek-chat",
            api_key=settings.llm_api_key,
        )
    if settings.llm_provider == "aimlapi":
        # aimlapi.com is a third-party OpenAI-compatible gateway that serves
        # DeepSeek's models under a different auth realm/base URL than
        # DeepSeek's own API. ChatDeepSeek (a BaseChatOpenAI subclass) already
        # supports an arbitrary base_url and already has a code path for
        # exactly this shape of third-party DeepSeek proxy (see its
        # OpenRouter-handling branch) — ChatOpenAI is deliberately not used
        # here, its own docs warn it drops DeepSeek's non-standard
        # reasoning_content field.
        return ChatDeepSeek(
            model=settings.llm_model or "deepseek/deepseek-v4-flash",
            api_key=settings.llm_api_key,
            base_url=AIMLAPI_API_BASE,
        )
    raise UnsupportedLLMProviderError(f"unsupported LLM provider: {settings.llm_provider!r}")
