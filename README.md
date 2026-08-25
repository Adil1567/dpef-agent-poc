# dpef-agent-poc

A proof-of-concept repo for testing the `dpef-feature-agent` skill: an agent that turns
a data product owner's (DPO's) free-text feature requests into reviewed pull requests,
with every irreversible step (merge, deploy) gated on explicit human instruction.

## What lives here

- `.claude/skills/dpef-init` — one-time setup for a target repo
- `.claude/skills/dpef-build-feature` — the main workflow: request → preview → PR →
  corrections → merge detection → deploy gate
- `dpef-agent/` — per-feature state tracking and the state helper script
- `.github/workflows/verify-dpef-state.yml` — required CI check that independently
  verifies state file claims against GitHub's real PR status
