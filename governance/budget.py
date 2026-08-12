"""
budget.py — hard spend/token cap per run.

Tracks cumulative token usage across a run. Once a configured ceiling
is crossed, raises BudgetExceeded — the run halts immediately rather
than continuing to accumulate cost. This is a circuit breaker, not a
per-call check (that's policy.py's job); it answers "what stops a
runaway loop?" rather than "was this one call allowed?"
"""


class BudgetExceeded(Exception):
    def __init__(self, spent, limit, unit="tokens"):
        self.spent = spent
        self.limit = limit
        super().__init__(
            f"Budget exceeded: {spent} {unit} spent, limit was {limit} {unit}"
        )


class BudgetTracker:
    def __init__(self, max_total_tokens: int):
        self.max_total_tokens = max_total_tokens
        self.spent_tokens = 0
        self.calls = 0

    def record(self, input_tokens: int = 0, output_tokens: int = 0):
        """Record a call's usage. Raises BudgetExceeded if over cap."""
        self.spent_tokens += input_tokens + output_tokens
        self.calls += 1
        if self.spent_tokens > self.max_total_tokens:
            raise BudgetExceeded(self.spent_tokens, self.max_total_tokens)

    def remaining(self) -> int:
        return max(0, self.max_total_tokens - self.spent_tokens)

    def status(self) -> dict:
        return {
            "spent_tokens": self.spent_tokens,
            "max_total_tokens": self.max_total_tokens,
            "remaining": self.remaining(),
            "calls": self.calls,
            "pct_used": round(100 * self.spent_tokens / self.max_total_tokens, 1),
        }