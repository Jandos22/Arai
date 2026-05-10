"""MCPClient unit tests — no live token, fully mocked via respx."""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from orchestrator.mcp_client import MCPClient, MCPError


@pytest.fixture
def client():
    c = MCPClient(url="https://example.test/api/mcp", token="test-token")
    yield c
    c.close()


def _envelope(text_payload):
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"content": [{"type": "text", "text": json.dumps(text_payload)}]},
    }


@respx.mock
def test_call_tool_unwraps_text_envelope(client):
    respx.post("https://example.test/api/mcp").mock(
        return_value=httpx.Response(200, json=_envelope({"monthlyBudgetUsd": 500}))
    )
    result = client.call_tool("marketing_get_budget", {})
    assert result == {"monthlyBudgetUsd": 500}


@respx.mock
def test_call_tool_passes_arguments(client):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_envelope({"orderId": "ord_1"}))

    respx.post("https://example.test/api/mcp").mock(side_effect=handler)
    out = client.call_tool("square_create_order", {"items": [{"variationId": "x", "quantity": 1}]})
    assert out == {"orderId": "ord_1"}
    assert captured["body"]["method"] == "tools/call"
    assert captured["body"]["params"]["name"] == "square_create_order"
    assert captured["body"]["params"]["arguments"]["items"][0]["variationId"] == "x"


@respx.mock
def test_rpc_error_raises(client):
    respx.post("https://example.test/api/mcp").mock(
        return_value=httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "bad args"}},
        )
    )
    with pytest.raises(MCPError, match="bad args"):
        client.call_tool("kitchen_create_ticket", {})


@respx.mock
def test_unauthorized_raises(client):
    respx.post("https://example.test/api/mcp").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )
    with pytest.raises(MCPError, match="Check STEPPE_MCP_TOKEN"):
        client.call_tool("anything", {})


@respx.mock
def test_list_tools(client):
    respx.post("https://example.test/api/mcp").mock(
        return_value=httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"tools": [{"name": "square_list_catalog"}, {"name": "kitchen_get_capacity"}]},
            },
        )
    )
    tools = client.list_tools()
    assert len(tools) == 2
    assert tools[0]["name"] == "square_list_catalog"


@respx.mock
def test_transient_5xx_retries_then_succeeds(monkeypatch):
    # Avoid sleeping during retries.
    import orchestrator.mcp_client as mc
    monkeypatch.setattr(mc.time, "sleep", lambda *_: None)

    c = MCPClient(url="https://example.test/api/mcp", token="t", max_retries=2)
    try:
        route = respx.post("https://example.test/api/mcp").mock(
            side_effect=[
                httpx.Response(503, text="overloaded"),
                httpx.Response(502, text="bad gateway"),
                httpx.Response(200, json=_envelope({"ok": True})),
            ]
        )
        out = c.call_tool("anything", {})
        assert out == {"ok": True}
        assert route.call_count == 3
    finally:
        c.close()


@respx.mock
def test_transient_5xx_gives_up_after_retries(monkeypatch):
    import orchestrator.mcp_client as mc
    monkeypatch.setattr(mc.time, "sleep", lambda *_: None)

    c = MCPClient(url="https://example.test/api/mcp", token="t", max_retries=1)
    try:
        respx.post("https://example.test/api/mcp").mock(
            return_value=httpx.Response(503, text="overloaded")
        )
        with pytest.raises(MCPError, match="HTTP 503"):
            c.call_tool("anything", {})
    finally:
        c.close()


@respx.mock
def test_empty_content_returns_none(client):
    respx.post("https://example.test/api/mcp").mock(
        return_value=httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "result": {"content": []}},
        )
    )
    assert client.call_tool("noop", {}) is None
