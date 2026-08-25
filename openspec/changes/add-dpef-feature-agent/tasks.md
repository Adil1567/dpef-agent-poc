## 1. State helper script

- [x] 1.1 Define the per-feature YAML state schema (feature, status, branch, pr_number, pr_url, requested_by, created_at, updated_at, last_seen_comment_id, correction_history)
- [x] 1.2 Write `dpef-agent/scripts/state_helper.py` with read/write functions for `dpef-agent/state/<feature>.yaml`, including safe creation when the file doesn't yet exist
- [x] 1.3 Add a "list features by status" function (used for disambiguation when a DPO refers to "the feature" ambiguously)
- [x] 1.4 Add the state transition function enforcing the allowed state machine edges (`developing → pr_open → awaiting_review ⇄ correcting → merged → deployed`, or `→ rejected`)
- [x] 1.5 Add the reconciliation function: given a feature's cached status and a GitHub-reported status, overwrite and persist the cached value when they disagree, returning the corrected status

## 2. `dpef:init` skill

- [x] 2.1 Write `.claude/skills/dpef-init/SKILL.md`: scaffolds `dpef-agent/state/` and a config file (target repo path, any settings) in the current repo
- [x] 2.2 Include a GitHub access check in the init flow (e.g. a minimal API call) so credential/permission problems surface at setup time, not mid feature-request
- [x] 2.3 Make init idempotent — running it again when already set up reports current config rather than overwriting silently

## 3. `dpef:build-feature` skill — request to preview

- [x] 3.1 Write `.claude/skills/dpef-build-feature/SKILL.md` covering the full lifecycle described below
- [x] 3.2 Instructions for reading the target repo's file/solution-area layout and workflow conventions before generating any code
- [x] 3.3 Instructions for intake of a free-text feature request: derive a feature identifier, and disambiguate against existing in-progress features (using the "list by status" helper) if the request is ambiguous
- [x] 3.4 Instructions to create the state file at status `developing` (via the state helper) and a local working branch
- [x] 3.5 Instructions to generate code on the working branch following the read conventions, then present a plan summary and diff preview to the DPO — explicitly no PR yet
- [x] 3.6 Instructions for handling DPO-requested revisions to the preview (regenerate on the same branch, re-present) before any confirmation
- [x] 3.7 Instructions to open the PR (GitHub MCP tools) only on explicit DPO confirmation, then transition state to `pr_open` → `awaiting_review`. Commit the state file itself into the PR branch so the CI check (section 6) has something to read.

## 4. `dpef:build-feature` skill — correction loop

- [x] 4.1 Instructions to poll the PR for comments/review activity newer than `last_seen_comment_id` on each invocation
- [x] 4.2 Instructions to classify each new DPO comment as a correction request or not; surface non-correction comments without proposing a fix
- [x] 4.3 Instructions to present a proposed fix for a correction-requesting comment and wait for explicit DPO confirmation — never commit automatically
- [x] 4.4 Instructions to, on confirmation: transition to `correcting`, commit and push the fix, append to `correction_history`, update `last_seen_comment_id`, transition back to `awaiting_review`

## 5. `dpef:build-feature` skill — merge, rejection, deploy

- [x] 5.1 Instructions to detect PR merge via GitHub API and transition state to `merged`
- [x] 5.2 Instructions to detect PR closure-without-merge and transition state to `rejected`, leaving the branch in place
- [x] 5.3 Instructions for the deploy action: triggered only by an explicit DPO instruction naming a specific feature
- [x] 5.4 Instructions to re-verify PR/merge status directly via GitHub API at that moment (call the reconciliation helper) — this is the agent's own synchronous check, done right before acting, not a wait for an external signal
- [x] 5.5 Instructions to refuse the deploy with the corrected current status unless that corrected status is `merged`
- [x] 5.6 Instructions to perform the deploy action and transition state to `deployed` on success

## 6. CI enforcement (runs automatically on GitHub, independent of the agent)

- [ ] 6.1 Write `.github/workflows/verify-dpef-state.yml`: triggered automatically by GitHub on every push to a PR branch — no manual or agent-initiated trigger. It re-fetches the PR's real approval/merge status from the GitHub API and compares it against the `dpef-agent/state/<feature>.yaml` committed in that branch; fails (red X on the PR) if they disagree
- [ ] 6.2 You (repo admin) mark this check as required in the target repo's branch protection settings, and separately enable "require approving review before merge" — this makes merging physically blocked while the check is red, so nothing needs to separately "notify" anyone of a mismatch after the fact
- [ ] 6.3 Document that this CI check only guards the merge step, not the deploy step — the deploy step's own guard is the synchronous check in task 5.4, done by the agent at the moment it acts

## 7. Evaluation

- [ ] 7.1 Write `claude plugin eval` cases covering: a question-only comment produces no commit; a correction comment + explicit confirmation produces a commit; a deploy instruction before merge is refused; a deploy instruction with a deliberately stale "merged" state file gets corrected and still refused
- [ ] 7.2 Manually verify: a feature request produces a preview (not a PR) and the PR opens only after explicit confirmation
- [ ] 7.3 Manually verify: two features tracked concurrently do not interfere with each other's state files
- [ ] 7.4 Manually verify: the agent never merges a PR under any circumstance — merge only happens via direct DPO action in GitHub
- [ ] 7.5 Manually verify: closing a PR without merging transitions state to `rejected` and leaves the branch in place
- [ ] 7.6 Manually verify: `dpef:init` run a second time reports existing config rather than overwriting it
- [ ] 7.7 Manually verify: a PR whose committed state file deliberately disagrees with GitHub's real merge status shows a failing required check and cannot be merged
