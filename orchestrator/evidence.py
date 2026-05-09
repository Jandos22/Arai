"""Evidence logger — append-only JSONL with token redaction.

Schema documented in ``docs/EVIDENCE-SCHEMA.md``. One file per orchestrator
run, written to ``evidence/orchestrator-<runId>.jsonl``. Designed so judges
can read the file directly OR call ``evaluator_get_evidence_summary`` on the
sandbox side and see consistent shape.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Best-effort token redaction. The tokens look like ``sbc_team_<uuid-ish>``
# but we redact anything that looks like a long opaque secret too.
_TOKEN_PATTERN = re.compile(
    r"(sbc_team_[A-Za-z0-9_\-]+|"
    r"Bearer\s+[A-Za-z0-9_\-\.]{20,}|"
    r"X-Team-Token['\"\s:=]+[A-Za-z0-9_\-]{16,})",
    re.IGNORECASE,
)


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return _TOKEN_PATTERN.sub("[REDACTED]", value)
    if isinstance(value, dict):
        return {k: _redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


@dataclass
class EvidenceLogger:
    """Append JSONL events to a per-run file under ``evidence/``.

    Thread-safe via a single lock — orchestrator is single-threaded but
    we want to be safe if Telegram callbacks land on a worker thread.
    """

    run_id: str = field(default_factory=lambda: f"run-{uuid.uuid4().hex[:8]}")
    base_dir: Path = field(default_factory=lambda: Path("evidence"))
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def path(self) -> Path:
        return self.base_dir / f"orchestrator-{self.run_id}.jsonl"

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def write(self, kind: str, **fields: Any) -> None:
        line = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "runId": self.run_id,
            "kind": kind,
            **_redact(fields),
        }
        body = json.dumps(line, ensure_ascii=False, sort_keys=True)
        with self._lock, self.path.open("a", encoding="utf-8") as fh:
            fh.write(body + "\n")

    # --- common shapes --------------------------------------------------

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

    def event(self, source: str, etype: str, payload: dict[str, Any]) -> None:
        self.write("event", source=source, type=etype, payload=payload)

    def decision(self, agent: str, action: str, rationale: str, **extra: Any) -> None:
        self.write(
            "decision",
            agent=agent,
            action=action,
            rationale=rationale,
            **extra,
        )

    def owner_msg(self, kind: str, summary: str, **extra: Any) -> None:
        self.write("owner_msg", subkind=kind, summary=summary, **extra)


def default_logger() -> EvidenceLogger:
    """Convenience for handlers that share a single logger via env."""
    run_id = os.environ.get("ARAI_RUN_ID")
    if run_id:
        return EvidenceLogger(run_id=run_id)
    return EvidenceLogger()
