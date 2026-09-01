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
