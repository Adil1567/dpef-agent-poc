#!/usr/bin/env python3
"""Per-feature state file helpers for the dpef-feature-agent skill.

State schema (one YAML file per feature, at dpef-agent/state/<feature>.yaml):
    feature: str
    status: developing | pr_open | awaiting_review | correcting | merged | deployed | rejected
    branch: str
    pr_number: int | null
    pr_url: str | null
    requested_by: str | null
    created_at: ISO8601 str
    updated_at: ISO8601 str
    last_seen_comment_id: int | null
    correction_history: list of
        comment_id: int
        summary: str
        fixed_at: ISO8601 str
        fix_commit: str
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

STATE_DIR = Path("dpef-agent/state")

# Allowed state machine edges. `correcting` returns to `awaiting_review`.
ALLOWED_TRANSITIONS = {
    "developing": {"developing", "pr_open"},
    "pr_open": {"awaiting_review"},
    "awaiting_review": {"correcting", "merged", "rejected"},
    "correcting": {"awaiting_review"},
    "merged": {"deployed"},
    "deployed": set(),
    "rejected": set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _state_path(feature: str) -> Path:
    return STATE_DIR / f"{feature}.yaml"


def read_state(feature: str) -> dict | None:
    path = _state_path(feature)
    if not path.exists():
        return None
    with path.open("r") as f:
        return yaml.safe_load(f)


def write_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    path = _state_path(state["feature"])
    with path.open("w") as f:
        yaml.safe_dump(state, f, sort_keys=False)


def create_state(feature: str, branch: str, requested_by: str | None = None) -> dict:
    """Create a new feature's state file at status `developing`.

    Raises FileExistsError if a state file for this feature already exists —
    callers must not silently overwrite an in-progress feature.
    """
    if _state_path(feature).exists():
        raise FileExistsError(f"state file already exists for feature '{feature}'")
    now = _now()
    state = {
        "feature": feature,
        "status": "developing",
        "branch": branch,
        "pr_number": None,
        "pr_url": None,
        "requested_by": requested_by,
        "created_at": now,
        "updated_at": now,
        "last_seen_comment_id": None,
        "correction_history": [],
    }
    write_state(state)
    return state


def list_features(status: str | None = None) -> list[dict]:
    """List all feature states, optionally filtered by status."""
    if not STATE_DIR.exists():
        return []
    features = []
    for path in sorted(STATE_DIR.glob("*.yaml")):
        with path.open("r") as f:
            state = yaml.safe_load(f)
        if state is None:
            continue
        if status is None or state.get("status") == status:
            features.append(state)
    return features


NON_TERMINAL_STATUSES = {"developing", "pr_open", "awaiting_review", "correcting", "merged"}


def list_in_progress_features() -> list[dict]:
    """List features whose status is not a terminal state (deployed/rejected)."""
    return [f for f in list_features() if f.get("status") in NON_TERMINAL_STATUSES]


def transition(feature: str, new_status: str) -> dict:
    """Transition a feature to a new status, enforcing the state machine.

    Raises ValueError if the transition is not an allowed edge.
    """
    state = read_state(feature)
    if state is None:
        raise FileNotFoundError(f"no state file for feature '{feature}'")
    current = state["status"]
    if new_status == current:
        return state
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise ValueError(
            f"illegal transition for '{feature}': {current} -> {new_status} "
            f"(allowed from {current}: {sorted(allowed) or 'none (terminal)'})"
        )
    state["status"] = new_status
    write_state(state)
    return state


def reconcile(feature: str, github_status: str) -> dict:
    """Reconcile a feature's cached status against GitHub's real status.

    If they disagree, overwrite and persist the cached status with the
    GitHub-reported value, then return the corrected state. This does not
    itself enforce the state machine edges (GitHub's state is treated as
    ground truth, not a proposed transition), since the whole point is to
    correct a state file that may have drifted or been wrong.
    """
    state = read_state(feature)
    if state is None:
        raise FileNotFoundError(f"no state file for feature '{feature}'")
    if state["status"] != github_status:
        state["status"] = github_status
        write_state(state)
    return state


def record_correction(feature: str, comment_id: int, summary: str, fix_commit: str) -> dict:
    """Append a correction to history and update last_seen_comment_id."""
    state = read_state(feature)
    if state is None:
        raise FileNotFoundError(f"no state file for feature '{feature}'")
    state.setdefault("correction_history", []).append(
        {
            "comment_id": comment_id,
            "summary": summary,
            "fixed_at": _now(),
            "fix_commit": fix_commit,
        }
    )
    state["last_seen_comment_id"] = comment_id
    write_state(state)
    return state


def set_pr_info(feature: str, pr_number: int, pr_url: str) -> dict:
    """Record the real PR number/URL once a PR has actually been opened."""
    state = read_state(feature)
    if state is None:
        raise FileNotFoundError(f"no state file for feature '{feature}'")
    state["pr_number"] = pr_number
    state["pr_url"] = pr_url
    write_state(state)
    return state


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("read", help="Read a feature's state as JSON")
    p.add_argument("feature")

    p = sub.add_parser("create", help="Create a new feature's state file")
    p.add_argument("feature")
    p.add_argument("branch")
    p.add_argument("--requested-by", default=None)

    p = sub.add_parser("list", help="List features, optionally filtered by status")
    p.add_argument("--status", default=None)

    p = sub.add_parser("list-in-progress", help="List non-terminal features")

    p = sub.add_parser("transition", help="Transition a feature to a new status")
    p.add_argument("feature")
    p.add_argument("status")

    p = sub.add_parser("reconcile", help="Reconcile cached status against GitHub's real status")
    p.add_argument("feature")
    p.add_argument("github_status")

    p = sub.add_parser("record-correction", help="Record a pushed correction")
    p.add_argument("feature")
    p.add_argument("comment_id", type=int)
    p.add_argument("summary")
    p.add_argument("fix_commit")

    p = sub.add_parser("set-pr-info", help="Record the PR number/URL once a PR is opened")
    p.add_argument("feature")
    p.add_argument("pr_number", type=int)
    p.add_argument("pr_url")

    args = parser.parse_args()

    try:
        if args.command == "read":
            result = read_state(args.feature)
            if result is None:
                print(f"no state file for feature '{args.feature}'", file=sys.stderr)
                sys.exit(1)
        elif args.command == "create":
            result = create_state(args.feature, args.branch, args.requested_by)
        elif args.command == "list":
            result = list_features(args.status)
        elif args.command == "list-in-progress":
            result = list_in_progress_features()
        elif args.command == "transition":
            result = transition(args.feature, args.status)
        elif args.command == "reconcile":
            result = reconcile(args.feature, args.github_status)
        elif args.command == "record-correction":
            result = record_correction(args.feature, args.comment_id, args.summary, args.fix_commit)
        elif args.command == "set-pr-info":
            result = set_pr_info(args.feature, args.pr_number, args.pr_url)
        print(json.dumps(result, indent=2))
    except (FileNotFoundError, FileExistsError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _main()
