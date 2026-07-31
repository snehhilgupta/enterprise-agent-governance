"""Tests for the declarative policy engine."""
import pytest
from governance.policy import Policy, PolicyViolation


@pytest.fixture
def policy():
    return Policy("policies/pipeline_policy.yaml")


def test_allowed_tool(policy):
    d = policy.evaluate_tool("google_search")
    assert d["outcome"] == "allow"


def test_unlisted_tool_requires_approval(policy):
    d = policy.evaluate_tool("delete_database")
    assert d["outcome"] == "require_approval"


def test_allowed_model_under_limit(policy):
    d = policy.evaluate_model("gemini-2.5-flash", input_tokens=500, output_tokens=200)
    assert d["outcome"] == "allow"


def test_model_over_token_limit_escalates(policy):
    d = policy.evaluate_model("gemini-2.5-flash", input_tokens=9000, output_tokens=200)
    assert d["outcome"] == "require_approval"
    assert "limit" in d["reason"].lower()


def test_explicit_require_approval_model(policy):
    d = policy.evaluate_model("gemini-2.5-pro")
    assert d["outcome"] == "require_approval"


def test_enforce_raises_on_block(policy):
    policy.tools["banned_tool"] = {"outcome": "block", "reason": "test block"}
    decision = policy.evaluate_tool("banned_tool")
    with pytest.raises(PolicyViolation):
        policy.enforce(decision)


def test_enforce_passes_through_allow(policy):
    decision = policy.evaluate_tool("google_search")
    result = policy.enforce(decision)
    assert result["outcome"] == "allow"