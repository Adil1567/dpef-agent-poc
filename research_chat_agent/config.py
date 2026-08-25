import os

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    pass


def get_llm_provider() -> str:
    provider = os.environ.get("LLM_PROVIDER", "groq").strip().lower()
    if provider not in ("groq", "openai"):
        raise ConfigError(
            f"Unsupported LLM_PROVIDER '{provider}'. Expected 'groq' or 'openai'."
        )
    return provider


def get_groq_config() -> dict:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("GROQ_API_KEY is not set.")
    return {
        "api_key": api_key,
        "model": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
    }


def get_openai_config() -> dict:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("OPENAI_API_KEY is not set.")
    return {
        "api_key": api_key,
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    }


def get_firecrawl_api_key() -> str:
    api_key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("FIRECRAWL_API_KEY is not set.")
    return api_key
