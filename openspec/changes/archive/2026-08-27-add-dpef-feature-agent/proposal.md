## Why

Data engineers face scalability limitations due to their human nature — a single data product owner cannot evolve a data product at the speed the business needs. The goal is to build an agent that understands a DPEF project's structure and conventions, implements new features on request, opens a pull request for human review, handles corrections via PR comments, and deploys to production once approved. This PoC validates that an agent can safely operate within human-gated guardrails (DPO reviews and approves before any merge or deploy), with no capability to unilaterally push to production.

## What Changes

- Add an agent skill (`dpef:build-feature`) that takes a free-text feature request from a DPO and produces working code on a new branch, opened as a PR for review.
- Implement a state machine and per-feature state file tracking: `developing → pr_open → awaiting_review → correcting → merged → deployed` (or `rejected` if the DPO closes the PR).
- Add a correction loop: the agent reads PR comments, makes additional commits to the same branch if the DPO requests changes, and polls GitHub for approval/merge status.
- Add a deploy action gated so it fires only when status is `merged` *and* the DPO gives an explicit, separate instruction to deploy.
- Wire the skill to read the DPEF repo's conventions (file structure, solution area layout, workflow config) before generating code, so it produces features that fit the existing architecture.
- Add CI/GitHub enforcement: a required status check that independently verifies (via GitHub API) any claim the state file makes before trusting it downstream.

## Capabilities

### New Capabilities
- `dpef-feature-agent`: An agent skill that reads DPEF project conventions, implements features, manages PR lifecycle (open, correction, merge), and handles production deployment under explicit DPO instruction. Includes per-feature state tracking and GitHub enforcement of approval/merge gates.

### Modified Capabilities
(none — this is new functionality, no existing capability behavior changes)

## Impact

- New agent skill: `dpef:build-feature`, reusable per DPEF repo by configuring the target repo path and credentials.
- New local state schema: a per-feature YAML file tracking PR number, status, correction history.
- New GitHub Action / CI check: verifies state claims before they're trusted (enforcement layer).
- Dependencies: Python, LangGraph (if code generation uses LLM), GitHub MCP tools (PR operations).
- Workflow impact: DPO can now request features asynchronously; agent handles drafting and PR mechanics; DPO's time spent is only on review/approval, not on typing commands to apply patches.
