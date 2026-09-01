## Purpose

Lets a new contributor understand how to propose, review, and land a change in this repo without having to reverse-engineer the OpenSpec + PR-lifecycle workflow from source.

## ADDED Requirements

### Requirement: Root-level contributing guide
The system SHALL provide a `CONTRIBUTING.md` file at the repo root describing the change lifecycle: propose, implement, PR review, merge, archive.

#### Scenario: New contributor reads CONTRIBUTING.md
- **WHEN** a contributor opens `CONTRIBUTING.md` at the repo root
- **THEN** they see the sequence of `openspec` commands used to propose, implement, and archive a change, in order
