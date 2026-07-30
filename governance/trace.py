"""
trace.py — tamper-evident run traces.

Emits one JSONL line per agent event, using OpenTelemetry GenAI
semantic convention attribute names (pre-stable, pinned to v1.42.0).

Each line carries prev_hash + hash, forming a chain: altering any
line invalidates every line after it. Tamper-EVIDENT, not tamper-proof
(see README limitations).

Content capture (prompts/completions) is OFF by default; enable with
capture_content=True for debugging only.
"""
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone

GENESIS_HASH = "0" * 64


def _hash_line(payload: dict, prev_hash: str) -> str:
    """SHA-256 over canonical payload + previous hash."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((canonical + prev_hash).encode("utf-8")).hexdigest()


class RunTrace:
    """One trace per pipeline run. Append-only."""

    def __init__(self, run_id=None, trace_dir="traces", capture_content=False):
        self.run_id = run_id or f"run-{uuid.uuid4().hex[:12]}"
        self.capture_content = capture_content
        self.path = os.path.join(trace_dir, f"{self.run_id}.jsonl")
        self._prev_hash = GENESIS_HASH
        self._seq = 0
        os.makedirs(trace_dir, exist_ok=True)

    def emit(self, operation: str, attributes: dict, content=None,
             parent_span_id=None, duration_ms=None):
        """Append one event. operation: invoke_agent|execute_tool|chat|...

        parent_span_id links this event to the one that caused it,
        turning the flat log into a causal tree.
        """
        span_id = uuid.uuid4().hex[:16]
        payload = {
            "run_id": self.run_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "seq": self._seq,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "gen_ai.operation.name": operation,
            **attributes,
        }
        if content is not None and self.capture_content:
            payload["content"] = content

        line_hash = _hash_line(payload, self._prev_hash)
        record = {**payload, "prev_hash": self._prev_hash, "hash": line_hash}

        with open(self.path, "a") as f:
            f.write(json.dumps(record) + "\n")

        self._prev_hash = line_hash
        self._seq += 1
        return span_id


def verify_chain(path: str) -> dict:
    """Walk a trace file, recompute hashes. Returns first break, if any."""
    prev_hash = GENESIS_HASH
    count = 0

    with open(path) as f:
        for lineno, line in enumerate(f, start=1):
            record = json.loads(line)
            stored_hash = record.pop("hash")
            stored_prev = record.pop("prev_hash")

            if stored_prev != prev_hash:
                return {"valid": False, "broken_at_line": lineno,
                        "reason": "prev_hash mismatch"}

            if _hash_line(record, prev_hash) != stored_hash:
                return {"valid": False, "broken_at_line": lineno,
                        "reason": "content altered"}

            prev_hash = stored_hash
            count += 1

    return {"valid": True, "events": count}