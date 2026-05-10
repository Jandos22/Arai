"""Thin JSON-RPC 2.0 client for the Happy Cake sandbox MCP.

Auth: ``X-Team-Token`` header (NOT ``Authorization: Bearer`` — confirmed in T-004).
Wire format: plain JSON-RPC over HTTPS POST. The server returns a single JSON
body — no SSE despite the MCP spec hint.

Response envelope quirk: ``result.content[0].text`` is a **JSON-encoded string**,
not an object. We unwrap it here so callers always get parsed Python data.

This module is the ONLY place we touch ``httpx`` against the sandbox. Every
other module routes through :func:`MCPClient.call_tool`.
"""
from __future__ import annotations

import json
import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger(__name__)

DEFAULT_URL = "https://www.steppebusinessclub.com/api/mcp"


class MCPError(RuntimeError):
    """Wraps a JSON-RPC error response or transport failure."""


@dataclass
class MCPClient:
    """Synchronous MCP client. Token loaded from env at construction time.

    The orchestrator is single-process; sync is fine and keeps tracebacks
    readable. If we later need concurrency, swap to :class:`httpx.AsyncClient`.
    """

    url: str = DEFAULT_URL
    token: str | None = None
    timeout: float = 30.0
    max_retries: int = 2  # transient-error retries on 5xx / transport errors
    _client: httpx.Client | None = None

    @classmethod
    def from_env(cls) -> "MCPClient":
        token = os.environ.get("STEPPE_MCP_TOKEN")
        url = os.environ.get("STEPPE_MCP_URL", DEFAULT_URL)
        if not token:
            raise MCPError(
                "STEPPE_MCP_TOKEN missing. Source .env.local before running."
            )
        return cls(url=url, token=token)

    def __post_init__(self) -> None:
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    **({"X-Team-Token": self.token} if self.token else {}),
                },
            )

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "MCPClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # --- public API -----------------------------------------------------

    def list_tools(self) -> list[dict[str, Any]]:
        """Return raw ``tools/list`` response. No parsing — server already
        returns canonical JSON shapes here."""
        envelope = self._rpc("tools/list", {})
        return envelope["result"]["tools"]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Call an MCP tool. Returns the **parsed** content, unwrapping the
        ``content[0].text`` JSON-encoded string envelope.

        Returns ``None`` if the tool returned an empty content list (rare).
        Raises :class:`MCPError` on any RPC error.
        """
        args = arguments or {}
        envelope = self._rpc(
            "tools/call", {"name": name, "arguments": args}
        )
        content = envelope.get("result", {}).get("content") or []
        if not content:
            return None
        first = content[0]
        text = first.get("text")
        if text is None:
            return first
        # Per T-001: text is JSON-encoded. Try to parse; fall back to raw if not.
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    # --- internal -------------------------------------------------------

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        assert self._client is not None
        payload = {
            "jsonrpc": "2.0",
            "id": random.randint(1, 10**9),
            "method": method,
            "params": params,
        }
        last_exc: Exception | None = None
        last_resp: httpx.Response | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._client.post(self.url, json=payload)
            except httpx.HTTPError as exc:
                last_exc = exc
                last_resp = None
                log.warning("transport error on %s (attempt %d): %s", method, attempt + 1, exc)
            else:
                last_exc = None
                last_resp = resp
                if resp.status_code < 500:
                    break
                log.warning(
                    "transient %s on %s (attempt %d): %s",
                    resp.status_code, method, attempt + 1, resp.text[:200],
                )
            if attempt < self.max_retries:
                # 0.4s, 0.8s with small jitter — caps at ~1s tail latency.
                time.sleep(0.4 * (2 ** attempt) + random.random() * 0.1)
        if last_resp is None:
            raise MCPError(f"transport error calling {method}: {last_exc}") from last_exc
        resp = last_resp
        if resp.status_code >= 500:
            raise MCPError(f"{method} -> HTTP {resp.status_code}: {resp.text[:200]}")
        if resp.status_code == 401 or resp.status_code == 403:
            raise MCPError(
                f"{method} -> HTTP {resp.status_code}. Check STEPPE_MCP_TOKEN."
            )
        try:
            envelope = resp.json()
        except ValueError as exc:
            raise MCPError(
                f"{method} -> non-JSON response (HTTP {resp.status_code}): "
                f"{resp.text[:200]}"
            ) from exc
        if "error" in envelope:
            err = envelope["error"]
            raise MCPError(f"{method} -> RPC error {err.get('code')}: {err.get('message')}")
        return envelope
