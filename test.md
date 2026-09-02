# PR-lifecycle extension — demo test script

Covers every use case in the `spec-driven-pr` schema + `openspec-pr-lifecycle` skill +
generic `apply`/`archive` edits. Run from the repo root.

Prereq: `openspec/schemas/spec-driven-pr/`, `.claude/skills/openspec-pr-lifecycle/`,
`.claude/skills/openspec-apply-change/`, `.claude/skills/openspec-archive-change/`,
`.claude/commands/opsx/apply.md`, `.claude/commands/opsx/archive.md` are already copied
into this repo.

---

## 0. Prerequisites check

```bash
openspec --version
openspec schemas --json | grep -A2 '"spec-driven-pr"'
grep -c "openspec-pr-lifecycle" .claude/skills/openspec-archive-change/SKILL.md   # expect 0 — must NOT be hardcoded
grep -c '`pr` artifact' .claude/skills/openspec-archive-change/SKILL.md          # expect 0 — must NOT be hardcoded
```

---

## 1. Create a change and confirm the schema wires up `pr` correctly

```bash
openspec new change "test-feature" --schema spec-driven-pr
openspec status --change test-feature --json
```

**Check:** `artifacts` includes `pr` with `requires: ["tasks"]`, status `blocked`.

---

## 2. Populate planning artifacts

(Normally `/opsx:propose` does this — this is the minimal manual version for testing.)

```bash
mkdir -p openspec/changes/test-feature/specs/test-capability

cat > openspec/changes/test-feature/proposal.md <<'EOF'
## Why
Test.
## What Changes
- test
## Capabilities
- **New Capabilities**: test-capability
## Impact
None.
EOF

cat > openspec/changes/test-feature/specs/test-capability/spec.md <<'EOF'
## Purpose
Throwaway capability for testing.

## ADDED Requirements

### Requirement: Dummy
The system SHALL do nothing observable.

#### Scenario: No-op
- **WHEN** nothing happens
- **THEN** nothing happens
EOF

cat > openspec/changes/test-feature/design.md <<'EOF'
## Context
Test.
EOF

cat > openspec/changes/test-feature/tasks.md <<'EOF'
## 1. Verify
- [ ] 1.1 Do a trivial change
EOF

openspec status --change test-feature --json
```

**Check:** `proposal`, `specs`, `design`, `tasks` all `done`; `pr` now `ready`.

---

## 3. Apply's generic PR discovery

*(apply completion suggests the next artifact without hardcoding its id)*

```bash
openspec instructions apply --change test-feature --json
```

Then, in a Claude Code session:

```
/opsx:apply test-feature
```

Check off the one task. Confirm apply's completion message surfaces the `pr` artifact's
instruction (not a hardcoded skill name), then verify directly:

```bash
openspec instructions pr --change test-feature --json
```

**Check:** `instruction` field mentions `openspec-pr-lifecycle` (comes from the schema, not from apply itself).

---

## 4. Opening a PR

*(openspec-pr-lifecycle step 2 — requires a real branch pushed to a real GitHub repo)*

In Claude Code:

```
Invoke openspec-pr-lifecycle to open a PR for test-feature. Branch <your-branch> is pushed, base is <default-branch>, repo is <owner/repo>.
```

**Check:** `openspec/changes/test-feature/pr.md` created with PR URL/Number/Status/Branch filled in, Review Log empty.

---

## 5. Polling — comments + CI status

*(openspec-pr-lifecycle step 3)*

```
Check on the PR for test-feature.
```

**Check:** response reports both comment triage AND a CI status line
(e.g. `CI: all checks passing` / `CI: no checks configured on this PR` / failing check names).

---

## 6. Comment triage — bug path

*(step 4a — leave a PR comment describing an implementation bug, then poll again)*

```
Check on the PR for test-feature.
```

**Confirm:** user is asked before any commit; on confirmation, code is fixed and pushed;
`pr.md`'s Review Log gets an entry; `tasks.md`/specs are untouched.

---

## 7. Comment triage — spec-gap path

*(step 4b — leave a PR comment describing a new requirement not in the spec, then poll again)*

**Confirm:** it's surfaced as a spec gap (not silently fixed), and on your confirmation it
invokes `/opsx:update` then `/opsx:apply` before pushing.

---

## 8. Archive's generic reconciliation — not-yet-created case

```bash
openspec new change "test-no-pr" --schema spec-driven-pr
```

Do **not** create `pr.md` for this change. Then:

```
/opsx:archive test-no-pr
```

**Confirm:** step 2.5 is skipped silently (no `pr.md` exists yet), archive proceeds normally.

---

## 9. Archive's hard stop

*(unresolved PR blocks archive)*

With `test-feature`'s PR still open on GitHub:

```
/opsx:archive test-feature
```

**Confirm:** archive refuses, reports the PR is still open, and does not move the change directory.

```bash
# Verify nothing moved:
ls openspec/changes/test-feature   # should still exist, unarchived
```

---

## 10. Archive succeeding after merge

*(full end-to-end)*

Merge the PR on GitHub, then:

```
/opsx:archive test-feature
```

**Confirm:**
- Step 2.5 delegates to `openspec-pr-lifecycle`, which confirms merged and updates `pr.md`'s Status field.
- Archive proceeds, moves the change to `openspec/changes/archive/`.
- Step 5.5 commits/pushes the archive move to a new branch and **asks before opening its own PR** — confirm it stops and asks, doesn't auto-open.

```bash
ls openspec/changes/archive/ | grep test-feature
cat openspec/changes/archive/*test-feature/pr.md | grep Status   # should say merged, not the "as of creation" placeholder
```

---

## 11. Recovery patch

*(`openspec update` fragility)*

```bash
git stash   # if you have local edits
openspec update --force   # will overwrite apply/archive stock files
git diff --stat .claude/skills/openspec-apply-change/SKILL.md .claude/skills/openspec-archive-change/SKILL.md
```

If that shows the generic edits reverted to stock:

```bash
git apply openspec/patches/pr-lifecycle-workflow-edits.patch
git apply --check openspec/patches/pr-lifecycle-workflow-edits.patch  # sanity check, silent = already applied cleanly
```

---

## 12. Cleanup

```bash
rm -rf openspec/changes/test-feature openspec/changes/test-no-pr openspec/changes/archive/*test-feature
```

---

This covers every behavior built for this extension: generic discovery in apply/archive,
PR opening, comment-poll with CI-status reporting, both triage branches, the archive
hard-stop guardrail, the post-merge success path, and the `openspec update` recovery patch.
