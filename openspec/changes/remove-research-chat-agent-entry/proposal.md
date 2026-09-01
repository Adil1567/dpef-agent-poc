## Why

`research_chat_agent` was a LangGraph example used while building and testing the OpenSpec PR-lifecycle extension. It's being removed from the repo to leave only the OpenSpec work itself (schemas, skills) and `dpef-agent`. `STATUS.md`'s spec still requires a `research_chat_agent` entry, which is now stale.

## What Changes

- Remove the `research_chat_agent` requirement from the `project-status` spec's scenario.
- Update `STATUS.md` to drop the `research_chat_agent` row.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `project-status`: the "Contributor reads STATUS.md" scenario no longer requires a `research_chat_agent` entry.

## Impact

- Affects: repo root (`STATUS.md`) and `openspec/specs/project-status/`. No code behavior changes - `research_chat_agent` itself is being deleted, not modified.
