"""Evidence logger tests — schema, redaction, append-only."""
from __future__ import annotations

import json

import pytest

from orchestrator.evidence import EvidenceLogger, _redact, read_jsonl_tail, unresolved_approval_requests


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


def test_logger_writes_growth_bonus_rows(tmp_path):
    log = EvidenceLogger(run_id="growth-test", base_dir=tmp_path)
    log.write(
        "lead_score",
        channel="whatsapp",
        score=90,
        segment="hot",
        evidenceSources=["whatsapp_inbound", "square_recent_orders"],
    )
    log.write(
        "whatsapp_follow_up_sent",
        recipient="+12815550123",
        evidenceSources=["square_recent_orders", "whatsapp_send"],
    )

    rows = [json.loads(line) for line in log.path.read_text().strip().splitlines()]
    assert rows[0]["kind"] == "lead_score"
    assert rows[0]["evidenceSources"] == ["whatsapp_inbound", "square_recent_orders"]
    assert rows[1]["kind"] == "whatsapp_follow_up_sent"


def test_read_jsonl_tail_skips_bad_lines(tmp_path):
    path = tmp_path / "orchestrator-run-tail.jsonl"
    path.write_text(
        '{"kind":"one"}\nnot json\n{"kind":"two"}\n',
        encoding="utf-8",
    )

    assert read_jsonl_tail(path, limit=2) == [{"kind": "two"}]


def test_unresolved_approval_requests_lists_only_pending_latest_run(tmp_path):
    older = tmp_path / "orchestrator-run-old.jsonl"
    older.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "ts": "2026-05-10T01:00:00Z",
                        "kind": "owner_msg",
                        "subkind": "approval_request",
                        "approvalId": "old",
                        "summary": "old pending",
                    }
                )
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    latest = tmp_path / "orchestrator-run-new.jsonl"
    latest.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "ts": "2026-05-10T02:00:00Z",
                        "kind": "owner_msg",
                        "subkind": "approval_request",
                        "approvalId": "resolved",
                        "summary": "already resolved",
                    }
                ),
                json.dumps(
                    {
                        "ts": "2026-05-10T02:01:00Z",
                        "kind": "owner_msg",
                        "subkind": "approval_resolution",
                        "approvalId": "resolved",
                        "verdict": "approve",
                    }
                ),
                json.dumps(
                    {
                        "ts": "2026-05-10T02:02:00Z",
                        "kind": "owner_msg",
                        "subkind": "approval_request",
                        "approvalId": "pending",
                        "summary": "needs owner",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = unresolved_approval_requests(tmp_path)

    assert result["path"] == str(latest)
    assert [row["approvalId"] for row in result["pending"]] == ["pending"]
