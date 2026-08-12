"""Tests for the token budget circuit breaker."""
import pytest
from governance.budget import BudgetTracker, BudgetExceeded


def test_records_usage_under_cap():
    b = BudgetTracker(max_total_tokens=1000)
    b.record(input_tokens=300, output_tokens=200)
    assert b.spent_tokens == 500
    assert b.calls == 1
    assert b.remaining() == 500


def test_accumulates_across_multiple_calls():
    b = BudgetTracker(max_total_tokens=1000)
    b.record(input_tokens=300, output_tokens=200)
    b.record(input_tokens=100, output_tokens=100)
    assert b.spent_tokens == 700
    assert b.calls == 2


def test_raises_when_cap_exceeded():
    b = BudgetTracker(max_total_tokens=500)
    b.record(input_tokens=300, output_tokens=100)
    with pytest.raises(BudgetExceeded):
        b.record(input_tokens=200, output_tokens=50)


def test_exact_cap_does_not_raise():
    b = BudgetTracker(max_total_tokens=500)
    b.record(input_tokens=300, output_tokens=200)
    assert b.spent_tokens == 500


def test_runaway_loop_halts():
    """Simulates many small allowed calls that individually pass
    policy but collectively blow the budget — the scenario this
    breaker exists for."""
    b = BudgetTracker(max_total_tokens=1000)
    with pytest.raises(BudgetExceeded):
        for _ in range(50):
            b.record(input_tokens=50, output_tokens=0)


def test_status_reports_correctly():
    b = BudgetTracker(max_total_tokens=1000)
    b.record(input_tokens=250, output_tokens=250)
    s = b.status()
    assert s["spent_tokens"] == 500
    assert s["remaining"] == 500
    assert s["pct_used"] == 50.0

def test_budget_from_policy_yaml():
    """Proves run_budget.max_total_tokens in the policy file actually
    drives the breaker — not just a number we typed into other tests."""
    import yaml
    with open("policies/pipeline_policy.yaml") as f:
        config = yaml.safe_load(f)

    limit = config["run_budget"]["max_total_tokens"]
    assert limit == 20000

    b = BudgetTracker(max_total_tokens=limit)
    b.record(input_tokens=15000, output_tokens=4000)
    assert b.spent_tokens == 19000
    with pytest.raises(BudgetExceeded):
        b.record(input_tokens=2000, output_tokens=0)