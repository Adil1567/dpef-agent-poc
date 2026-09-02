# Contributing

This repo uses [OpenSpec](openspec/) to plan changes before writing code, and (via the `spec-driven-pr` schema) to track each change's PR through review.

## Lifecycle

1. `openspec new change "<name>"` - scaffolds a new change under `openspec/changes/<name>/`
2. `/opsx:propose` or manual writing - fills in `proposal.md`, `specs/`, `tasks.md`
3. `/opsx:apply` - implements the tasks, checks them off
4. The `openspec-pr-lifecycle` skill opens a PR once tasks are done, tracked in `pr.md`
5. Review happens on the PR - comments get triaged as either code fixes or real spec/design gaps
6. Once merged, `/opsx:archive` moves the change to `openspec/changes/archive/` and syncs its spec into `openspec/specs/`
7. The archive itself lands via its own small follow-up PR

## Maintenance note: `openspec update`

Steps 3 and 6 above (`/opsx:apply`, `/opsx:archive`) rely on edits made directly to OpenSpec's own stock workflow files:
`.claude/skills/openspec-apply-change/SKILL.md`, `.claude/skills/openspec-archive-change/SKILL.md`,
`.claude/commands/opsx/apply.md`, `.claude/commands/opsx/archive.md`. These edits teach apply to discover
and surface the `pr` artifact generically, and teach archive to reconcile a PR's status (via the
`openspec-pr-lifecycle` skill) before archiving - a hard safety check, not just a suggestion.

`openspec update` regenerates these same files from OpenSpec's own bundled templates and **overwrites them
unconditionally** - there is no merge, and no detection of local edits. If you ever run `openspec update`
(or `--force`) in this repo:

1. Run `git diff` on the four files above afterward.
2. If they've reverted to stock, reapply `openspec/patches/pr-lifecycle-workflow-edits.patch`
   (`git apply openspec/patches/pr-lifecycle-workflow-edits.patch` from the repo root, then resolve
   any conflicts by hand if the stock files changed shape since this patch was made).
3. Re-run the verification steps in that patch's own header comment before trusting the result.

This does not apply to `openspec/schemas/spec-driven-pr/` or `.claude/skills/openspec-pr-lifecycle/` -
those are custom additions outside OpenSpec's managed workflow set, so `openspec update` never touches them.
