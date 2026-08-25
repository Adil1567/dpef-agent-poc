from langchain_core.tools import tool

from research_chat_agent.config import get_firecrawl_api_key


def _get_firecrawl_client():
    from firecrawl import FirecrawlApp

    return FirecrawlApp(api_key=get_firecrawl_api_key())


@tool
def web_research(query: str) -> str:
    """Search the web for current or external information relevant to the query.

    Use this when the answer requires information beyond your own knowledge,
    such as recent events, current data, or specific facts you're not certain of.
    Returns a text summary of the most relevant search results found.
    """
    try:
        app = _get_firecrawl_client()
        result = app.search(query, limit=3)
    except Exception as exc:
        return (
            "Web research failed due to an error contacting the research "
            f"service ({exc}). Answer using your own knowledge if possible, "
            "and tell the user that research could not be completed."
        )

    if isinstance(result, dict):
        data = result.get("web") or result.get("data")
    else:
        data = getattr(result, "web", None) or getattr(result, "data", None)
    if not data:
        return (
            "Web research returned no results for this query. Answer using "
            "your own knowledge if possible, and tell the user that no "
            "research results were found."
        )

    max_description_chars = 300
    lines = []
    for item in data[:3]:
        if isinstance(item, dict):
            title = item.get("title", "")
            url = item.get("url", "")
            description = item.get("description", "")
        else:
            title = getattr(item, "title", "")
            url = getattr(item, "url", "")
            description = getattr(item, "description", "")
        # Firecrawl descriptions can contain full page markdown, which is far
        # more than a small-context/free-tier model's token budget can take.
        description = (description or "").strip().replace("\n", " ")
        if len(description) > max_description_chars:
            description = description[:max_description_chars].rstrip() + "..."
        lines.append(f"- {title} ({url}): {description}")

    return "Web research results:\n" + "\n".join(lines)
