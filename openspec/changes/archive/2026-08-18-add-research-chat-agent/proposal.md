## Why

We want a conversational agent that can decide, per turn, whether to answer directly or use a web-research tool to look up current information, as the first iteration of a broader "chat with your documents" assistant. Document ingestion and retrieval (RAG) are deferred to a later change; this iteration focuses on getting the agent loop, tool-calling, and chat UI working end-to-end with free/low-cost LLMs.

## What Changes

- Add a LangGraph agent graph with a router/decision node: the LLM decides each turn whether to call the web-research tool or answer directly from its own knowledge.
- Add a web-research tool backed by Firecrawl (search/scrape) that the agent can invoke.
- Support Groq (free-tier) and OpenAI (paid, optional) as LLM providers, selectable via configuration, so the agent isn't hard-coded to one provider.
- Add a Gradio chat UI for interacting with the agent (text in, streamed/response text out).
- No document ingestion, embeddings, or vector store in this iteration — RAG is explicitly out of scope and planned as a follow-up change.

## Capabilities

### New Capabilities
- `research-chat-agent`: A chat agent that, per user turn, decides whether to invoke a web-research tool (Firecrawl) or answer directly, using Groq or OpenAI as the configured LLM, exposed through a Gradio chat interface.

### Modified Capabilities
(none — greenfield project, no existing specs)

## Impact

- New Python application code: LangGraph graph definition, Firecrawl tool wrapper, LLM provider configuration, Gradio app entrypoint.
- New dependencies: `langgraph`, `langchain`, `langchain-groq`, `langchain-openai`, Firecrawl client, `gradio`.
- New configuration/secrets: Groq API key and/or OpenAI API key (whichever provider is selected), and Firecrawl API key.
- No impact on existing systems (this is a new, standalone capability in a greenfield project).
