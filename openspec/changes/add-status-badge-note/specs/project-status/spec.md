## Purpose

Lets a new contributor quickly see which efforts in this repo are active and what each one does, without digging through openspec/ change history.

## ADDED Requirements

### Requirement: Repo root status file
The system SHALL provide a `STATUS.md` file at the repo root listing every active effort in the repo with a one-line description, a status label, and a maintainer.

#### Scenario: Contributor reads STATUS.md
- **WHEN** a contributor opens `STATUS.md` at the repo root
- **THEN** they see an entry for `research_chat_agent` and an entry for `dpef-agent`, each with a one-line description and a status label (e.g. active, experimental)

#### Scenario: Contributor sees who owns an effort
- **WHEN** a contributor opens `STATUS.md` at the repo root
- **THEN** each effort's entry names a maintainer they can contact with questions
