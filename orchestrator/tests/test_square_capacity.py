"""Capacity-aware Square walk-in handoff tests.

Cover both branches of the decision tree (accept + reject) plus the
custom-work short-circuit, using a fake MCP client and a recording
evidence logger. No network, no token.
"""
from __future__ import annotations

from typing import Any

from orchestrator.dispatcher import HandlerContext
from orchestrator.handlers import square as square_handler


class _FakeMCP:
    """Fake MCPClient that returns canned responses keyed by tool name.

    Records every call so tests can assert the exact tool chain.
    """

    def __init__(self, responses: dict[str, Any]):
        self.responses = responses
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        self.calls.append((name, arguments or {}))
        value = self.responses.get(name)
        if callable(value):
            return value(arguments or {})
        return value


class _RecordingEvidence:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def write(self, kind: str, **fields: Any) -> None:
        self.entries.append({"kind": kind, **fields})


def _walk_in_event(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "channel": "square",
        "type": "walk_in_order",
        "payload": {
            "source": "walk-in",
            "customerName": "Walk-in Smoke",
            "items": items,
        },
    }


def _ctx(mcp: _FakeMCP, evidence: _RecordingEvidence, telegram: Any = None) -> HandlerContext:
    return HandlerContext(client=mcp, evidence=evidence, telegram_notifier=telegram)  # type: ignore[arg-type]


def _decision_row(entries: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [e for e in entries if e["kind"] == "square_capacity_decision"]
    assert len(rows) == 1, f"expected exactly one capacity decision row, got {len(rows)}"
    return rows[0]


def _tools_called(mcp: _FakeMCP) -> list[str]:
    return [name for name, _ in mcp.calls]


def test_accept_path_when_capacity_is_ample():
    mcp = _FakeMCP(
        {
            "square_create_order": {"orderId": "ord_1", "status": "open"},
            "kitchen_create_ticket": {"ticketId": "tkt_1", "status": "queued"},
            "kitchen_get_capacity": {
                "dailyCapacityMinutes": 420,
                "defaultLeadTimeMinutes": 45,
                "activePrepMinutes": 0,
                "remainingCapacityMinutes": 420,
                "queuedTickets": 0,
                "acceptedTickets": 0,
            },
            "kitchen_get_menu_constraints": [
                {"productId": "honey-cake-slice", "prepMinutes": 5, "requiresCustomWork": False},
                {"productId": "honey-cake", "prepMinutes": 60, "requiresCustomWork": False},
            ],
            "kitchen_accept_ticket": {"ticketId": "tkt_1", "status": "accepted"},
            "kitchen_mark_ready": {"ticketId": "tkt_1", "status": "ready"},
            "square_update_order_status": {"orderId": "ord_1", "status": "ready"},
        }
    )
    ev = _RecordingEvidence()

    square_handler.handle(
        _walk_in_event(
            [
                {"variationId": "sq_var_honey_cake_slice", "quantity": 2},
                {"variationId": "sq_var_honey_cake_whole", "quantity": 1},
            ]
        ),
        _ctx(mcp, ev),
    )

    assert _tools_called(mcp) == [
        "square_create_order",
        "kitchen_create_ticket",
        "kitchen_get_capacity",
        "kitchen_get_menu_constraints",
        "kitchen_accept_ticket",
        "kitchen_mark_ready",
        "square_update_order_status",
    ]
    decision = _decision_row(ev.entries)
    assert decision["decision"] == "accept"
    assert decision["capacity_checked"] is True
    assert decision["orderId"] == "ord_1"
    assert decision["ticketId"] == "tkt_1"
    # 2×5 + 1×60 = 70 min required, 420 min remaining
    assert decision["requiredMinutes"] == 70
    assert decision["remainingMinutes"] == 420

    final = [e for e in ev.entries if e["kind"] == "square_handoff_complete"][-1]
    assert final["decision"] == "accept"


def test_reject_path_when_capacity_is_short_routes_to_owner_review():
    captured_status: dict[str, Any] = {}

    def _capture_status(args: dict[str, Any]) -> dict[str, Any]:
        captured_status.update(args)
        return {"orderId": args.get("orderId"), "status": args.get("status")}

    mcp = _FakeMCP(
        {
            "square_create_order": {"orderId": "ord_2"},
            "kitchen_create_ticket": {"ticketId": "tkt_2"},
            "kitchen_get_capacity": {
                "dailyCapacityMinutes": 420,
                "defaultLeadTimeMinutes": 45,
                "activePrepMinutes": 380,
                "remainingCapacityMinutes": 40,
                "queuedTickets": 12,
                "acceptedTickets": 8,
            },
            "kitchen_get_menu_constraints": [
                {"productId": "honey-cake", "prepMinutes": 60, "requiresCustomWork": False},
            ],
            "kitchen_reject_ticket": {"ticketId": "tkt_2", "status": "rejected"},
            "square_update_order_status": _capture_status,
        }
    )
    ev = _RecordingEvidence()

    class _FakeNotifier:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        def request_approval(self, **kw: Any) -> None:
            self.calls.append(kw)

    notifier = _FakeNotifier()

    square_handler.handle(
        _walk_in_event(
            [{"variationId": "sq_var_honey_cake_whole", "quantity": 1}]
        ),
        _ctx(mcp, ev, telegram=notifier),
    )

    tools = _tools_called(mcp)
    assert tools == [
        "square_create_order",
        "kitchen_create_ticket",
        "kitchen_get_capacity",
        "kitchen_get_menu_constraints",
        "kitchen_reject_ticket",
        "square_update_order_status",
    ]
    # Critical: never marks ready when rejected.
    assert "kitchen_mark_ready" not in tools
    assert "kitchen_accept_ticket" not in tools

    decision = _decision_row(ev.entries)
    assert decision["decision"] == "reject"
    assert decision["requiredMinutes"] == 60
    assert decision["remainingMinutes"] == 40
    assert "Capacity short" in decision["reason"]

    assert captured_status["status"] == "delayed_or_needs_owner_review"

    assert len(notifier.calls) == 1
    assert "delayed" in notifier.calls[0]["summary"].lower()
    assert notifier.calls[0]["context"]["decision"] == "reject"


def test_reject_path_when_item_requires_custom_work_short_circuits_capacity():
    mcp = _FakeMCP(
        {
            "square_create_order": {"orderId": "ord_3"},
            "kitchen_create_ticket": {"ticketId": "tkt_3"},
            "kitchen_get_capacity": {
                "dailyCapacityMinutes": 420,
                "defaultLeadTimeMinutes": 45,
                "activePrepMinutes": 0,
                "remainingCapacityMinutes": 420,
            },
            "kitchen_get_menu_constraints": {
                "products": [
                    {"productId": "custom-birthday-cake", "prepMinutes": 90, "requiresCustomWork": True},
                ]
            },
            "kitchen_reject_ticket": {"ticketId": "tkt_3", "status": "rejected"},
            "square_update_order_status": {"orderId": "ord_3", "status": "delayed_or_needs_owner_review"},
        }
    )
    ev = _RecordingEvidence()

    square_handler.handle(
        _walk_in_event(
            [{"variationId": "sq_var_custom_birthday_cake", "quantity": 1}]
        ),
        _ctx(mcp, ev),
    )

    decision = _decision_row(ev.entries)
    assert decision["decision"] == "reject"
    assert "custom-work" in decision["reason"]
    assert "custom-birthday-cake" in decision["reason"]
    # Custom-work line short-circuits before computing capacity required.
    assert decision["requiredMinutes"] == 0


def test_unmapped_items_short_circuit_before_capacity_check():
    mcp = _FakeMCP(
        {
            "square_create_order": {"orderId": "ord_4"},
        }
    )
    ev = _RecordingEvidence()

    square_handler.handle(
        _walk_in_event([{"variationId": "sq_var_unknown", "quantity": 1}]),
        _ctx(mcp, ev),
    )

    # No kitchen tools should fire when there's no mapping.
    assert _tools_called(mcp) == ["square_create_order"]
    assert any(
        e["kind"] == "square_handoff_failed" and e.get("reason") == "no_kitchen_mapping"
        for e in ev.entries
    )
    assert not any(e["kind"] == "square_capacity_decision" for e in ev.entries)


def test_unsupported_event_type_drops_without_calling_mcp():
    mcp = _FakeMCP({})
    ev = _RecordingEvidence()

    square_handler.handle(
        {"channel": "square", "type": "refund_issued", "payload": {}},
        _ctx(mcp, ev),
    )

    assert mcp.calls == []
    assert any(
        e["kind"] == "channel_dropped" and e.get("subtype") == "refund_issued"
        for e in ev.entries
    )
