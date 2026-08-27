---
name: dpef-build-feature
description: Turn a DPO's free-text feature request into a reviewed pull request, handle PR corrections, and deploy to production on explicit instruction. Use when a data product owner asks for a new feature, asks about the status of an in-progress feature, wants to respond to review comments, or wants to deploy an approved feature. Requires dpef:init to have been run in this repo first.
allowed-tools: Bash, Read, Write, Edit
license: MIT
metadata:
  author: dpef-agent
  version: "0.1"
---

Implement a DPO's feature request as a reviewed, human-gated pull request; handle corrections through the PR; deploy only on explicit instruction.

**Precondition**: `dpef-agent/config.yaml` must exist (created by `dpef:init`). If it does not, tell the user to run `dpef:init` first and stop.

**Input**: A free-text message from the DPO. It could be:
- A new feature request ("add a customer LTV column to the revenue mart")
- A reference to an in-progress feature ("check on the PR", "fix that comment", "deploy it")
- A response to a previously shown preview or proposed correction ("yes go ahead", "change X instead")

## State machine

```
developing → pr_open → awaiting_review ⇄ correcting → merged → deployed
                              │
                              └──────────────→ rejected
```

Every arrow that writes to GitHub (opening a PR, pushing a commit, deploying) requires an explicit DPO instruction as a separate turn — never inferred from a prior approval, from silence, or from the mere presence of a PR comment.

All state reads/writes go through `dpef-agent/scripts/state_helper.py` (see its `--help` / subcommands: `read`, `create`, `list`, `list-in-progress`, `transition`, `reconcile`, `record-correction`). Never hand-edit or hand-parse the YAML state files directly — always go through the helper so the state machine's allowed transitions are enforced.

## Steps

### 1. Resolve which feature this request is about

- Run `python3 dpef-agent/scripts/state_helper.py list-in-progress` to see features that are not yet `deployed` or `rejected`.
- If the DPO's message clearly names or describes a new feature not matching any in-progress one, treat it as a **new feature request** — go to step 2.
- If the DPO's message is ambiguous (e.g. "check on the PR", "fix that") and there is more than one in-progress feature, list them (feature id + status + one-line description if available) and ask the DPO which one they mean. Do not guess.
- If there is exactly one in-progress feature and the message plausibly refers to it, proceed with that one.
- If the DPO's request could plausibly be either a new feature or a continuation of an existing one, ask them to confirm which, before doing anything else.

### 2. New feature request → preview (no PR yet)

1. Derive a kebab-case feature identifier from the request (e.g. "add customer LTV column" → `add-customer-ltv-column`).
2. Read the target repo's structure and conventions before writing any code: look at existing solution-area/module layout, naming patterns, and any workflow configuration files, so generated code fits in. Do this by exploring the repo (file listing, reading a few representative existing files in the area the new feature touches) — do not assume a layout.
3. Create a local working branch, e.g. `feature/<feature-id>`.
4. Create the state file: `python3 dpef-agent/scripts/state_helper.py create <feature-id> feature/<feature-id> --requested-by <DPO identity if known>`. This sets status `developing`.
5. Generate the code for the request on the working branch, following the conventions found in step 2.
6. Present a **preview** to the DPO: a short plan summary (what you built and why) plus the code diff. Explicitly state that no PR has been opened yet and ask for confirmation to open one.
7. **Do not open a PR yet.** Wait for the DPO's response.

### 3. Handling the DPO's response to a preview

- **If the DPO asks for changes**: revise the code on the same working branch (do not create a new branch or new state file), then present an updated preview. Repeat until confirmed.
- **If the DPO explicitly confirms** (e.g. "looks good", "open the PR", "yes"): open the pull request using the GitHub MCP tools (base = the repo's default branch from `dpef-agent/config.yaml`, head = the working branch). Commit the feature's state file itself into the PR branch (so the CI check described below has something to compare against). Then:
  ```bash
  python3 dpef-agent/scripts/state_helper.py set-pr-info <feature-id> <pr-number> <pr-url>
  python3 dpef-agent/scripts/state_helper.py transition <feature-id> pr_open
  python3 dpef-agent/scripts/state_helper.py transition <feature-id> awaiting_review
  ```
  Report the PR URL to the DPO and tell them review now happens on the PR itself.

### 4. Checking on an in-progress feature (polling)

When invoked for a feature already at `pr_open` or later:

1. Read the feature's state file.
2. Fetch the PR's current comments/review activity via GitHub MCP tools.
3. Compare against `last_seen_comment_id`. For each comment newer than that:
   - **If it requests a code change**: present the comment and a proposed fix to the DPO. Wait for explicit confirmation before making any commit. Do not update `last_seen_comment_id` yet — that happens only once the fix is actually pushed (see step 5), so a comment the DPO hasn't yet acted on is still surfaced on the next check.
   - **If it is a question or does not request a change**: surface it to the DPO as informational. Do not propose a fix. Do not change feature status.
4. Check whether the PR has been merged or closed via GitHub MCP tools:
   - **Merged**: `python3 dpef-agent/scripts/state_helper.py transition <feature-id> merged`. Tell the DPO it's merged and that they can now instruct a deploy.
   - **Closed without merging**: `python3 dpef-agent/scripts/state_helper.py transition <feature-id> rejected`. Tell the DPO the PR was closed; the branch is left in place; no further action is taken on this feature.

### 5. Pushing a correction (only on explicit confirmation)

Only after the DPO has explicitly confirmed a previously proposed fix (never on comment detection alone):

1. `python3 dpef-agent/scripts/state_helper.py transition <feature-id> correcting`
2. Make the corrective code change on the feature's branch, commit, and push.
3. `python3 dpef-agent/scripts/state_helper.py record-correction <feature-id> <comment_id> "<one-line summary>" <commit-sha>` — this also updates `last_seen_comment_id`.
4. `python3 dpef-agent/scripts/state_helper.py transition <feature-id> awaiting_review`
5. Reply on the PR (or tell the DPO in chat) summarizing what changed, so they know to re-review.

### 6. Deploying (only on explicit, separate instruction)

Deploy is never automatic on merge. It requires the DPO to separately and explicitly ask to deploy a named feature.

1. Identify the feature. If ambiguous, ask (same as step 1).
2. Fetch the PR's real merge status directly from the GitHub API (do not trust the cached state file).
3. Reconcile: `python3 dpef-agent/scripts/state_helper.py reconcile <feature-id> <github-reported-status>`. This overwrites and persists the state file if it was stale, and returns the corrected state.
4. If the corrected status is **not** `merged`: refuse the deploy and tell the DPO the feature's actual current status. Stop.
5. If the corrected status **is** `merged`: perform the deploy action (as configured for this DPEF repo's deployment mechanism), then:
   ```bash
   python3 dpef-agent/scripts/state_helper.py transition <feature-id> deployed
   ```
   Confirm success to the DPO.

## Guardrails

- Never open a PR without an explicit DPO confirmation of the preview.
- Never push a corrective commit without an explicit DPO confirmation of that specific fix.
- Never merge a pull request. Merging only happens when the DPO merges it directly in GitHub.
- Never deploy without both: state file status `merged` (reconciled against GitHub immediately beforehand) AND a separate, explicit DPO deploy instruction. A merge event alone never triggers a deploy.
- Never guess which feature an ambiguous request refers to — list in-progress features and ask.
- Never hand-edit state YAML files directly — always go through `state_helper.py` so transitions stay valid.
