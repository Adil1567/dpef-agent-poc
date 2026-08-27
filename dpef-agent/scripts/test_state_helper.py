"""Deterministic test cases for the dpef-feature-agent's state logic.

Covers the scenarios from specs/dpef-feature-agent/spec.md that don't
require a live LLM/skill invocation to verify:
  - a correction is only recorded on an explicit confirm-and-push flow
    (never inferred from a comment alone)
  - a deploy is refused before merge
  - a stale "merged" state file is corrected against GitHub's real status
    and the deploy is still refused if the corrected status isn't merged
  - two features' state stays independent
  - illegal state transitions are rejected

These exercise dpef-agent/scripts/state_helper.py directly, since that is
the deterministic, testable core of the skill's gating logic. The
comment-classification and preview-confirmation behavior (steps 1-3 of
the SKILL.md) is judgment-based LLM behavior, not deterministic code, and
is covered by the manual verification checklist instead (tasks 7.2-7.7).

Run: uv run pytest dpef-agent/scripts/test_state_helper.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import state_helper  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_state_dir(tmp_path, monkeypatch):
    """Point state_helper at a throwaway directory for every test."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(state_helper, "STATE_DIR", Path("dpef-agent/state"))
    yield


def test_correction_requires_explicit_record_not_inferred():
    state_helper.create_state("feat-a", "feature/feat-a")
    state_helper.transition("feat-a", "pr_open")
    state_helper.transition("feat-a", "awaiting_review")

    before = state_helper.read_state("feat-a")
    assert before["last_seen_comment_id"] is None

    # Simulate: a comment was merely detected/surfaced (no state helper call
    # for that alone) — status and correction_history must be untouched.
    untouched = state_helper.read_state("feat-a")
    assert untouched["status"] == "awaiting_review"
    assert untouched["correction_history"] == []

    # Now the explicit-confirm path: DPO confirmed, fix pushed.
    state_helper.transition("feat-a", "correcting")
    state_helper.record_correction("feat-a", 555, "fix X", "abc123")
    state_helper.transition("feat-a", "awaiting_review")

    after = state_helper.read_state("feat-a")
    assert len(after["correction_history"]) == 1
    assert after["correction_history"][0]["comment_id"] == 555
    assert after["last_seen_comment_id"] == 555
    assert after["status"] == "awaiting_review"


def test_deploy_precondition_not_merged_before_merge_happens():
    state_helper.create_state("feat-b", "feature/feat-b")
    state_helper.transition("feat-b", "pr_open")
    state_helper.transition("feat-b", "awaiting_review")

    state = state_helper.read_state("feat-b")
    assert state["status"] != "merged"
    # The skill's own instructions (not code) refuse deploy unless status
    # == "merged"; this asserts the precondition they rely on holds.


def test_stale_merged_claim_is_corrected_and_deploy_still_refused():
    state_helper.create_state("feat-c", "feature/feat-c")
    state_helper.transition("feat-c", "pr_open")
    state_helper.transition("feat-c", "awaiting_review")

    # Force a stale claim directly, modeling drift/corruption rather than
    # a legitimate transition.
    state = state_helper.read_state("feat-c")
    state["status"] = "merged"
    state_helper.write_state(state)

    corrected = state_helper.reconcile("feat-c", "awaiting_review")
    assert corrected["status"] == "awaiting_review"
    assert state_helper.read_state("feat-c")["status"] == "awaiting_review"
    assert corrected["status"] != "merged"  # deploy would be refused


def test_understated_status_corrected_to_merged():
    state_helper.create_state("feat-d", "feature/feat-d")
    state_helper.transition("feat-d", "pr_open")
    state_helper.transition("feat-d", "awaiting_review")

    corrected = state_helper.reconcile("feat-d", "merged")
    assert corrected["status"] == "merged"


def test_multiple_features_independent():
    state_helper.create_state("feat-e", "feature/feat-e")
    state_helper.create_state("feat-f", "feature/feat-f")
    state_helper.transition("feat-e", "pr_open")

    e = state_helper.read_state("feat-e")
    f = state_helper.read_state("feat-f")
    assert e["status"] == "pr_open"
    assert f["status"] == "developing"

    in_progress = {s["feature"] for s in state_helper.list_in_progress_features()}
    assert {"feat-e", "feat-f"} <= in_progress


def test_illegal_transition_rejected():
    state_helper.create_state("feat-g", "feature/feat-g")
    with pytest.raises(ValueError):
        state_helper.transition("feat-g", "deployed")


def test_rejected_is_terminal():
    state_helper.create_state("feat-h", "feature/feat-h")
    state_helper.transition("feat-h", "pr_open")
    state_helper.transition("feat-h", "awaiting_review")
    state_helper.transition("feat-h", "rejected")

    with pytest.raises(ValueError):
        state_helper.transition("feat-h", "merged")


def test_create_does_not_overwrite_existing_feature():
    state_helper.create_state("feat-i", "feature/feat-i")
    with pytest.raises(FileExistsError):
        state_helper.create_state("feat-i", "feature/feat-i-again")


def test_set_pr_info_records_pr_number_and_url():
    state_helper.create_state("feat-j", "feature/feat-j")
    updated = state_helper.set_pr_info("feat-j", 42, "https://github.com/org/repo/pull/42")
    assert updated["pr_number"] == 42
    assert updated["pr_url"] == "https://github.com/org/repo/pull/42"
    assert state_helper.read_state("feat-j")["pr_number"] == 42
