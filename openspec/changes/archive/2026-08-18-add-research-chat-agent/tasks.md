## 1. Project setup

- [x] 1.1 Initialize Python project structure and dependency management (e.g., `pyproject.toml`/`requirements.txt`)
- [x] 1.2 Add dependencies: `langgraph`, `langchain`, `langchain-groq`, `langchain-openai`, Firecrawl client, `gradio`
- [x] 1.3 Set up configuration/env var loading for LLM provider selection, provider API keys, and Firecrawl API key
- [x] 1.4 Add `.env.example` (or equivalent) documenting required environment variables

## 2. LLM provider abstraction

- [x] 2.1 Implement a provider-selection function that returns a LangChain chat model instance based on configuration (Groq or OpenAI)
- [x] 2.2 Verify tool-calling works against both providers with a minimal smoke test (Groq and OpenAI both verified live)

## 3. Research tool

- [x] 3.1 Implement a LangChain tool wrapping Firecrawl search (and/or scrape) for web research
- [x] 3.2 Handle Firecrawl error/empty-result cases and return a usable message to the agent

## 4. Agent graph

- [x] 4.1 Define the LangGraph state (conversation messages, in-memory per session)
- [x] 4.2 Implement the router/decision node using LLM tool-calling with the research tool bound
- [x] 4.3 Implement the direct-answer path (no tool call)
- [x] 4.4 Implement the tool-call path: invoke research tool, feed results back to the LLM, produce final response
- [x] 4.5 Wire the graph edges (router → direct-answer or research loop back to router → end when no more tool calls; see design.md for why this replaced a separate synthesize node)
- [x] 4.6 Add in-memory conversation history handling across turns within a session

## 5. Chat UI

- [x] 5.1 Build a Gradio chat interface that sends user messages to the agent graph and displays responses
- [x] 5.2 Wire per-session state so conversation history persists across turns within a browser session but not across restarts
- [x] 5.3 Surface tool/provider errors in the UI (e.g., research failure, rate limit) as visible chat messages

## 6. Validation

- [x] 6.1 Manually verify: a question answerable without research returns a direct answer (no tool call) — verified with Groq: "What is 12 * 8?" answered directly, no tool call
- [x] 6.2 Manually verify: a question requiring current info triggers the research tool and the response reflects tool results — verified with Groq: research question triggered `web_research`, results were incorporated into the final answer
- [x] 6.3 Manually verify: switching the configured provider (Groq ↔ OpenAI) works without code changes; a missing API key for the selected provider produces a clear configuration error — both verified live: Groq and OpenAI each answered a direct question and a research question correctly when selected via `LLM_PROVIDER`, and a missing `OPENAI_API_KEY` raised a clear config error
- [x] 6.4 Manually verify: a Firecrawl failure/empty result is handled gracefully and reported to the user — verified: simulated Firecrawl error returns a usable fallback message instead of crashing; also fixed a real bug found here where empty Firecrawl responses were misreported due to reading the wrong response field (`.data` instead of `.web`)
