"""Subprocess wrapper for ``claude -p`` headless invocations.

Each agent (sales, ops, marketing) is its own Claude Code project under
``agents/<role>/`` with a project-scoped ``.mcp.json`` and ``CLAUDE.md``.
The orchestrator delegates LLM reasoning by shelling into that directory
and running ``claude -p "<prompt>"``.

We capture stdout, log the prompt + a result summary to evidence, and return
the model's textual response. Errors propagate but are also logged.
"""
from __future__ import annotations

import json
import logging
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .evidence import EvidenceLogger

log = logging.getLogger(__name__)

_OUTBOUND_TOOL_MAP = {
    "mcp__happycake__whatsapp_send": ("whatsapp", "to", "message"),
    "mcp__happycake__instagram_send_dm": ("instagram", "threadId", "message"),
    "mcp__happycake__instagram_reply_to_comment": ("instagram", "commentId", "message"),
    "mcp__happycake__gb_simulate_reply": ("gmb", "reviewId", "reply"),
}


def _resolve_claude_binary(name: str = "claude") -> str:
    """Find the ``claude`` CLI even when invoked from a sparse PATH (e.g. a
    non-interactive ssh session whose PATH is ``/usr/bin:/bin:...``).

    Search order:
      1. Honour ``CLAUDE_BINARY`` env var if set (escape hatch for prod)
      2. ``shutil.which`` against the inherited PATH
      3. Common install locations: ``~/.local/bin/claude``, Homebrew, npm
    """
    override = os.environ.get("CLAUDE_BINARY")
    if override and Path(override).exists():
        return override

    found = shutil.which(name)
    if found:
        return found

    home = Path.home()
    candidates = [
        home / ".local" / "bin" / name,
        Path("/opt/homebrew/bin") / name,
        Path("/usr/local/bin") / name,
        home / ".bun" / "bin" / name,
    ]
    for path in candidates:
        if path.exists() and os.access(path, os.X_OK):
            return str(path)
    # Last resort: return bare name. subprocess will surface a clean
    # FileNotFoundError that tells the user to set CLAUDE_BINARY.
    return name


class ClaudeRunError(RuntimeError):
    pass


def _parse_stream_json(stdout: str) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    """Extract final text and tool_use events from ``claude`` stream-json.

    Falls back to the raw stdout shape when the CLI returns plain text. This
    keeps older/manual runner invocations readable while letting the
    orchestrator capture evaluator-visible tool calls.
    """
    saw_json = False
    result_text = ""
    result_meta: dict[str, Any] = {}
    tool_uses: list[dict[str, Any]] = []

    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        saw_json = True
        if event.get("type") == "assistant":
            content = (event.get("message") or {}).get("content") or []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    name = block.get("name")
                    if isinstance(name, str):
                        tool_uses.append(
                            {
                                "name": name,
                                "input": block.get("input") or {},
                            }
                        )
        elif event.get("type") == "result":
            result_text = event.get("result") or ""
            result_meta = {
                "num_turns": event.get("num_turns"),
                "total_cost_usd": event.get("total_cost_usd"),
                "is_error": event.get("is_error"),
            }

    if not saw_json:
        return stdout.strip(), [], {}
    return result_text.strip(), tool_uses, {k: v for k, v in result_meta.items() if v is not None}


def _body_preview(value: Any, limit: int = 240) -> str:
    if value is None:
        return ""
    return str(value).replace("\n", " ")[:limit]


@dataclass
class ClaudeRunner:
    project_dir: Path
    evidence: EvidenceLogger
    timeout: float = 600.0
    binary: str = ""  # resolved lazily in __post_init__
    extra_args: tuple[str, ...] = (
        "--mcp-config",
        ".mcp.json",
        "--permission-mode",
        "bypassPermissions",
        "--output-format",
        "stream-json",
        "--verbose",
    )

    def __post_init__(self) -> None:
        if not self.binary:
            self.binary = _resolve_claude_binary()

    def run(self, prompt: str, *, label: str = "claude_p") -> str:
        cmd = [self.binary, *self.extra_args, "-p", prompt]
        log.debug("ClaudeRunner: %s in %s", shlex.join(cmd), self.project_dir)
        env = os.environ.copy()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.project_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            self.evidence.write(
                "claude_run",
                label=label,
                project=str(self.project_dir),
                ok=False,
                error=f"timeout after {self.timeout}s",
            )
            raise ClaudeRunError(f"claude -p timed out: {exc}") from exc

        if proc.returncode != 0:
            self.evidence.write(
                "claude_run",
                label=label,
                project=str(self.project_dir),
                ok=False,
                error=proc.stderr[:500],
                exitCode=proc.returncode,
            )
            raise ClaudeRunError(
                f"claude -p exit {proc.returncode}: {proc.stderr[:300]}"
            )

        response, tool_uses, result_meta = _parse_stream_json(proc.stdout)
        logged_tool_uses = 0
        for tool_use in tool_uses:
            if self._log_tool_use(tool_use, label=label):
                logged_tool_uses += 1
        self.evidence.write(
            "claude_run",
            label=label,
            project=str(self.project_dir),
            ok=True,
            promptPreview=prompt[:200],
            responsePreview=response[:300],
            responseLen=len(response),
            toolUseCount=logged_tool_uses,
            **result_meta,
        )
        return response

    def _log_tool_use(self, tool_use: dict[str, Any], *, label: str) -> bool:
        name = tool_use["name"]
        if not name.startswith("mcp__happycake__"):
            return False

        args = tool_use.get("input") if isinstance(tool_use.get("input"), dict) else {}
        self.evidence.write(
            "agent_tool_use",
            label=label,
            project=str(self.project_dir),
            tool=name,
            args=args,
        )

        outbound = _OUTBOUND_TOOL_MAP.get(name)
        if outbound is None:
            return True

        channel, recipient_key, body_key = outbound
        self.evidence.write(
            "channel_outbound",
            label=label,
            channel=channel,
            tool=name,
            recipientKey=recipient_key,
            recipient=args.get(recipient_key),
            bodyPreview=_body_preview(args.get(body_key)),
        )
        return True
