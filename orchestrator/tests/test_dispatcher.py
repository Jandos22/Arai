"""Dispatcher routing tests."""
from __future__ import annotations

from orchestrator.dispatcher import HandlerContext, make_dispatcher


def _ctx(evidence):
    return HandlerContext(client=None, evidence=evidence)  # type: ignore[arg-type]


class _RecordingEvidence:
    def __init__(self):
        self.entries = []

    def write(self, kind, **fields):
        self.entries.append({"kind": kind, **fields})


def test_exact_channel_type_match():
    calls = []

    def h(event, ctx):
        calls.append(event["type"])

    table = {"whatsapp:inbound_message": h}
    ev = _RecordingEvidence()
    dispatch = make_dispatcher(_ctx(ev), table)

    dispatch({"channel": "whatsapp", "type": "inbound_message", "payload": {}})
    assert calls == ["inbound_message"]


def test_channel_wildcard_fallback():
    calls = []

    def h(event, ctx):
        calls.append(event["type"])

    table = {"whatsapp:*": h}
    ev = _RecordingEvidence()
    dispatch = make_dispatcher(_ctx(ev), table)

    dispatch({"channel": "whatsapp", "type": "weird_new_event"})
    assert calls == ["weird_new_event"]


def test_no_handler_logs_drop():
    ev = _RecordingEvidence()
    dispatch = make_dispatcher(_ctx(ev), {})

    dispatch({"channel": "unknown", "type": "x"})
    assert any(e["kind"] == "dispatch_drop" for e in ev.entries)


def test_handler_exception_is_logged_and_swallowed():
    ev = _RecordingEvidence()

    def boom(event, ctx):
        raise RuntimeError("kitchen on fire")

    dispatch = make_dispatcher(_ctx(ev), {"whatsapp:*": boom})
    # Must not raise — the orchestrator loop has to keep running.
    dispatch({"channel": "whatsapp", "type": "inbound_message", "payload": {"x": 1}})

    errors = [e for e in ev.entries if e["kind"] == "handler_error"]
    assert len(errors) == 1
    err = errors[0]
    assert err["handler"] == "boom"
    assert "RuntimeError" in err["error"]
    assert "kitchen on fire" in err["error"]
    assert err["key"] == "whatsapp:inbound_message"
    assert "traceback" in err


def test_handler_error_notifies_telegram_when_present():
    ev = _RecordingEvidence()
    notifications = []

    class _Notifier:
        def notify(self, text, **extra):
            notifications.append((text, extra))

    ctx = HandlerContext(client=None, evidence=ev, telegram_notifier=_Notifier())  # type: ignore[arg-type]

    def boom(event, ctx):
        raise ValueError("nope")

    dispatch = make_dispatcher(ctx, {"*": boom})
    dispatch({"channel": "x", "type": "y"})

    assert notifications, "telegram notifier should be called"
    text, extra = notifications[0]
    assert "Handler error" in text
    assert extra.get("kind") == "handler_error"


def test_global_wildcard_catches_everything():
    calls = []

    def catchall(event, ctx):
        calls.append(event["type"])

    ev = _RecordingEvidence()
    dispatch = make_dispatcher(_ctx(ev), {"*": catchall})

    dispatch({"channel": "novel", "type": "anything"})
    assert calls == ["anything"]
