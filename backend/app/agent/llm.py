from langchain_core.language_models.chat_models import BaseChatModel

from app.config import Settings


class UnsupportedLLMProviderError(Exception):
    pass


def get_llm(settings: Settings) -> BaseChatModel:
    """Factory seam for the chat model — see ARCHITECTURE.md §8.5 / §15.1.

    No provider is chosen yet (open question). Swapping in a real one means
    adding one branch here plus its client dependency — nothing upstream
    should need to change.
    """
    if not settings.llm_provider:
        raise UnsupportedLLMProviderError(
            "LLM_PROVIDER is not configured — ARCHITECTURE.md §15 open question 1 is unresolved"
        )
    raise UnsupportedLLMProviderError(f"unsupported LLM provider: {settings.llm_provider!r}")
