"""Claude runner stream parsing tests."""
from __future__ import annotations

import json
from pathlib import Path

from orchestrator.claude_runner import ClaudeRunner, _parse_stream_json


class _RecordingEvidence:
    def __init__(self) -> None:
        self.entries = []

    def write(self, kind, **fields):
        self.entries.append({"kind": kind, **fields})


def test_parse_stream_json_extracts_final_result_and_tool_use():
    stream = "\n".join(
        [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "mcp__happycake__whatsapp_send",
                                "input": {
                                    "to": "+12815550199",
                                    "message": "Honey cake is available today.",
                                },
                            }
                        ]
                    },
                }
            ),
            json.dumps(
                {
                    "type": "result",
                    "result": "Sent the customer a WhatsApp reply.",
                    "num_turns": 3,
                    "total_cost_usd": 0.12,
                    "is_error": False,
                }
            ),
        ]
    )

    response, tool_uses, meta = _parse_stream_json(stream)

    assert response == "Sent the customer a WhatsApp reply."
    assert tool_uses == [
        {
            "name": "mcp__happycake__whatsapp_send",
            "input": {
                "to": "+12815550199",
                "message": "Honey cake is available today.",
            },
        }
    ]
    assert meta["num_turns"] == 3
    assert meta["total_cost_usd"] == 0.12
    assert meta["is_error"] is False


def test_parse_stream_json_falls_back_to_plain_stdout():
    response, tool_uses, meta = _parse_stream_json("plain final answer\n")

    assert response == "plain final answer"
    assert tool_uses == []
    assert meta == {}


def test_log_tool_use_writes_channel_outbound_for_whatsapp():
    evidence = _RecordingEvidence()
    runner = ClaudeRunner(Path("/tmp/agents/sales"), evidence, binary="/bin/echo")

    logged = runner._log_tool_use(
        {
            "name": "mcp__happycake__whatsapp_send",
            "input": {
                "to": "+12815550199",
                "message": "Honey cake is available today.\nWant me to hold one?",
            },
        },
        label="whatsapp_inbound",
    )

    assert logged is True
    assert evidence.entries[0]["kind"] == "agent_tool_use"
    outbound = evidence.entries[1]
    assert outbound["kind"] == "channel_outbound"
    assert outbound["channel"] == "whatsapp"
    assert outbound["recipient"] == "+12815550199"
    assert outbound["bodyPreview"] == "Honey cake is available today. Want me to hold one?"


def test_log_tool_use_writes_channel_outbound_for_gmb_post():
    evidence = _RecordingEvidence()
    runner = ClaudeRunner(Path("/tmp/agents/ops"), evidence, binary="/bin/echo")

    logged = runner._log_tool_use(
        {
            "name": "mcp__happycake__gb_simulate_post",
            "input": {
                "content": "Fresh cake \"Honey\" is ready at HappyCake today.",
                "callToAction": {"label": "Order", "url": "https://happycake.us/order"},
            },
        },
        label="gmb_local_post",
    )

    assert logged is True
    assert evidence.entries[0]["kind"] == "agent_tool_use"
    outbound = evidence.entries[1]
    assert outbound["kind"] == "channel_outbound"
    assert outbound["channel"] == "gmb"
    assert outbound["recipient"] == "proposed_gmb_post"
    assert outbound["bodyPreview"] == "Fresh cake \"Honey\" is ready at HappyCake today."


def test_log_tool_use_ignores_local_claude_tools():
    evidence = _RecordingEvidence()
    runner = ClaudeRunner(Path("/tmp/agents/marketing"), evidence, binary="/bin/echo")

    logged = runner._log_tool_use(
        {
            "name": "Edit",
            "input": {
                "file_path": "/tmp/docs/MARKETING.md",
                "new_string": "local doc edit",
            },
        },
        label="marketing_trigger",
    )

    assert logged is False
    assert evidence.entries == []
