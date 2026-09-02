---
name: openspec-pr-lifecycle
description: Open a pull request for a completed OpenSpec change, poll it for review comments, and triage each comment as either a code fix or a real spec/design gap. Use when a change's tasks are all done and it's time to open a PR, when checking on an open PR's review status, or when responding to PR comments for a change using the spec-driven-pr schema.
allowed-tools: Bash(openspec:*), Read, Write, Edit
license: MIT
metadata:
  author: openspec
  version: "0.1"
---

Open a PR for an OpenSpec change's implemented branch, track it in `pr.md`, and handle review comments by fixing code directly for bugs or looping back through the planning artifacts for real spec gaps.

**Precondition**: The change must use a schema with a `pr` artifact (e.g. `spec-driven-pr`) and every task in `tasks.md` must actually be checked off - not merely that `tasks.md` exists. `openspec status`'s artifact-level `done` for `tasks` means only "the file exists," which is true the moment `tasks.md` is created, even with every box still unchecked - it is not checkbox-aware. Use `openspec instructions apply` instead (see step 1), which genuinely parses `- [x]` vs `- [ ]` and returns a `progress` count. If any task remains unchecked, tell the user to finish `/opsx:apply` first and stop.

**Model: one change, one PR.** A change (proposal + specs + design + tasks) is already scoped to one coherent unit of review, so it maps 1:1 to one branch and one PR. `pr.md` tracks exactly one PR for the life of the change. This skill does not open a second PR for a change that already has one recorded — see the "Abandoned PR" case below for the one exception.

**Input**: A change name, plus what's being asked:
- Open the PR for a change whose tasks are complete ("open a PR for add-health-check")
- Check on an already-open PR ("check the PR for add-health-check", "any new comments?")
- A user response to a previously surfaced comment ("yes fix it", "that's a real gap, update the spec")

## Where state lives

There is no separate state file. `pr.md` (the change's `pr` artifact, at the path `openspec instructions pr --change "<name>" --json` resolves to) is both the OpenSpec artifact and this skill's own memory: it holds the PR URL/number/status and a Review Log of every comment this skill has already processed. Read it fresh from disk each time — never rely on a cached view from earlier in the conversation.

## Steps

### 1. Resolve the change and confirm preconditions

```bash
openspec status --change "<name>" --json
```

- If `pr` does not exist as an artifact on this change's schema, tell the user this schema doesn't support PR tracking (they'd need `spec-driven-pr` or a schema that includes a `pr` node) and stop.

Then confirm task completion with the checkbox-aware command, not the artifact-level status above:

```bash
openspec instructions apply --change "<name>" --json
```

- Check `progress.remaining` in the response. **If it is not `0`, stop and tell the user to finish `/opsx:apply` first** - do not proceed to open a PR. `openspec status`'s `tasks: "done"` only means `tasks.md` exists on disk; it does not mean every checkbox is checked, so it must never be used alone as the completion signal here.
- If `progress.remaining` is `0`, tasks are genuinely complete - proceed to step 2.

### 2. Opening the PR (pr.md does not exist yet, or has no PR URL recorded)

1. Get the artifact instructions and resolved path:
   ```bash
   openspec instructions pr --change "<name>" --json
   ```
2. Determine the implementation branch (the branch `/opsx:apply`'s commits were made on — ask the user if it's not obvious from git state).
3. Open the pull request using the GitHub MCP tools (base = the repo's default branch, head = the implementation branch).
4. Write `pr.md` at the resolved output path using the schema's `pr.md` template: fill in PR URL, PR Number, Status (`open (as of creation — ask this skill or check GitHub for current status)`), Branch. Leave the Review Log section empty (no entries yet).
5. Report the PR URL to the user.

Do not open a PR without the tasks being complete. Do not open a second PR for a change that already has one recorded in `pr.md` — if `pr.md` already has a PR URL and `Status` is not `closed`, treat this request as a poll (step 3) instead.

### 3. Polling for comments (pr.md already has a PR URL)

1. Read `pr.md` from disk to get the PR number and the highest comment ID already logged in the Review Log.
2. Fetch the PR's current comments/review activity via GitHub MCP tools.
3. Fetch the PR's current CI status via GitHub MCP tools (combined commit status and/or check runs for the head commit) and **report it to the user directly in conversation** alongside the comment summary (e.g. "CI: 2 checks passing, 1 failing (lint)" or "CI: all checks passing" or "CI: no checks configured on this PR"). This is read-only visibility, not a gate this skill enforces - it never blocks opening a PR, triaging a comment, or reporting merge status. If the repo has no CI configured, or the check-runs/status lookup returns nothing, say so plainly rather than treating it as a failure to report.
   - If any check is failing and no comment already covers it, surface the failing check name(s) to the user as information, same as an informational comment - do not propose a fix unless the user asks, and do not log it in the Review Log (CI status is not a comment; the Review Log is for comment triage only, so this is intentionally a separate, ephemeral report re-fetched fresh on each poll rather than something to deduplicate against).
4. For each comment newer than the highest logged ID, triage it (step 4). Do not advance past a comment in the Review Log until its action is actually complete — an unresolved comment stays unlogged so it's re-surfaced on the next poll.
5. Check merge/close status via GitHub MCP tools and **report it to the user directly in conversation** (e.g. "PR #5 is merged"). Do **not** write this back to `pr.md` on its own — see "Why Status isn't updated live" below. The only exception is while a comment-triage cycle already has a real code/artifact change to commit (step 4a/4b) — in that one case, also refresh the Status field as part of that same commit, since a PR is already required for it.
6. **If GitHub now reports the PR as merged or closed, and `pr.md`'s stored Status field still shows the "open (as of creation...)" placeholder** (i.e. this is the first time you've observed the terminal state): add a brief, non-blocking suggestion to archive, in the same response - do not turn it into a separate question or wait for an answer before continuing:
   - Merged: "PR #5 is merged. Per OpenSpec's recommended workflow, changes are archived after their PR merges — say the word if you'd like me to do that now."
   - Closed without merging: "PR #5 was closed without merging. If this attempt is done, I can archive it to keep the record accurate — or if you want to retry, let me know and I'll open a new PR on the same change instead."
   Mention this once per terminal-state transition, not on every subsequent poll of an already-resolved PR - if the user doesn't act on it, don't repeat the suggestion next time they check the same change.

### Why Status isn't updated live

Many teams (including environments with mandatory-PR branch protection on `main`) require every write to `main` to go through review. A bare `pr.md` status flip ("open" → "merged") is bookkeeping, not code under review, and doesn't deserve its own single-purpose PR — that's wasted process for a one-line change. So:

- `pr.md`'s `Status` field is set once at creation (`open`) and is **not** kept live-synced with GitHub on every poll.
- Label it honestly so nobody is misled by stale data: write it as `Status: open (as of creation — ask this skill or check GitHub for current status)`.
- The field only gets refreshed as a **side effect of a commit that already has another reason to exist** — either a comment-triage commit (4a/4b above), or during `/opsx:archive`, which already needs its own PR to move the change directory. The archive workflow should, as part of that same PR, read the change's `pr.md` and current GitHub PR status, and update the Status field to match before archiving. If you are implementing or invoking `/opsx:archive` for a change with a `pr` artifact, include this refresh.
- Never open a dedicated PR whose only content is a `pr.md` status update. If asked to do so, explain this convention and suggest waiting for the next real commit or archive instead.

### 4. Triaging a comment

For each new comment, decide which bucket it falls in. When genuinely unclear, ask the user rather than guessing — this classification decides whether OpenSpec's planning artifacts get touched.

**a) Pure implementation bug** — the code doesn't match what proposal/specs/design/tasks already say (the plan was already correct, the code just didn't follow it):
- Fix the code directly, commit, push to the same branch.
- Log the resolution in `pr.md`'s Review Log only. Do **not** touch tasks.md, specs, design.md, or proposal.md — the plan didn't change, so the artifacts describing it don't need to change. See the Review Log entry format below.
- Exception (rare, judgment call): if the fix is significant enough that a future reader of tasks.md would be confused why shipped behavior doesn't match what's checked off (e.g. it changes an interface, not just an internal detail), still log it in `pr.md` as the primary record, but also add one explanatory line to the relevant artifact — never a new task, just a footnote so the artifacts stay trustworthy.

**b) Real spec/design gap** — the comment reveals a new requirement, changed behavior, or a design flaw that was never specified:
- Do not silently patch code to cover it.
- Surface the gap to the user explicitly: quote the comment, explain what's missing from the spec, propose how you'd revise it. Wait for confirmation.
- On confirmation, invoke `/opsx:update` (the `openspec-update-change` skill) to revise `proposal.md` / `specs/*.md` / `design.md` / `tasks.md` coherently. This should add new unchecked tasks for the gap.
- Then invoke `/opsx:apply` to implement the new/changed tasks.
- Push the resulting commits to the same PR branch.
- Log the resolution in `pr.md`, including which artifacts were touched.

**c) Question or non-actionable comment**:
- Surface it to the user as informational. No code change, no artifact change.
- Log it in the Review Log with `Classification: informational` so it doesn't get re-surfaced on the next poll (still record it, just with `Action: None`).

### Review Log entry format

Append one entry per comment to `pr.md`'s Review Log section:

```markdown
### <YYYY-MM-DD> — Comment #<id>
**From:** <author>
**Comment:** "<comment text, verbatim or close paraphrase>"
**Classification:** <implementation bug | spec gap | informational>
**Action:** <what was done, or "None — answered in PR thread">
**Artifacts touched:** <none, or list of paths like specs/health-check/spec.md, design.md, tasks.md>
```

### Abandoned PR (the one exception to "one change, one PR")

If `pr.md` shows `Status: closed` (closed without merging) and the user explicitly asks to restart — e.g. "the approach was wrong, let's redo this PR" — treat it as a deliberate reset, not an automatic action:
1. Confirm with the user that they want a new PR for the same change, not a new change.
2. Append a final Review Log entry noting the old PR was abandoned and why.
3. Open a new PR (step 2 above) and overwrite the PR URL/Number/Status/Branch fields with the new PR's info.
Never do this automatically just because `Status` reads `closed` — always require an explicit user instruction to restart.

### Only the "archive after merge" convention is supported

OpenSpec's own team-workflow docs describe two conventions: archive after the PR merges (recommended), or archive inside the same PR as the code. **Only the first is supported when a `pr` artifact is involved.** Archiving inside the code PR is structurally incompatible with this skill's design: `/opsx:archive`'s step 2.5 needs to read the PR's final GitHub status (merged or closed) to write an accurate `pr.md` Status field, but that status doesn't exist yet while the code PR is still open and its own commits are being written. Archiving at that point would either write a guess or a value that becomes wrong the moment the PR gets more review activity, and if the PR is later rejected or needs rework, the change would need to be un-archived to keep working - moving folders and syncing specs back out of `openspec/changes/archive/`. If a user asks this skill to archive a change whose `pr` artifact still shows a non-terminal status (not confirmed merged or closed by GitHub), explain this and wait until the PR resolves first. This check is also enforced directly inside `openspec-archive-change`'s own step 2.5, regardless of which skill archiving is invoked through - it is not solely this skill's responsibility to catch.

## Guardrails

- Never push a corrective commit without explicit user confirmation of that specific fix.
- Never merge a pull request. Merging only happens when the user merges it directly in GitHub.
- Never treat `openspec status`'s `tasks: "done"` as proof implementation is complete — it only means `tasks.md` exists, not that every checkbox is checked. Always confirm via `openspec instructions apply`'s `progress.remaining === 0` before opening a PR.
- Never archive a change with a `pr` artifact while its PR is still open/unresolved on GitHub - confirm merged or closed first (see "Only the archive after merge convention is supported" above).
- Never open a second PR for a change without an explicit user instruction to restart after an abandoned PR — one change maps to one PR by default.
- Never classify a comment as "just a bug" to avoid the update/apply cycle when it's actually ambiguous — ask the user which bucket it falls in rather than guessing, since this decision controls whether planning artifacts get revised.
- Never re-process a comment already logged in `pr.md`'s Review Log — always read the log fresh from disk first to find the true watermark.
- Delegate, don't reimplement: use `/opsx:update` for artifact revisions and `/opsx:apply` for implementing new tasks, rather than hand-editing specs/design/tasks or writing code outside the normal apply loop.
- Keep bug-fix records in `pr.md` only, per this project's convention — do not add completed-task entries to tasks.md for pure bug fixes.
- Never treat CI status as a merge gate this skill enforces — report it for visibility on every poll, but decisions about whether a PR is mergeable belong to the target repo's own branch protection and to the user, not to this skill.
