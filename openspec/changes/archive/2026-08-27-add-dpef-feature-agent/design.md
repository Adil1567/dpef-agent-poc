## Context

See proposal.md - Why. This design covers the state machine, state file schema, and the human-gating mechanics that make the agent safe to run against a real DPEF repo. The target repo is a real GitOps-managed data product repo — production data flows through it, so every irreversible action (merge, deploy) must trace to an explicit human decision recorded outside the agent's own state.

## Goals / Non-Goals

**Goals:**
- Make every irreversible action (PR merge, production deploy) require an explicit, separate DPO instruction — never inferred from a prior approval or from silence.
- Make GitHub the source of truth for PR/merge state; treat the agent's own state file as a cache that can go stale and must be reconciled, never trusted blindly for anything gating a deploy.
- Support several features in flight per DPO without cross-talk between them.

**Non-Goals:**
- Multi-DPO / multi-tenant support (one DPO's features are not shared or visible to another DPO in this PoC).
- Automatic conflict resolution if a correction's diff conflicts with upstream changes on the branch — surfaced to the DPO as a blocker, not silently resolved.
- CI pipeline execution itself — the agent reads pipeline/check status via the GitHub API but does not run or configure the pipeline.

## Decisions

### State machine

```
developing → pr_open → awaiting_review ⇄ correcting → merged → deployed
                              │
                              └──────────────→ rejected
```

- `developing`: code generated on a local working branch, preview shown to DPO, no PR yet.
- `pr_open`: DPO confirmed the preview; PR opened.
- `awaiting_review`: PR open, no unactioned DPO comment pending.
- `correcting`: DPO confirmed a proposed fix; agent is pushing a corrective commit. Returns to `awaiting_review` once pushed.
- `merged`: GitHub shows the PR merged (detected by poll, or corrected via reconciliation).
- `deployed`: DPO gave an explicit deploy instruction and the deploy action completed.
- `rejected`: DPO closed the PR without merging. Terminal — branch is left in place, no rollback action (nothing was ever merged to main, so there is nothing to undo).

**Why gate PR creation behind a preview, not just the PR itself:** Opening a PR is cheap to *create* but not cheap to *ignore* — a DPO refining a request through several chat turns would otherwise generate a new PR (or force-push confusion) per iteration. Showing a plan + diff in chat first, and only opening the PR on explicit confirmation, keeps early iteration off GitHub entirely and means every PR that does appear represents a DPO-approved starting point.

**Why corrections require explicit confirmation, not auto-push-on-comment:** A PR comment might be a question, a partial thought, or one of several comments left while the DPO is still drafting feedback. Auto-pushing on comment detection risks committing based on a misread or incomplete request. Requiring "yes, make that change" as a separate turn mirrors the deploy gate's logic: read-only polling is safe to automate, anything that writes to the branch is not.

### State file: one YAML file per feature

```
dpef-agent/
└── state/
    ├── add-customer-ltv-column.yaml
    ├── fix-churn-flag-logic.yaml
    └── add-region-dimension.yaml
```

```yaml
feature: add-customer-ltv-column
status: awaiting_review
branch: feature/add-customer-ltv-column
pr_number: 47
pr_url: https://github.com/org/dpef-repo/pull/47
requested_by: dpo@company.com
created_at: 2026-08-25T14:30:00Z
updated_at: 2026-08-25T15:10:00Z
last_seen_comment_id: 998877
correction_history:
  - comment_id: 998877
    summary: "DPO asked to exclude trial accounts from LTV calc"
    fixed_at: 2026-08-25T15:05:00Z
    fix_commit: a1b2c3d
```

**Why one file per feature instead of one file with a list:** Independent features should be independently readable, diffable, and lockable. A single shared file risks a write race if a future version of this agent runs multiple features concurrently, and makes "list features by status" (needed for the disambiguation flow) a simple directory scan instead of a parse-and-filter.

**Why `last_seen_comment_id`:** It is what makes polling idempotent. Without it, every poll would re-surface every historical comment; with it, the agent can distinguish "new since I last looked" from "already surfaced, DPO hasn't responded yet" and avoid re-prompting on each invocation.

### Reconciliation over refusal-only

When the state file and GitHub's actual PR/merge status disagree, the agent overwrites the stale field with GitHub's value and persists the correction, then re-evaluates the requested action against the corrected state — rather than just refusing and leaving the mismatch for a human to fix by hand. GitHub is the durable, independently-auditable record; the state file is a cache the agent itself writes and can therefore get out of sync with (e.g. a deploy attempted from a stale session, or another process merging the PR outside the agent's awareness). Self-healing keeps the state file trustworthy for the *next* read without a manual repair step, while the gating logic (deploy only if `merged` and explicitly instructed) still applies to the corrected value, so a stale "looks merged" claim can never itself unlock a deploy.

### Agent never merges

Recommendation carried over from the working plan: the DPO always clicks merge in GitHub directly. If the agent merged on the DPO's behalf, GitHub's approval trail would stop meaning "a human looked at this," which matters for anything touching production data. This is enforced doubly: by convention (the skill has no merge action) and by GitHub branch protection on the target repo (required approving review before merge is possible at all).

## Risks / Trade-offs

- **Comment misclassification** (agent treats a question as a correction request, or vice versa) → Mitigation: the agent always proposes the fix in chat and waits for explicit confirmation before committing; a misclassified question simply gets an unwanted proposal, not an unwanted commit.
- **Stale local working branch during `developing`** if the DPO takes a long time to confirm a preview and the target repo's base branch moves → Mitigation: re-check for base-branch drift before opening the PR at confirmation time; surface a rebase-needed warning rather than silently opening a PR against a stale base.
- **State file and GitHub diverge silently between polls** (e.g., merged outside the agent's awareness) → Mitigation: reconciliation logic above; every deploy attempt forces a fresh GitHub read regardless of cached status age.
