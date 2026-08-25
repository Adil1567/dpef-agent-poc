#!/usr/bin/env python3
"""Required CI check for dpef-feature-agent PRs.

Runs independently of the agent, on GitHub's own infrastructure, on every
push to a PR branch. Re-fetches this PR's real approval/merge status from
the GitHub API and compares it against whatever
dpef-agent/state/<feature>.yaml claims in this branch. Fails (non-zero
exit -> red X on the PR) if the committed state file's claim about this
PR's status disagrees with what GitHub itself reports.

This exists so that "the agent's state file said X" can never be trusted
on its own — this check is what makes that claim independently verifiable
before a human relies on it (e.g. before merging).

Scope: this check only guards the MERGE step (via required-status-check
branch protection). It does not guard the DEPLOY step — deploy has its
own separate, synchronous guard: the dpef-build-feature skill re-fetches
and reconciles the real PR status immediately before deploying, every
time, regardless of whether this CI check ever ran. The two guards are
independent and deliberately redundant: one blocks an unmerged PR from
being merged, the other blocks an unmerged feature from being deployed.
"""

import glob
import os
import sys

import requests
import yaml

STATE_DIR = "dpef-agent/state"

# Feature-file statuses that imply "this PR has already been approved
# and merged" per the state machine in design.md. If a state file claims
# one of these while GitHub disagrees, that is exactly the drift this
# check exists to catch.
STATUSES_CLAIMING_MERGED = {"merged", "deployed"}


def fail(message: str) -> None:
    print(f"::error::{message}")
    sys.exit(1)


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    pr_number = os.environ.get("PR_NUMBER")
    repo_full_name = os.environ.get("REPO_FULL_NAME")

    if not (token and pr_number and repo_full_name):
        fail("missing required environment: GITHUB_TOKEN, PR_NUMBER, REPO_FULL_NAME")

    state_files = sorted(glob.glob(f"{STATE_DIR}/*.yaml"))
    matching = []
    for path in state_files:
        with open(path) as f:
            state = yaml.safe_load(f)
        if state and str(state.get("pr_number")) == str(pr_number):
            matching.append((path, state))

    if not matching:
        # Not every PR in this repo is necessarily a dpef-agent PR. If no
        # state file claims this PR number, there is nothing to verify.
        print(f"No dpef-agent state file references PR #{pr_number}. Nothing to verify.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    resp = requests.get(
        f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}",
        headers=headers,
        timeout=30,
    )
    if resp.status_code != 200:
        fail(f"could not fetch PR #{pr_number} from GitHub API: {resp.status_code} {resp.text}")

    pr = resp.json()
    actually_merged = bool(pr.get("merged"))
    actually_open = pr.get("state") == "open"

    problems = []
    for path, state in matching:
        claimed_status = state.get("status")
        feature = state.get("feature", path)

        if claimed_status in STATUSES_CLAIMING_MERGED and not actually_merged:
            problems.append(
                f"{feature}: state file claims '{claimed_status}' but GitHub reports "
                f"this PR is NOT merged (state={pr.get('state')}, merged={actually_merged})"
            )

        if claimed_status not in STATUSES_CLAIMING_MERGED and actually_merged:
            problems.append(
                f"{feature}: GitHub reports this PR IS merged, but the state file claims "
                f"'{claimed_status}' (expected 'merged' or 'deployed')"
            )

        if claimed_status == "rejected" and actually_open:
            problems.append(
                f"{feature}: state file claims 'rejected' (closed without merge) but "
                f"GitHub reports this PR is still open"
            )

    if problems:
        for p in problems:
            print(f"::error::{p}")
        fail(f"{len(problems)} state file claim(s) disagree with GitHub's actual PR status")

    print(f"OK: {len(matching)} state file(s) referencing PR #{pr_number} match GitHub's actual status.")


if __name__ == "__main__":
    main()
