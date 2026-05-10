"""Operator health snapshot + audit trail for the latest orchestrator run.

Read-only helpers that aggregate the latest evidence JSONL into a shape the
ops Telegram bot can show in one screen. No I/O outside the evidence dir.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .evidence import latest_evidence_file, read_jsonl_tail


def health_snapshot(
    base_dir: Path | str = Path("evidence"),
    *,
    pattern: str = "orchestrator-run-*.jsonl",
    tail_lines: int = 2000,
) -> dict[str, Any]:
    """Aggregate the latest run into a single owner-readable health dict.

    Returns counts of mcp calls / errors / handler errors, the most recent
    decision, and a list of unresolved owner approvals. Designed so the ops
    bot can render the result with no further parsing.
    """
    path = latest_evidence_file(base_dir, pattern)
    if path is None:
        return {
            "path": None,
            "runId": None,
            "ok": True,
            "rows": 0,
            "mcp": {"total": 0, "errors": 0},
            "handlerErrors": 0,
            "lastError": None,
            "lastDecision": None,
            "pendingApprovals": [],
            "kinds": {},
        }

    rows = read_jsonl_tail(path, limit=tail_lines)
    kinds: Counter[str] = Counter()
    mcp_total = 0
    mcp_errors = 0
    handler_errors = 0
    last_error: dict[str, Any] | None = None
    last_decision: dict[str, Any] | None = None
    approvals: dict[str, dict[str, Any]] = {}
    resolved: set[str] = set()
    run_id: str | None = None

    for row in rows:
        kind = row.get("kind") or "unknown"
        kinds[kind] += 1
        run_id = row.get("runId") or run_id
        if kind == "mcp_call":
            mcp_total += 1
            if not row.get("ok", True):
                mcp_errors += 1
                last_error = {
                    "ts": row.get("ts"),
                    "tool": row.get("tool"),
                    "error": row.get("error"),
                }
        elif kind == "handler_error":
            handler_errors += 1
            last_error = {
                "ts": row.get("ts"),
                "handler": row.get("handler"),
                "key": row.get("key"),
                "error": row.get("error"),
            }
        elif kind == "decision":
            last_decision = {
                "ts": row.get("ts"),
                "agent": row.get("agent"),
                "action": row.get("action"),
                "rationale": row.get("rationale"),
            }
        elif kind == "owner_msg":
            approval_id = row.get("approvalId")
            if isinstance(approval_id, str) and approval_id:
                if row.get("subkind") == "approval_request":
                    approvals[approval_id] = row
                elif row.get("subkind") == "approval_resolution":
                    resolved.add(approval_id)

    pending = [
        {
            "approvalId": aid,
            "ts": row.get("ts"),
            "summary": row.get("summary"),
        }
        for aid, row in approvals.items()
        if aid not in resolved
    ]
    pending.sort(key=lambda r: str(r.get("ts", "")))

    ok = handler_errors == 0 and mcp_errors == 0
    return {
        "path": str(path),
        "runId": run_id,
        "ok": ok,
        "rows": len(rows),
        "mcp": {"total": mcp_total, "errors": mcp_errors},
        "handlerErrors": handler_errors,
        "lastError": last_error,
        "lastDecision": last_decision,
        "pendingApprovals": pending,
        "kinds": dict(kinds),
    }


def audit_trail(
    approval_id: str,
    base_dir: Path | str = Path("evidence"),
    *,
    pattern: str = "orchestrator-run-*.jsonl",
    tail_lines: int = 5000,
) -> dict[str, Any]:
    """Return every evidence row that names the given approval id.

    Useful for ``/audit <id>`` so the owner can replay the chain of events
    that led to a single approve/reject decision.
    """
    path = latest_evidence_file(base_dir, pattern)
    if path is None:
        return {"path": None, "approvalId": approval_id, "rows": []}
    rows = read_jsonl_tail(path, limit=tail_lines)
    chain = [row for row in rows if row.get("approvalId") == approval_id]
    return {"path": str(path), "approvalId": approval_id, "rows": chain}


def format_health(snapshot: dict[str, Any]) -> str:
    """Render a snapshot as a compact Telegram-friendly block."""
    if snapshot.get("path") is None:
        return "🟡 No orchestrator runs found yet."
    icon = "🟢" if snapshot["ok"] else "🔴"
    mcp = snapshot["mcp"]
    lines = [
        f"{icon} Run `{snapshot['runId'] or '?'}`",
        f"  rows: {snapshot['rows']}",
        f"  mcp: {mcp['total']} calls, {mcp['errors']} errors",
        f"  handler errors: {snapshot['handlerErrors']}",
        f"  pending approvals: {len(snapshot['pendingApprovals'])}",
    ]
    if snapshot["lastError"]:
        err = snapshot["lastError"]
        lines.append(
            "  last error: "
            f"{err.get('ts', '?')} — {err.get('tool') or err.get('handler') or '?'}"
            f": {err.get('error') or '?'}"
        )
    if snapshot["lastDecision"]:
        d = snapshot["lastDecision"]
        lines.append(
            f"  last decision: {d.get('agent') or '?'} → {d.get('action') or '?'}"
        )
    return "\n".join(lines)
