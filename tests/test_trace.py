"""Tests for the tamper-evident trace chain."""
import json
import os
import tempfile

from governance.trace import RunTrace, verify_chain


def _sample_trace(tmpdir):
    t = RunTrace(run_id="test-run", trace_dir=tmpdir)
    agent = t.emit("invoke_agent", {"gen_ai.agent.name": "orchestrator"})
    t.emit("execute_tool", {"gen_ai.tool.name": "search"},
           parent_span_id=agent, duration_ms=100)
    t.emit("chat", {"gen_ai.request.model": "gemini-2.5-flash",
                    "gen_ai.usage.input_tokens": 1200},
           parent_span_id=agent, duration_ms=500)
    return t


def test_valid_chain_verifies():
    with tempfile.TemporaryDirectory() as d:
        t = _sample_trace(d)
        assert verify_chain(t.path) == {"valid": True, "events": 3}


def test_altered_content_is_detected():
    with tempfile.TemporaryDirectory() as d:
        t = _sample_trace(d)
        with open(t.path) as f:
            lines = f.readlines()
        record = json.loads(lines[2])
        record["gen_ai.usage.input_tokens"] = 99
        lines[2] = json.dumps(record) + "\n"
        with open(t.path, "w") as f:
            f.writelines(lines)

        result = verify_chain(t.path)
        assert result["valid"] is False
        assert result["broken_at_line"] == 3


def test_deleted_line_is_detected():
    with tempfile.TemporaryDirectory() as d:
        t = _sample_trace(d)
        with open(t.path) as f:
            lines = f.readlines()
        del lines[1]
        with open(t.path, "w") as f:
            f.writelines(lines)

        assert verify_chain(t.path)["valid"] is False


def test_content_not_captured_by_default():
    with tempfile.TemporaryDirectory() as d:
        t = RunTrace(run_id="no-content", trace_dir=d)
        t.emit("chat", {"gen_ai.request.model": "x"}, content="secret prompt")
        with open(t.path) as f:
            assert "secret prompt" not in f.read()


def test_content_captured_when_enabled():
    with tempfile.TemporaryDirectory() as d:
        t = RunTrace(run_id="with-content", trace_dir=d, capture_content=True)
        t.emit("chat", {"gen_ai.request.model": "x"}, content="visible prompt")
        with open(t.path) as f:
            assert "visible prompt" in f.read()