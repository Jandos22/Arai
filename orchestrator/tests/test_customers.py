"""Customer profile store + repeat-customer flow tests."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from orchestrator.customers import (
    CustomerStore,
    is_greeting,
    propose_reorder,
)
from orchestrator.dispatcher import HandlerContext
from orchestrator.handlers import instagram as instagram_handler
from orchestrator.handlers import whatsapp as whatsapp_handler


# ---------- pure helpers --------------------------------------------------


@pytest.mark.parametrize(
    "msg, expected",
    [
        ("hi", True),
        ("Hi!", True),
        ("hello there", False),  # has trailing words → not bare greeting
        ("hello", True),
        ("Salem!", True),
        ("Good morning", True),
        ("good morning, can I order a cake?", False),
        ("I want to order a cake", False),
        ("", False),
    ],
)
def test_is_greeting(msg: str, expected: bool) -> None:
    assert is_greeting(msg) is expected


def test_propose_reorder_requires_repeat_signal() -> None:
    assert propose_reorder({}) is None
    assert propose_reorder({"favorite_product": {"sku": "medovik", "count": 1}}) is None


def test_propose_reorder_builds_message_with_saved_payment() -> None:
    profile = {
        "name": "Sam",
        "favorite_product": {"sku": "medovik-medium", "count": 4},
        "payment_token": "sandbox_card_visa_4242",
        "delivery_address": "123 Main St",
    }
    proposal = propose_reorder(profile)
    assert proposal is not None
    assert proposal["sku"] == "medovik-medium"
    assert proposal["saved_payment"] is True
    assert proposal["saved_address"] is True
    assert "Sam" in proposal["message"]
    assert "medovik medium" in proposal["message"]
    assert "saved address" in proposal["message"]


# ---------- store ---------------------------------------------------------


def test_customer_store_upsert_and_favorite_detection(tmp_path: Path) -> None:
    store = CustomerStore(path=tmp_path / "customers.json")
    recent = {
        "orders": [
            {"id": "o1", "phone": "+12815550100", "sku": "medovik-medium"},
            {"id": "o2", "phone": "+12815550100", "sku": "medovik-medium"},
            {"id": "o3", "phone": "+12815550100", "sku": "milk-maiden"},
            {"id": "x1", "phone": "+12815559999", "sku": "honey-cake"},
        ]
    }
    profile = store.upsert_from_inbound(
        channel="whatsapp",
        identifier="+12815550100",
        name="Sam",
        recent_orders=recent,
    )
    assert profile["name"] == "Sam"
    assert profile["favorite_product"] == {"sku": "medovik-medium", "count": 2}
    assert len(profile["last_orders"]) == 3
    assert profile["channel_keys"]["whatsapp"] == "+12815550100"

    # Second upsert without orders preserves favorite_product (last good)
    again = store.upsert_from_inbound(
        channel="whatsapp",
        identifier="+12815550100",
        recent_orders=None,
    )
    assert again["favorite_product"] == {"sku": "medovik-medium", "count": 2}


# ---------- handler integration ------------------------------------------


class _FakeMCP:
    def __init__(self, responses: dict[str, Any]):
        self.responses = responses
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        args = arguments or {}
        self.calls.append((name, args))
        value = self.responses.get(name)
        if callable(value):
            return value(args)
        return value


class _RecordingEvidence:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def write(self, kind: str, **fields: Any) -> None:
        self.entries.append({"kind": kind, **fields})

    def mcp_call(self, tool: str, args: dict[str, Any] | None = None, **rest: Any) -> None:
        self.write("mcp_call", tool=tool, args=args or {}, **rest)


class _FakeRunner:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def run(self, prompt: str, *, label: str = "claude_p") -> str:
        self.prompts.append(prompt)
        return ""


def test_whatsapp_greeting_triggers_proposed_reorder(tmp_path: Path) -> None:
    store = CustomerStore(path=tmp_path / "customers.json")
    # Pre-seed two prior orders so the favorite kicks in
    store.upsert_from_inbound(
        channel="whatsapp",
        identifier="+12815550100",
        name="Sam",
        recent_orders={
            "orders": [
                {"id": "o1", "phone": "+12815550100", "sku": "medovik-medium"},
                {"id": "o2", "phone": "+12815550100", "sku": "medovik-medium"},
            ]
        },
    )

    mcp = _FakeMCP(
        {
            "square_recent_orders": {"orders": []},
            "whatsapp_send": {"ok": True, "messageId": "wa_proposed_1"},
        }
    )
    ev = _RecordingEvidence()
    runner = _FakeRunner()
    ctx = HandlerContext(client=mcp, evidence=ev, sales_runner=runner, customers=store)  # type: ignore[arg-type]

    whatsapp_handler.handle(
        {
            "channel": "whatsapp",
            "type": "inbound_message",
            "payload": {"from": "+12815550100", "message": "Hi!"},
        },
        ctx,
    )

    kinds = [e["kind"] for e in ev.entries]
    assert "customer_profile_upserted" in kinds
    assert "repeat_customer_detected" in kinds
    assert "proposed_reorder" in kinds
    # Sales runner should NOT have been invoked when we short-circuit with reorder
    assert runner.prompts == []
    # WhatsApp send should have been called with the proposal message
    sent = [c for c in mcp.calls if c[0] == "whatsapp_send"]
    assert len(sent) == 1
    assert "medovik medium" in sent[0][1]["message"]


def test_whatsapp_inbound_without_repeat_history_falls_through(tmp_path: Path) -> None:
    store = CustomerStore(path=tmp_path / "customers.json")
    mcp = _FakeMCP({"square_recent_orders": {"orders": []}})
    ev = _RecordingEvidence()
    runner = _FakeRunner()
    ctx = HandlerContext(client=mcp, evidence=ev, sales_runner=runner, customers=store)  # type: ignore[arg-type]

    whatsapp_handler.handle(
        {
            "channel": "whatsapp",
            "type": "inbound_message",
            "payload": {"from": "+12815550999", "message": "Hi!"},
        },
        ctx,
    )

    kinds = [e["kind"] for e in ev.entries]
    assert "customer_profile_upserted" in kinds
    assert "repeat_customer_detected" not in kinds
    assert "proposed_reorder" not in kinds
    # Sales runner gets the prompt because we fell through
    assert len(runner.prompts) == 1


def test_instagram_greeting_triggers_proposed_reorder(tmp_path: Path) -> None:
    store = CustomerStore(path=tmp_path / "customers.json")
    store.upsert_from_inbound(
        channel="instagram",
        identifier="sam_h",
        name="Sam",
    )
    # Manually set a favorite (IG handle has no phone match in Square)
    profiles = store.all_profiles()
    profiles["sam_h"]["favorite_product"] = {"sku": "milk-maiden", "count": 3}
    store._save(profiles)  # type: ignore[attr-defined]

    mcp = _FakeMCP(
        {
            "square_recent_orders": {"orders": []},
            "instagram_send_dm": {"ok": True, "messageId": "ig_proposed_1"},
        }
    )
    ev = _RecordingEvidence()
    runner = _FakeRunner()
    ctx = HandlerContext(client=mcp, evidence=ev, sales_runner=runner, customers=store)  # type: ignore[arg-type]

    instagram_handler.handle(
        {
            "channel": "instagram",
            "type": "dm",
            "payload": {"threadId": "t1", "from": "sam_h", "message": "hello"},
        },
        ctx,
    )

    kinds = [e["kind"] for e in ev.entries]
    assert "repeat_customer_detected" in kinds
    assert "proposed_reorder" in kinds
    sent = [c for c in mcp.calls if c[0] == "instagram_send_dm"]
    assert len(sent) == 1
    assert sent[0][1]["threadId"] == "t1"
    assert runner.prompts == []


def test_instagram_owner_gated_response_queues_outbound_draft() -> None:
    mcp = _FakeMCP({"square_recent_orders": {"orders": []}})
    ev = _RecordingEvidence()
    runner = _FakeRunner()
    runner.run = lambda prompt, *, label="claude_p": (
        '{"needs_approval": true, "kind": "transactional", '
        '"trigger": "standing_order", "summary": "Owner review needed", '
        '"draft_reply": "Thanks — I am checking this with the owner before confirming the Friday box."}'
    )
    ctx = HandlerContext(client=mcp, evidence=ev, sales_runner=runner)  # type: ignore[arg-type]

    instagram_handler.handle(
        {
            "channel": "instagram",
            "type": "dm",
            "payload": {
                "threadId": "ig-deshawn-001",
                "from": "deshawn_office",
                "message": "Can we set up a weekly office dessert box?",
            },
        },
        ctx,
    )

    outbound = [entry for entry in ev.entries if entry["kind"] == "channel_outbound"]
    assert len(outbound) == 1
    assert outbound[0]["channel"] == "instagram"
    assert outbound[0]["tool"] == "instagram_send_dm"
    assert outbound[0]["recipient"] == "ig-deshawn-001"
    assert outbound[0]["status"] == "queued_owner_gate"
    assert "Friday box" in outbound[0]["bodyPreview"]


def test_instagram_plain_response_without_recipient_queues_draft() -> None:
    mcp = _FakeMCP({})
    ev = _RecordingEvidence()
    runner = _FakeRunner()
    runner.run = lambda prompt, *, label="claude_p": (
        "Draft reply ready once the comment id is attached: Yes, local delivery is quoted case by case."
    )
    ctx = HandlerContext(client=mcp, evidence=ev, sales_runner=runner)  # type: ignore[arg-type]

    instagram_handler.handle(
        {
            "channel": "instagram",
            "type": "comment",
            "payload": {
                "from": "unknown",
                "comment": "Do you deliver in Sugar Land today?",
            },
        },
        ctx,
    )

    outbound = [entry for entry in ev.entries if entry["kind"] == "channel_outbound"]
    assert len(outbound) == 1
    assert outbound[0]["channel"] == "instagram"
    assert outbound[0]["tool"] == "instagram_reply_to_comment"
    assert outbound[0]["recipient"] == "unknown"
    assert outbound[0]["status"] == "draft_needs_recipient"
    assert outbound[0]["reason"] == "missing_comment_or_thread_id"
    assert any(entry["kind"] == "instagram_draft_queued" for entry in ev.entries)
