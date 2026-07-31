"""
policy.py — declarative policy enforcement.

Loads a YAML policy file and evaluates tool/model calls against it.
Outcomes: allow | block | require_approval

Design: policy lives outside the model. The agent never sees this
check — it either proceeds, is refused, or is paused for a human.
Unlisted actions default to require_approval, not allow — an
unknown action is untrusted by default, not implicitly safe.
"""
import yaml


class PolicyViolation(Exception):
    """Raised when an action is blocked outright."""
    def __init__(self, action_type, action_name, reason):
        self.action_type = action_name
        self.reason = reason
        super().__init__(f"BLOCKED: {action_type} '{action_name}' — {reason}")


class Policy:
    def __init__(self, path):
        with open(path) as f:
            self._raw = yaml.safe_load(f)
        self.tools = self._raw.get("tools", {})
        self.models = self._raw.get("models", {})
        self.limits = self._raw.get("limits", {})
        self.default_outcome = self._raw.get("defaults", {}).get(
            "outcome", "require_approval"
        )

    def evaluate_tool(self, tool_name: str) -> dict:
        """Check a tool call against policy. Returns decision dict."""
        rule = self.tools.get(tool_name)
        if rule is None:
            return {
                "action_type": "tool", "action_name": tool_name,
                "outcome": self.default_outcome,
                "reason": "No explicit rule; unlisted actions require approval",
                "tier": None,
            }
        return {
            "action_type": "tool", "action_name": tool_name,
            "outcome": rule["outcome"], "reason": rule.get("reason", ""),
            "tier": rule.get("tier"),
        }

    def evaluate_model(self, model_name: str, input_tokens=None,
                        output_tokens=None) -> dict:
        """Check a model call against policy, including token limits."""
        rule = self.models.get(model_name)
        if rule is None:
            decision = {
                "action_type": "model", "action_name": model_name,
                "outcome": self.default_outcome,
                "reason": "No explicit rule; unlisted actions require approval",
                "tier": None,
            }
        else:
            decision = {
                "action_type": "model", "action_name": model_name,
                "outcome": rule["outcome"], "reason": rule.get("reason", ""),
                "tier": rule.get("tier"),
            }

        # Token limits can escalate an otherwise-allowed call
        max_in = self.limits.get("max_input_tokens_per_call")
        max_out = self.limits.get("max_output_tokens_per_call")
        over_limit = (
            (max_in is not None and input_tokens is not None and input_tokens > max_in)
            or (max_out is not None and output_tokens is not None and output_tokens > max_out)
        )
        if over_limit and decision["outcome"] == "allow":
            decision["outcome"] = self.limits.get("over_limit_outcome", "require_approval")
            decision["reason"] = "Token limit exceeded for this call"

        return decision

    def enforce(self, decision: dict):
        """Raise if blocked. Return decision unchanged otherwise.

        require_approval is NOT enforced here — that's Phase 4's job.
        This just raises on outright blocks; callers check 'outcome'
        for require_approval themselves.
        """
        if decision["outcome"] == "block":
            raise PolicyViolation(
                decision["action_type"], decision["action_name"], decision["reason"]
            )
        return decision