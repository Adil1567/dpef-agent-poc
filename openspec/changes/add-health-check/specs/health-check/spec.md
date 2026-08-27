## Purpose

Lets operators verify the research-chat-agent service and its configured LLM provider are reachable, without manually exercising the chat flow.

## ADDED Requirements

### Requirement: Health check endpoint
The system SHALL expose a health-check that reports overall service status and whether the configured LLM provider is reachable.

#### Scenario: All dependencies reachable
- **WHEN** the health check is invoked and the LLM provider responds
- **THEN** the system reports status "healthy"

#### Scenario: LLM provider unreachable
- **WHEN** the health check is invoked and the configured LLM provider does not respond
- **THEN** the system reports status "degraded" with a reason
