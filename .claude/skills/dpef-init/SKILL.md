---
name: dpef-init
description: One-time setup for the DPEF feature agent in a target repo. Use when a DPO or repo admin wants to start using dpef:build-feature in a repo for the first time, or wants to check its current configuration.
allowed-tools: Bash, Read, Write
license: MIT
metadata:
  author: dpef-agent
  version: "0.1"
---

Set up the DPEF feature agent (`dpef:build-feature`) in the current repo.

**Input**: None required. Optionally the user may name a target repo path if they are not already inside it.

**Steps**

1. **Determine the target repo**

   The target repo is the current working directory unless the user names a different path. Confirm it is a git repository:
   ```bash
   git rev-parse --show-toplevel
   ```
   If this fails, tell the user this must be run inside a git repository and stop.

2. **Check for existing setup (idempotency)**

   Check whether `dpef-agent/config.yaml` already exists in the repo root.

   - **If it exists**: read and display its current contents (target repo path, any settings) to the user. Ask if they want to re-run setup anyway (e.g. to change the configured repo path) or leave it as-is. Do NOT overwrite silently. Stop here unless the user explicitly asks to redo setup.
   - **If it does not exist**: continue to step 3.

3. **Scaffold the state directory**

   Create `dpef-agent/state/` in the repo root if it does not already exist (empty directory is fine — feature state files are created later by `dpef:build-feature`). Add a `.gitkeep` or similar if needed so the empty directory can be committed, unless the repo already tracks empty dirs some other way.

4. **Write the config file**

   Create `dpef-agent/config.yaml` with:
   ```yaml
   target_repo: <owner/repo, e.g. Adil1567/dpef-agent-poc>
   default_branch: <the repo's default branch, e.g. main>
   initialized_at: <ISO8601 timestamp>
   ```
   Determine `owner/repo` from the git remote (`git remote get-url origin`), parsing the GitHub owner/repo out of the URL. If there is no remote configured, ask the user for the GitHub `owner/repo` this will eventually be pushed to — `dpef:build-feature` needs this to know where to open PRs and poll comments.

5. **Verify GitHub access**

   Using the GitHub MCP tools, make a minimal read call against the configured repo (e.g. fetch repo details or list pull requests with a small limit) to confirm:
   - The authenticated GitHub identity has read access to `target_repo`
   - The repo actually exists at that path

   If this fails, report the specific error (auth failure vs. repo-not-found vs. no permission) so the user can fix credentials or the repo path before trying `dpef:build-feature`. Do not proceed past this step silently — a broken credential should surface now, not on the DPO's first real feature request.

6. **Confirm completion**

   Show the user:
   - The config that was written (`target_repo`, `default_branch`)
   - That `dpef-agent/state/` is ready
   - That GitHub access was verified
   - Next step: they can now use `dpef:build-feature` to request a feature

**Guardrails**
- Never overwrite an existing `dpef-agent/config.yaml` without the user's explicit confirmation to redo setup.
- Always verify GitHub access before declaring setup complete — a config file that points at an inaccessible repo is worse than no config, since it will fail confusingly later instead of clearly now.
- Do not guess the target repo's owner/repo path if it cannot be determined from the git remote — ask the user rather than assuming.
