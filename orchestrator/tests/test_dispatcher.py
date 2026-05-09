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


def test_global_wildcard_catches_everything():
    calls = []

    def catchall(event, ctx):
        calls.append(event["type"])

    ev = _RecordingEvidence()
    dispatch = make_dispatcher(_ctx(ev), {"*": catchall})

    dispatch({"channel": "novel", "type": "anything"})
    assert calls == ["anything"]
