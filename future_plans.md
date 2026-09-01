# Future Plans

## Scripted `pr.md` helper (deferred from the archive-status-check fix, 2026-09-01)

### Problem

`pr.md`'s read/write operations are currently done by prose-guided LLM parsing of a
markdown file, across every step of `openspec-pr-lifecycle` and `openspec-archive-change`:

- Reading the PR number (`- **PR Number:** <n>` line)
- Finding the highest logged comment ID in the Review Log (to know what's new on the next poll)
- Appending a new Review Log entry in the exact expected format
- Flipping the Status field between `open (as of creation...)`, `merged`, `closed`

None of this is scripted or validated. Every operation relies on Claude correctly
locating and parsing specific markdown structure each time, with no defined fallback
if the file drifts from its expected shape (a stray edit, a renamed field, inconsistent
formatting from an earlier session). This is the same class of risk that was flagged
and partially fixed for the "which PR to archive-check" step (see step 2.5 in
`openspec-archive-change/SKILL.md`, which now at least specifies the exact field-match
pattern and what to do if it's missing) - but that fix only covers one read, not the
whole file's lifecycle.

### Proposed fix

Build a small helper script - `pr_md_helper.py` or similar - mirroring the pattern
already proven in `dpef-agent/scripts/state_helper.py`, which `dpef-build-feature`
uses for all its state mutations instead of hand-parsing YAML.

Candidate subcommands:

- `get-pr-number <path-to-pr.md>` - returns the PR number, or a clear error if the field is missing/malformed
- `get-last-comment-id <path-to-pr.md>` - returns the highest comment ID already logged, or none if the Review Log is empty
- `append-review-log-entry <path-to-pr.md> --comment-id <id> --from <author> --comment <text> --classification <bug|spec-gap|informational> --action <text> --artifacts-touched <list|none>` - appends a correctly-formatted entry
- `set-status <path-to-pr.md> <merged|closed|open>` - flips the Status field, replacing whatever placeholder/value was there
- `get-status <path-to-pr.md>` - returns the current stored Status field value (distinct from asking GitHub - this reads only what's on disk)

### What changes in the skills

`openspec-pr-lifecycle` and `openspec-archive-change` would call this script for every
mechanical `pr.md` read/write, instead of instructing Claude to parse/edit the markdown
directly. The skills' prose would stay focused on judgment calls (bug vs. spec-gap
classification, what to tell the user, when to suggest archiving) - the same split
`dpef-build-feature` already has between its own judgment-heavy SKILL.md and the
deterministic `state_helper.py`.

### Why this was deferred rather than done immediately (2026-09-01)

This is a bigger, more structural change than the smaller instruction-tightening fixes
that shipped alongside this plan (moving the open-PR archive guardrail into
`openspec-archive-change` itself, and specifying step 2.5's exact field-match pattern).
It touches every step of both skills' `pr.md` interactions and deserves its own
planning pass (a proper `/opsx:propose` cycle, most likely) rather than being bolted
onto a guardrail fix. Revisit this once the current guardrail fixes have been used for
a while and any remaining `pr.md`-parsing fragility becomes concrete rather than
theoretical.
