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

**Precondition**: The change must use a schema with a `pr` artifact (e.g. `spec-driven-pr`) and its `tasks` artifact must be `done`. If `tasks` isn't done yet, tell the user to finish `/opsx:apply` first and stop.

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

- If `tasks` is not `done`, stop and tell the user to finish implementation first.
- If `pr` does not exist as an artifact on this change's schema, tell the user this schema doesn't support PR tracking (they'd need `spec-driven-pr` or a schema that includes a `pr` node) and stop.

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
3. For each comment newer than the highest logged ID, triage it (step 4). Do not advance past a comment in the Review Log until its action is actually complete — an unresolved comment stays unlogged so it's re-surfaced on the next poll.
4. Check merge/close status via GitHub MCP tools and **report it to the user directly in conversation** (e.g. "PR #5 is merged"). Do **not** write this back to `pr.md` on its own — see "Why Status isn't updated live" below. The only exception is while a comment-triage cycle already has a real code/artifact change to commit (step 4a/4b) — in that one case, also refresh the Status field as part of that same commit, since a PR is already required for it.

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

## Guardrails

- Never push a corrective commit without explicit user confirmation of that specific fix.
- Never merge a pull request. Merging only happens when the user merges it directly in GitHub.
- Never open a second PR for a change without an explicit user instruction to restart after an abandoned PR — one change maps to one PR by default.
- Never classify a comment as "just a bug" to avoid the update/apply cycle when it's actually ambiguous — ask the user which bucket it falls in rather than guessing, since this decision controls whether planning artifacts get revised.
- Never re-process a comment already logged in `pr.md`'s Review Log — always read the log fresh from disk first to find the true watermark.
- Delegate, don't reimplement: use `/opsx:update` for artifact revisions and `/opsx:apply` for implementing new tasks, rather than hand-editing specs/design/tasks or writing code outside the normal apply loop.
- Keep bug-fix records in `pr.md` only, per this project's convention — do not add completed-task entries to tasks.md for pure bug fixes.
