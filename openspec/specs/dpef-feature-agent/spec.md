## Purpose

Lets a data product owner (DPO) request a new feature in natural language and have an agent draft the implementation, open it as a pull request, revise it through explicit DPO-approved corrections, and deploy it to production only on the DPO's separate, explicit instruction.

## Requirements

### Requirement: Feature request produces a preview before a PR
The system SHALL accept a free-text feature request from a DPO, generate the implementation on a local working branch, and present the DPO a preview (plan summary and code diff) before opening a pull request. The system SHALL NOT open a pull request until the DPO explicitly confirms the preview.

#### Scenario: DPO requests a new feature
- **WHEN** a DPO submits a free-text feature request
- **THEN** the system creates a per-feature state file with status `developing`, generates conforming code, and presents a plan summary and diff to the DPO without opening a PR

#### Scenario: DPO confirms the preview
- **WHEN** the DPO explicitly confirms a previewed feature
- **THEN** the system opens a pull request from the working branch and updates the feature's state file status to `pr_open`

#### Scenario: DPO requests changes to the preview
- **WHEN** the DPO asks for adjustments before confirming
- **THEN** the system revises the code on the same working branch and presents an updated preview, without opening a PR

#### Scenario: Feature request while another feature is ambiguous
- **WHEN** a DPO's request could plausibly refer to an existing in-progress feature instead of a new one
- **THEN** the system asks the DPO to confirm whether this is a new feature or a continuation before generating code

### Requirement: Per-feature state tracking
The system SHALL maintain one state file per feature, keyed by a unique feature identifier, tracking status, PR number, branch name, and correction history. The system SHALL support multiple features with open PRs concurrently, each tracked independently.

#### Scenario: Multiple features in flight
- **WHEN** a DPO has two or more features with open PRs at the same time
- **THEN** each feature's state (status, PR number, correction history) is tracked in its own state file and updates to one feature's state do not affect another's

#### Scenario: Ambiguous reference to an in-progress feature
- **WHEN** a DPO refers to "the PR" or "the feature" without naming one, and more than one feature is in a non-terminal status
- **THEN** the system lists the in-progress features and asks the DPO which one they mean, rather than guessing

### Requirement: PR comment surfacing without unprompted action
The system SHALL poll the pull request for new comments and review activity on each invocation. When a new DPO comment is found that was not previously surfaced, the system SHALL present the comment content to the DPO and propose a corrective action, but SHALL NOT push a corrective commit until the DPO gives explicit instruction to proceed.

#### Scenario: New PR comment found
- **WHEN** the agent detects a PR comment from the DPO that has not yet been surfaced
- **THEN** it presents the comment and a proposed fix to the DPO and waits for explicit confirmation before making any commit

#### Scenario: DPO confirms the proposed fix
- **WHEN** the DPO explicitly instructs the agent to proceed with a previously proposed fix
- **THEN** the agent makes the corrective commit(s), pushes to the same branch, records the correction in the feature's state file, and updates status to `correcting` then back to `awaiting_review`

#### Scenario: DPO comment is not a correction request
- **WHEN** a new PR comment is a question or does not request a code change
- **THEN** the agent surfaces the comment without proposing a commit, and does not alter the feature's status

### Requirement: Human-gated merge
The system SHALL NOT merge a pull request under any circumstance. Merging SHALL only occur when the DPO merges the PR directly in GitHub.

#### Scenario: PR approved and merged by DPO
- **WHEN** the DPO approves and merges the pull request in GitHub
- **THEN** the system detects the merge on its next poll and updates the feature's state file status to `merged`

#### Scenario: PR rejected
- **WHEN** the DPO closes the pull request without merging
- **THEN** the system updates the feature's state file status to `rejected`, leaves the feature branch in place, and takes no further action on that feature

### Requirement: Deploy gated on explicit instruction
The system SHALL perform a production deploy for a feature only when both of the following hold: the feature's state file status is `merged`, and the DPO has given a separate, explicit instruction to deploy that feature (distinct from the merge action itself).

#### Scenario: Deploy requested after merge
- **WHEN** the feature's status is `merged` and the DPO explicitly instructs the agent to deploy that feature
- **THEN** the system performs the deploy action and updates the feature's state file status to `deployed`

#### Scenario: Deploy requested before merge
- **WHEN** the DPO instructs the agent to deploy a feature whose status is not `merged`
- **THEN** the system refuses the deploy and reports the feature's current status

#### Scenario: Merge alone does not trigger deploy
- **WHEN** a feature's status transitions to `merged`
- **THEN** the system does not deploy automatically and waits for a separate explicit deploy instruction

### Requirement: State claims reconciled against GitHub before deploy
The system SHALL independently verify, via the GitHub API, any claim the state file makes about PR approval or merge status before allowing a deploy to proceed. If the state file's cached status disagrees with GitHub's actual state, the system SHALL overwrite the stale field with the value from GitHub, persist the correction, and then re-evaluate the requested action against the corrected state.

#### Scenario: State file out of sync with GitHub
- **WHEN** the state file claims status `merged` but the GitHub API shows the PR is not actually merged
- **THEN** the system corrects the state file to reflect the PR's actual GitHub status, persists that correction, and refuses the deploy since the corrected status is not `merged`

#### Scenario: State file understates GitHub's actual status
- **WHEN** the state file claims status `awaiting_review` but the GitHub API shows the PR has already been merged
- **THEN** the system updates the state file to `merged` before evaluating any deploy instruction

### Requirement: Repo convention awareness
The system SHALL read the target DPEF repo's structure and conventions (file/solution-area layout, workflow configuration) before generating code for a feature request.

#### Scenario: Feature request generates code
- **WHEN** the agent generates code for a feature request
- **THEN** the generated code's file placement and structure follow the conventions found in the target repo
