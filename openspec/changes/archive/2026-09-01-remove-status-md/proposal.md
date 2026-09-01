## Why

`STATUS.md` and the `project-status` capability existed purely as a test fixture for building and verifying the `openspec-pr-lifecycle` skill (PR creation, comment triage, merge detection, archive-time status reconciliation). That testing is complete; the file and its spec have no further purpose and shouldn't be maintained as if they were a real deliverable.

## What Changes

- Remove `STATUS.md` from the repo root.
- Remove the `project-status` capability's requirement entirely from `openspec/specs/`.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
(none - this is a full removal, not a requirement change)

## Impact

- Affects: repo root (`STATUS.md` deleted), `openspec/specs/project-status/` (spec removed entirely).
