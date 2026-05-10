"""Google Business handler prompt-routing tests."""
from __future__ import annotations

from typing import Any

from orchestrator.dispatcher import HandlerContext
from orchestrator.handlers import gmb as gmb_handler


class _RecordingEvidence:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def write(self, kind: str, **fields: Any) -> None:
        self.entries.append({"kind": kind, **fields})


class _RecordingRunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def run(self, prompt: str, *, label: str = "claude_p") -> str:
        self.calls.append({"prompt": prompt, "label": label})
        return "ok"


def _ctx(evidence: _RecordingEvidence, runner: _RecordingRunner | None) -> HandlerContext:
    return HandlerContext(client=None, evidence=evidence, ops_runner=runner)  # type: ignore[arg-type]


def test_review_prompt_requires_action_check_and_owner_gate():
    ev = _RecordingEvidence()
    runner = _RecordingRunner()

    gmb_handler.handle(
        {
            "channel": "gmb",
            "type": "review_received",
            "payload": {"reviewId": "rev_1", "rating": 2, "text": "Too slow."},
        },
        _ctx(ev, runner),
    )

    assert runner.calls[0]["label"] == "gmb_review"
    prompt = runner.calls[0]["prompt"]
    assert "gb_list_reviews" in prompt
    assert "gb_list_simulated_actions" in prompt
    assert "owner-gate JSON" in prompt
    assert "do not call gb_simulate_reply" in prompt


def test_local_post_prompt_records_proposal_then_owner_gates():
    ev = _RecordingEvidence()
    runner = _RecordingRunner()

    gmb_handler.handle(
        {
            "channel": "gmb",
            "type": "local_post_request",
            "payload": {"trigger": "fresh_honey", "detail": "Honey cake by the slice today."},
        },
        _ctx(ev, runner),
    )

    assert runner.calls[0]["label"] == "gmb_local_post"
    prompt = runner.calls[0]["prompt"]
    assert "gb_get_metrics" in prompt
    assert "gb_simulate_post exactly once" in prompt
    assert 'trigger="gmb_post_publish"' in prompt
    assert "Do not claim a real Google Business post was published" in prompt


def test_q_and_a_prompt_documents_missing_tool():
    ev = _RecordingEvidence()
    runner = _RecordingRunner()

    gmb_handler.handle(
        {
            "channel": "gbusiness",
            "type": "q_and_a",
            "payload": {"question": "Do you have cake slices today?"},
        },
        _ctx(ev, runner),
    )

    assert runner.calls[0]["label"] == "gmb_presence"
    prompt = runner.calls[0]["prompt"]
    assert "does not expose a Google Business Q&A write/read tool" in prompt
    assert "do not invent a tool call" in prompt


def test_missing_ops_runner_logs_drop():
    ev = _RecordingEvidence()

    gmb_handler.handle(
        {"channel": "gmb", "type": "metrics_check", "payload": {}},
        _ctx(ev, None),
    )

    assert {"kind": "channel_dropped", "channel": "gmb", "reason": "ops_runner_not_configured"} in ev.entries
