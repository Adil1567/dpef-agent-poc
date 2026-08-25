## Purpose

Provides a conversational agent that can decide per turn whether to answer from its own knowledge or invoke a web-research tool, exposed through a chat UI, using a configurable LLM provider (Groq or OpenAI).

## Requirements

### Requirement: Turn-based tool decision
The system SHALL let the LLM decide, independently for each user turn, whether to invoke the web-research tool or respond directly without tool use.

#### Scenario: Question answerable without research
- **WHEN** the user asks a question the LLM can answer from its own knowledge (e.g., "what is 12 * 8?")
- **THEN** the agent responds directly without invoking the research tool

#### Scenario: Question requiring current or external information
- **WHEN** the user asks a question that requires up-to-date or external information (e.g., "what's the latest release of LangGraph?")
- **THEN** the agent invokes the web-research tool and incorporates the results into its response

### Requirement: Web-research tool
The system SHALL provide a web-research tool, backed by Firecrawl, that the agent can call to search and retrieve web content during a turn.

#### Scenario: Research tool returns results
- **WHEN** the agent invokes the research tool with a query
- **THEN** the tool returns search results or page content that the agent can use to compose its response

#### Scenario: Research tool fails or returns no results
- **WHEN** the research tool call fails (e.g., network error, API error) or returns no usable results
- **THEN** the agent informs the user that research could not be completed and still attempts to respond using its own knowledge where possible

### Requirement: Configurable LLM provider
The system SHALL support running the agent against Groq or OpenAI, selectable via configuration without code changes to the agent logic, configured via an API key and model name without hard-coding secrets in source.

#### Scenario: Switching provider via configuration
- **WHEN** the configured LLM provider is changed from Groq to OpenAI (or vice versa)
- **THEN** the agent operates correctly using the newly configured provider without requiring changes to the agent graph or tool code

#### Scenario: Missing credentials for the configured provider
- **WHEN** the API key for the currently configured provider is not set
- **THEN** the system reports a clear configuration error instead of failing silently or crashing unhandled

### Requirement: Chat interface
The system SHALL provide a Gradio-based chat interface where a user can send messages to the agent and view its responses within a session.

#### Scenario: User sends a message and receives a response
- **WHEN** a user submits a message in the Gradio chat UI
- **THEN** the UI displays the agent's response in the conversation

#### Scenario: Multi-turn conversation within a session
- **WHEN** a user sends multiple messages in the same session
- **THEN** the agent has access to the prior turns of that session when generating each response

### Requirement: No document ingestion or retrieval
The system SHALL NOT provide document upload, ingestion, embedding, or retrieval-augmented generation in this iteration.

#### Scenario: User attempts to upload a document
- **WHEN** a user looks for a way to upload or reference a document in the chat UI
- **THEN** no such capability is present; the UI only supports text chat with the research tool
