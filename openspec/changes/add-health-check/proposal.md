## Why

There's no way to programmatically check whether the research-chat-agent service is up and its dependencies (LLM provider, Firecrawl) are reachable, which makes it hard to monitor.

## What Changes

- Add a health-check capability to research_chat_agent that reports service and dependency status.

## Capabilities

### New Capabilities
- `health-check`: reports whether the service and its configured LLM provider are reachable.

### Modified Capabilities
(none)

## Impact

- Affects: research_chat_agent only (per project config, does not touch dpef-agent).
