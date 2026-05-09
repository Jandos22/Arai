"""Evidence logger tests — schema, redaction, append-only."""
from __future__ import annotations

import json

import pytest

from orchestrator.evidence import EvidenceLogger, _redact


def test_redacts_sbc_team_token():
    redacted = _redact("Authorization: Bearer sbc_team_18bABCDEF1234567xyz")
    assert "sbc_team_18b" not in redacted
    assert "[REDACTED]" in redacted


def test_redacts_x_team_token_header_form():
    redacted = _redact({"headers": {"X-Team-Token": "sbc_team_secret_blob_value_123"}})
    # Token value should be redacted regardless of being inside dict
    assert "sbc_team_secret" not in json.dumps(redacted)


def test_redact_preserves_safe_strings():
    assert _redact("normal text") == "normal text"
    assert _redact({"a": 1, "b": "hi"}) == {"a": 1, "b": "hi"}


def test_logger_writes_jsonl(tmp_path):
    log = EvidenceLogger(run_id="test-run", base_dir=tmp_path)
    log.write("hello", note="world")
    log.mcp_call("kitchen_get_capacity", {}, result_summary={"capacity": 420})

    lines = log.path.read_text().strip().splitlines()
    assert len(lines) == 2
    parsed = [json.loads(l) for l in lines]
    assert parsed[0]["kind"] == "hello"
    assert parsed[0]["note"] == "world"
    assert parsed[0]["runId"] == "test-run"
    assert parsed[1]["kind"] == "mcp_call"
    assert parsed[1]["tool"] == "kitchen_get_capacity"


def test_logger_redacts_token_in_payload(tmp_path):
    log = EvidenceLogger(run_id="redact-test", base_dir=tmp_path)
    log.write(
        "outbound",
        body="POST with token sbc_team_xxxxxxxx in the body",
    )
    line = json.loads(log.path.read_text().strip())
    assert "sbc_team_x" not in line["body"]
    assert "[REDACTED]" in line["body"]
