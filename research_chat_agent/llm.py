from langchain_core.language_models.chat_models import BaseChatModel

from research_chat_agent.config import get_groq_config, get_llm_provider, get_openai_config


def get_chat_model() -> BaseChatModel:
    """Return a LangChain chat model for the configured provider.

    Provider is selected via the LLM_PROVIDER env var ("groq" or "openai").
    Agent/graph code depends only on BaseChatModel, so switching providers
    requires no changes beyond configuration.
    """
    provider = get_llm_provider()

    if provider == "groq":
        from langchain_groq import ChatGroq

        cfg = get_groq_config()
        return ChatGroq(model=cfg["model"], api_key=cfg["api_key"], temperature=0)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        cfg = get_openai_config()
        return ChatOpenAI(model=cfg["model"], api_key=cfg["api_key"], temperature=0)

    raise ValueError(f"Unhandled provider: {provider}")
