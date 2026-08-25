## Context

See proposal.md - Why. This is a greenfield project with no existing code or specs. This is iteration 1 of a two-iteration plan; iteration 2 (a follow-up change) adds document ingestion and RAG via Chroma. Building the agent graph now with a router node keeps the door open to add a retrieval branch later without restructuring.

## Goals / Non-Goals

**Goals:**
- A working LangGraph agent with a decision node that routes each turn to either direct-answer or research-tool-call.
- A Firecrawl-backed research tool the agent can call.
- Groq or OpenAI as the LLM provider, selectable via configuration, without touching graph/tool code.
- A minimal Gradio chat UI to interact with the agent, with per-session conversation history.

**Non-Goals:**
- Document upload, chunking, embeddings, vector storage, or retrieval (deferred to iteration 2).
- Persisting conversation history across process restarts (in-memory per session is sufficient for this iteration).
- Multi-user auth/session isolation beyond what Gradio provides by default.
- Streaming token-by-token responses (nice-to-have, not required for this iteration).

## Decisions

### LangGraph over a plain LangChain agent executor
A graph with an explicit router node makes the "answer directly vs. call research tool" decision inspectable and gives iteration 2 a clean place to add a retrieval branch. A plain agent executor's tool-loop would need to be restructured later anyway.

### Router = LLM tool-calling, not a separate classifier
The router node is implemented as a single LLM call with the research tool bound (standard tool-calling), rather than a separate classification step. This keeps latency and complexity down and matches how Groq's tool-calling API works. Alternative considered: a dedicated small classifier model to decide route — rejected as unnecessary complexity for a prototype.

### Graph shape: router ⇄ research loop, not router → research → synthesize → end
Implementation revealed that a separate "synthesize" node calling the LLM *without* tools bound breaks on Groq (`openai/gpt-oss-120b`): after a tool round trip, the model still attempts to emit a tool call, and the API rejects that when no tools are declared on that call. The fix is the standard ReAct shape: the router node keeps tools bound on every invocation, including after a tool result comes back, and the graph loops `research → router` instead of `research → synthesize → end`. The router itself decides when to stop (no more tool calls → end). This also naturally supports multi-step research (the model retried several search queries before giving up in testing) without extra graph plumbing.

### Groq and OpenAI as supported providers, behind the LangChain chat model interface
`get_chat_model()` reads `LLM_PROVIDER` (`groq` or `openai`) and returns either `ChatGroq` (`GROQ_API_KEY`/`GROQ_MODEL`) or `ChatOpenAI` (`OPENAI_API_KEY`/`OPENAI_MODEL`). The graph/tool code depends only on the LangChain `BaseChatModel` interface, not a specific provider SDK, so this switch is a contained change to one function. Groq stays the default for prototyping without cost; OpenAI is there as an option when reliability/quality matters more than free-tier limits (e.g. rate-limit testing was hitting Groq's 8000 TPM cap - see Risks below - and OpenAI has no such free-tier ceiling, at the cost of paying per token).

Gemini (considered in an earlier iteration of this design) was dropped in favor of OpenAI: OpenAI's tool-calling behavior is the most consistently reliable across LangChain integrations, which matters since the router's correctness depends entirely on tool-calling working the same way regardless of provider.

### Firecrawl as the sole research tool
Firecrawl's search/scrape API is used directly (via its Python SDK/API, with an API key), exposed to the agent as a single LangChain tool. Alternative considered: Tavily — rejected only because the user has direct Firecrawl access already; either would satisfy the requirement, and swapping later is a contained change since the tool is a single bound function.

Firecrawl search results can include full page markdown in the `description` field (sometimes several KB per result). Combined with Groq's free-tier token-per-minute limit (8000 TPM on `openai/gpt-oss-120b`), returning multiple untruncated results caused live 413 "request too large" errors. The tool caps results to 3 and truncates each description to 300 characters before returning them to the model.

### Conversation memory: in-process, per Gradio session
Conversation history is held in memory for the duration of a Gradio session (e.g., via Gradio's built-in chat state or a simple in-memory checkpointer keyed by session), not persisted to disk or a database. This matches the proposal's explicit exclusion of Chroma/persistence from this iteration.

## Risks / Trade-offs

- [Groq free-tier rate/token limits (8000 TPM on `openai/gpt-oss-120b`) cause real 413 errors under normal use, e.g. a research tool result plus conversation history can exceed the limit in one call] → Research tool truncates/caps results (see Firecrawl decision below); OpenAI is available as a switch when Groq's limits are too tight for a session.
- [Groq model availability changes over time — the originally chosen default (`llama-3.3-70b-versatile`) was already deprecated during implementation] → Default model is a config value (`GROQ_MODEL`), not hard-coded in logic; verified live with `openai/gpt-oss-120b`.
- [OpenAI usage costs money per token, unlike Groq's free tier] → Documented in `.env.example`; OpenAI is opt-in via `LLM_PROVIDER=openai`, Groq remains the default.
- [No persistence means conversation and any research context is lost on restart] → Acceptable for a prototype; explicitly called out as a non-goal.
- [Firecrawl API key management] → Load via environment variable/config, not hard-coded; document required env vars in setup instructions.

