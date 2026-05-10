"""WhatsApp growth-layer handler tests."""
from __future__ import annotations

from typing import Any

from orchestrator.dispatcher import HandlerContext
from orchestrator.handlers import whatsapp as whatsapp_handler


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

    def mcp_call(
        self,
        tool: str,
        args: dict[str, Any] | None = None,
        result_summary: Any = None,
        ok: bool = True,
        error: str | None = None,
    ) -> None:
        self.write(
            "mcp_call",
            tool=tool,
            args=args or {},
            ok=ok,
            error=error,
            resultSummary=result_summary,
        )


class _FakeRunner:
    def __init__(self, response: str = "Sent reply") -> None:
        self.response = response
        self.prompts: list[str] = []

    def run(self, prompt: str, *, label: str = "claude_p") -> str:
        self.prompts.append(prompt)
        return self.response


def _ctx(mcp: _FakeMCP, evidence: _RecordingEvidence, runner: Any = None) -> HandlerContext:
    return HandlerContext(client=mcp, evidence=evidence, sales_runner=runner)  # type: ignore[arg-type]


def test_whatsapp_inbound_writes_lead_score_from_square_evidence():
    mcp = _FakeMCP(
        {
            "square_recent_orders": {
                "orders": [{"id": "sq_order_1", "customerPhone": "+1 281 555 0123"}]
            }
        }
    )
    ev = _RecordingEvidence()

    whatsapp_handler.handle(
        {
            "channel": "whatsapp",
            "type": "inbound_message",
            "payload": {
                "from": "+12815550123",
                "message": "I want a custom birthday cake for pickup tomorrow",
            },
        },
        _ctx(mcp, ev, _FakeRunner()),
    )

    scores = [entry for entry in ev.entries if entry["kind"] == "lead_score"]
    assert len(scores) == 1
    assert scores[0]["score"] == 90
    assert scores[0]["segment"] == "hot"
    assert scores[0]["route"] == "owner_review"
    assert "square_recent_orders" in scores[0]["evidenceSources"]


def test_owner_gated_whatsapp_response_queues_outbound_draft():
    mcp = _FakeMCP({"square_recent_orders": {"orders": []}})
    ev = _RecordingEvidence()
    runner = _FakeRunner(
        '{"needs_approval": true, "kind": "custom_cake_consult", '
        '"trigger": "custom_decoration", "summary": "Owner review needed", '
        '"draft_reply": "Thanks — I am checking this with the owner before confirming."}'
    )

    whatsapp_handler.handle(
        {
            "channel": "whatsapp",
            "type": "inbound_message",
            "payload": {
                "from": "+12815550123",
                "message": "Can you make a custom birthday cake tomorrow?",
            },
        },
        _ctx(mcp, ev, runner),
    )

    outbound = [entry for entry in ev.entries if entry["kind"] == "channel_outbound"]
    assert len(outbound) == 1
    assert outbound[0]["channel"] == "whatsapp"
    assert outbound[0]["tool"] == "whatsapp_send"
    assert outbound[0]["recipient"] == "+12815550123"
    assert outbound[0]["status"] == "queued_owner_gate"
    assert "checking this with the owner" in outbound[0]["bodyPreview"]


def test_follow_up_due_respects_explicit_message_no_referral_pitch(tmp_path, monkeypatch):
    # Explicit caller-provided message must not be overridden with the pitch.
    from orchestrator import handlers
    from orchestrator.referrals import ReferralStore

    monkeypatch.setattr(
        handlers.whatsapp,
        "_REFERRALS",
        ReferralStore(path=tmp_path / "referrals.json"),
    )
    mcp = _FakeMCP(
        {
            "square_recent_orders": {"orders": []},
            "whatsapp_send": {"ok": True},
        }
    )
    ev = _RecordingEvidence()

    whatsapp_handler.handle_follow_up_due(
        {
            "channel": "whatsapp",
            "type": "follow_up_due",
            "payload": {
                "to": "+12815550123",
                "message": "Custom abandoned-cart copy from caller.",
            },
        },
        _ctx(mcp, ev),
    )
    sent = next(args for name, args in mcp.calls if name == "whatsapp_send")
    assert sent["message"] == "Custom abandoned-cart copy from caller."
    assert not any(e["kind"] == "referral_issued" for e in ev.entries)


def test_inbound_self_redemption_marked_not_matched(tmp_path, monkeypatch):
    from orchestrator import handlers
    from orchestrator.referrals import ReferralStore, code_for

    store = ReferralStore(path=tmp_path / "referrals.json")
    sender = "+12815550123"
    issued = store.issue(sender)
    monkeypatch.setattr(handlers.whatsapp, "_REFERRALS", store)

    mcp = _FakeMCP({"square_recent_orders": {"orders": []}})
    ev = _RecordingEvidence()

    whatsapp_handler.handle(
        {
            "channel": "whatsapp",
            "type": "inbound_message",
            "payload": {"from": sender, "message": f"my code is {issued['code']}"},
        },
        _ctx(mcp, ev, _FakeRunner()),
    )
    redeems = [e for e in ev.entries if e["kind"] == "referral_redeemed"]
    assert len(redeems) == 1
    assert redeems[0]["selfRedeem"] is True
    assert redeems[0]["matched"] is False
    assert code_for(sender) == issued["code"]  # sanity


def test_follow_up_due_checks_square_then_sends_whatsapp():
    mcp = _FakeMCP(
        {
            "square_recent_orders": {"orders": [{"id": "sq_order_123"}]},
            "whatsapp_send": {"ok": True, "messageId": "wa_1"},
        }
    )
    ev = _RecordingEvidence()

    whatsapp_handler.handle_follow_up_due(
        {
            "channel": "whatsapp",
            "type": "follow_up_due",
            "payload": {"to": "+12815550123", "pickupAt": "today at 4 PM"},
        },
        _ctx(mcp, ev),
    )

    assert [name for name, _ in mcp.calls] == ["square_recent_orders", "whatsapp_send"]
    send_args = mcp.calls[-1][1]
    assert send_args["to"] == "+12815550123"
    assert "sq_order_123" in send_args["message"]
    assert any(entry["kind"] == "whatsapp_follow_up_sent" for entry in ev.entries)
    assert any(entry["kind"] == "channel_outbound" for entry in ev.entries)
