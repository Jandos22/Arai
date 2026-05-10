"""Health snapshot + audit-trail aggregation tests."""
from __future__ import annotations

import json
from pathlib import Path

from orchestrator.health import audit_trail, format_health, health_snapshot


def _write_run(base: Path, run_id: str, rows: list[dict]) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"orchestrator-run-{run_id}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps({"runId": run_id, **row}) + "\n")
    return path


def test_health_snapshot_empty(tmp_path):
    snap = health_snapshot(base_dir=tmp_path)
    assert snap["path"] is None
    assert snap["ok"] is True
    assert snap["pendingApprovals"] == []


def test_health_snapshot_aggregates(tmp_path):
    _write_run(
        tmp_path,
        "abc",
        [
            {"ts": "2026-05-10T00:00:00Z", "kind": "mcp_call", "tool": "kitchen_get_capacity", "ok": True},
            {"ts": "2026-05-10T00:00:01Z", "kind": "mcp_call", "tool": "square_create_order", "ok": False, "error": "boom"},
            {"ts": "2026-05-10T00:00:02Z", "kind": "handler_error", "handler": "h", "key": "whatsapp:inbound_message", "error": "RuntimeError: nope"},
            {"ts": "2026-05-10T00:00:03Z", "kind": "decision", "agent": "sales", "action": "reply", "rationale": "ok"},
            {"ts": "2026-05-10T00:00:04Z", "kind": "owner_msg", "subkind": "approval_request", "approvalId": "A1", "summary": "custom cake"},
        ],
    )
    snap = health_snapshot(base_dir=tmp_path)
    assert snap["runId"] == "abc"
    assert snap["mcp"] == {"total": 2, "errors": 1}
    assert snap["handlerErrors"] == 1
    assert snap["lastError"]["handler"] == "h"
    assert snap["lastDecision"]["agent"] == "sales"
    assert [p["approvalId"] for p in snap["pendingApprovals"]] == ["A1"]
    assert snap["ok"] is False


def test_pending_excludes_resolved(tmp_path):
    _write_run(
        tmp_path,
        "r2",
        [
            {"ts": "2026-05-10T00:00:00Z", "kind": "owner_msg", "subkind": "approval_request", "approvalId": "A1", "summary": "x"},
            {"ts": "2026-05-10T00:00:01Z", "kind": "owner_msg", "subkind": "approval_resolution", "approvalId": "A1", "decision": "approve"},
            {"ts": "2026-05-10T00:00:02Z", "kind": "owner_msg", "subkind": "approval_request", "approvalId": "A2", "summary": "y"},
        ],
    )
    snap = health_snapshot(base_dir=tmp_path)
    assert [p["approvalId"] for p in snap["pendingApprovals"]] == ["A2"]


def test_audit_trail_returns_full_chain(tmp_path):
    _write_run(
        tmp_path,
        "r3",
        [
            {"ts": "t1", "kind": "owner_msg", "subkind": "approval_request", "approvalId": "A1", "summary": "x"},
            {"ts": "t2", "kind": "owner_msg", "subkind": "approval_resolution", "approvalId": "A1", "decision": "approve"},
            {"ts": "t3", "kind": "owner_msg", "subkind": "approval_request", "approvalId": "B1", "summary": "y"},
            {"ts": "t4", "kind": "decision", "agent": "ops", "action": "kitchen_create_ticket", "approvalId": "A1"},
        ],
    )
    chain = audit_trail("A1", base_dir=tmp_path)
    assert len(chain["rows"]) == 3
    assert all(r.get("approvalId") == "A1" for r in chain["rows"])


def test_format_health_renders_block(tmp_path):
    _write_run(
        tmp_path,
        "r4",
        [
            {"ts": "t", "kind": "mcp_call", "tool": "x", "ok": True},
            {"ts": "t", "kind": "decision", "agent": "sales", "action": "reply", "rationale": ""},
        ],
    )
    snap = health_snapshot(base_dir=tmp_path)
    text = format_health(snap)
    assert "Run" in text
    assert "mcp: 1 calls" in text
    assert "🟢" in text  # ok run
