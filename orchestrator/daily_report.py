"""Daily report generator — one-shot CLI for the Arai POC.

Lean POC per design doc (`~/.gstack/projects/Jandos22-Arai/jandos-main-design-20260510-014144.md`).

Pipeline:
  1. ``discover_evidence(date)`` globs ``evidence/orchestrator-*.jsonl`` and
     filters events whose ts falls within ``date`` in America/Chicago.
  2. ``summarize(events)`` shells to ``claude -p`` with a baked-in prompt and
     parses a JSON object back. Falls back to a deterministic Python summary
     if the binary is missing, exits non-zero, times out, or returns garbage.
  3. The result is written to ``evidence/daily-<date>.json`` (the agent
     analytics layer — bots read this file directly when answering follow-ups).
  4. With ``--post-telegram``, the digest is posted to the owner via the
     existing ``TelegramNotifier`` with an inline "Open audit" button pointing
     at the orchestrator's tunnel ``GET /audit/<date>`` endpoint.

There is **no in-process JobQueue**. This module is invoked by host cron
(documented in README) or manually for demo: ``python -m
orchestrator.daily_report --date 2026-05-09 --post-telegram``.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import date as date_cls, datetime, time as time_cls
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .claude_runner import _resolve_claude_binary
from .evidence import EvidenceLogger
from .telegram_bot import TelegramNotifier

log = logging.getLogger(__name__)

CT = ZoneInfo("America/Chicago")
UTC = ZoneInfo("UTC")
EVIDENCE_DIR = Path("evidence")

# Files we ignore even though they live in evidence/. These are runtime
# artifacts from other tools (smoke runner, evaluator) that don't follow the
# orchestrator-<run_id>.jsonl shape and would confuse the summarizer.
_IGNORE_GLOBS = ("e2e-smoke-*.json", "self-eval-*", "evaluator-*", "daily-*.json")


def daily_report_path(d: date_cls | str, base_dir: Path = EVIDENCE_DIR) -> Path:
    """Single source of truth for the daily JSON file location.

    Used by the generator (write), the audit endpoint (read), and the bots
    when answering owner follow-ups (read). Importing this helper instead of
    hardcoding the path is the DRY guard called out by /plan-eng-review.
    """
    if isinstance(d, str):
        d = date_cls.fromisoformat(d)
    return base_dir / f"daily-{d.isoformat()}.json"


def _is_orchestrator_jsonl(path: Path) -> bool:
    if not path.name.startswith("orchestrator-"):
        return False
    if path.suffix != ".jsonl":
        return False
    return True


def discover_evidence(d: date_cls, base_dir: Path = EVIDENCE_DIR) -> list[dict[str, Any]]:
    """Return all orchestrator events whose UTC ts maps to ``d`` in CT.

    The window is ``[d 00:00 CT, d 23:59:59 CT]`` translated to UTC. Events
    from other tools (e2e-smoke, self-eval, etc.) are skipped. Malformed
    JSONL lines are logged and dropped — the report should not abort because
    one byte got truncated.
    """
    if not base_dir.exists():
        return []
    start_utc = datetime.combine(d, time_cls.min, tzinfo=CT).astimezone(UTC)
    end_utc = datetime.combine(d, time_cls.max, tzinfo=CT).astimezone(UTC)

    events: list[dict[str, Any]] = []
    for path in sorted(base_dir.iterdir()):
        if not _is_orchestrator_jsonl(path):
            continue
        try:
            with path.open("r", encoding="utf-8") as fh:
                for line_no, raw in enumerate(fh, 1):
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        obj = json.loads(raw)
                    except json.JSONDecodeError as exc:
                        log.warning("skip %s:%d — %s", path.name, line_no, exc)
                        continue
                    ts = obj.get("ts")
                    if not isinstance(ts, str):
                        continue
                    try:
                        when = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
                    except ValueError:
                        continue
                    if start_utc <= when <= end_utc:
                        events.append(obj)
        except OSError as exc:
            log.warning("could not read %s: %s", path.name, exc)
            continue
    return events


_REPORT_PROMPT = """\
You are the Arai daily reporter. The JSON array below contains every
orchestrator event recorded for one business day at Happy Cake US.

Emit a SINGLE JSON object with this exact shape and NOTHING else:

{
  "highlights": ["short owner-readable string", ...],
  "lowlights":  ["short owner-readable string", ...],
  "metrics":    { "totalEvents": <int>, "byKind": {<kind>: <int>, ...}, ... },
  "evidence_refs": [{"runId": "...", "kind": "...", "ts": "..."}, ...]
}

Rules:
- Output JSON only. No prose, no markdown fences, no commentary.
- 2-4 highlights and 2-4 lowlights. Fewer is fine if evidence is sparse.
- Highlights = wins (orders won, fast replies, kitchen on schedule).
- Lowlights = misses (slow replies, rejections, drops, anomalies).
- Each evidence_ref must point to a real event from the input.
- Be specific: name dollar amounts, channels, durations when present.
- Never fabricate. If you don't have the data, omit the bullet.

Evidence (JSON array):
"""


def _deterministic_summary(events: list[dict[str, Any]], reason: str) -> dict[str, Any]:
    """Cheap fallback when the LLM path fails. No narrative judgment.

    Always sets ``llmFallback: true`` so judges (and the audit page) can see
    this row was machine-generated, not LLM-generated.
    """
    by_kind: dict[str, int] = {}
    for ev in events:
        k = str(ev.get("kind", "unknown"))
        by_kind[k] = by_kind.get(k, 0) + 1
    if events:
        highlights = [f"{len(events)} events recorded across {len(by_kind)} kinds"]
        lowlights = [f"LLM summary unavailable ({reason})"]
    else:
        highlights = []
        lowlights = ["No orchestrator events recorded for this date"]
    return {
        "highlights": highlights,
        "lowlights": lowlights,
        "metrics": {"totalEvents": len(events), "byKind": by_kind},
        "evidence_refs": [],
        "llmFallback": True,
        "fallbackReason": reason,
    }


def _strip_markdown_fence(raw: str) -> str:
    raw = raw.strip()
    if not raw.startswith("```"):
        return raw
    # ```json\n...\n``` or ```\n...\n```
    inner = raw[3:]
    if inner.startswith("json"):
        inner = inner[4:]
    inner = inner.lstrip("\n")
    if inner.endswith("```"):
        inner = inner[: -3]
    return inner.strip()


def summarize(
    events: list[dict[str, Any]],
    *,
    claude_binary: str | None = None,
    cwd: Path | None = None,
    timeout_s: int = 90,
) -> dict[str, Any]:
    """Build the day's summary. Calls ``claude -p``; falls back if anything fails.

    ``claude_binary`` and ``cwd`` are injected for testability — the unit
    tests pass a fake binary path that returns canned stdout.
    """
    if not events:
        return _deterministic_summary([], "no events for date")

    binary = claude_binary or _resolve_claude_binary()
    prompt = _REPORT_PROMPT + json.dumps(events, default=str, ensure_ascii=False)

    try:
        proc = subprocess.run(
            [binary, "-p", prompt],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _deterministic_summary(events, f"claude -p timed out after {timeout_s}s")
    except FileNotFoundError:
        return _deterministic_summary(events, f"claude binary not found at {binary}")

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip().splitlines()[-1:]
        tail = stderr[0][:120] if stderr else ""
        return _deterministic_summary(events, f"claude -p exit {proc.returncode}: {tail}")

    try:
        obj = json.loads(_strip_markdown_fence(proc.stdout))
    except json.JSONDecodeError as exc:
        return _deterministic_summary(events, f"claude -p returned non-JSON: {exc}")

    if not isinstance(obj, dict):
        return _deterministic_summary(events, "claude -p returned non-object JSON")

    obj.setdefault("highlights", [])
    obj.setdefault("lowlights", [])
    obj.setdefault("metrics", {"totalEvents": len(events), "byKind": {}})
    obj.setdefault("evidence_refs", [])
    obj.setdefault("llmFallback", False)
    return obj


def format_digest(d: date_cls, summary: dict[str, Any]) -> str:
    """Render the Telegram message body. Pure function — unit-testable."""
    title = d.strftime("%a %b %d, %Y")
    lines = [f"☀️ Daily report — {title}", ""]

    if summary.get("llmFallback"):
        reason = summary.get("fallbackReason") or "unknown"
        lines.append(f"⚠️ LLM summary unavailable ({reason}). Showing deterministic counts.")
        lines.append("")

    highs = summary.get("highlights") or []
    if highs:
        lines.append("Highlights:")
        for h in highs:
            lines.append(f"✅ {h}")
        lines.append("")

    lows = summary.get("lowlights") or []
    if lows:
        lines.append("Lowlights:")
        for low in lows:
            lines.append(f"⚠️ {low}")
        lines.append("")

    metrics = summary.get("metrics") or {}
    total = metrics.get("totalEvents")
    if total is not None:
        lines.append(f"Total events: {total}")

    return "\n".join(lines).rstrip() + "\n"


def post_digest(
    d: date_cls,
    summary: dict[str, Any],
    audit_url: str | None,
    notifier: TelegramNotifier,
) -> None:
    """Send the digest via the existing notifier, with an optional audit button."""
    text = format_digest(d, summary)
    notifier.evidence.owner_msg(
        "daily_report",
        summary=text[:200],
        date=d.isoformat(),
        auditUrl=audit_url,
        llmFallback=bool(summary.get("llmFallback")),
    )
    if not notifier.enabled:
        log.warning("telegram disabled (no token/chat_id) — digest not sent, evidence logged")
        return

    payload: dict[str, Any] = {"chat_id": notifier.chat_id, "text": text}
    if audit_url:
        payload["reply_markup"] = {
            "inline_keyboard": [[{"text": "📊 Open audit", "url": audit_url}]],
        }
    notifier._call("sendMessage", payload)


def generate_daily(
    d: date_cls,
    *,
    base_dir: Path = EVIDENCE_DIR,
    claude_binary: str | None = None,
    cwd: Path | None = None,
    post_telegram: bool = False,
    audit_url_template: str | None = None,
    notifier: TelegramNotifier | None = None,
    evidence: EvidenceLogger | None = None,
) -> dict[str, Any]:
    """End-to-end: discover → summarize → write JSON → optionally post."""
    events = discover_evidence(d, base_dir=base_dir)
    summary = summarize(events, claude_binary=claude_binary, cwd=cwd)
    summary["date"] = d.isoformat()
    summary["generatedAt"] = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    out_path = daily_report_path(d, base_dir=base_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log.info("wrote %s (%d events, llmFallback=%s)", out_path, len(events), summary.get("llmFallback"))

    if post_telegram:
        evidence_logger = evidence or EvidenceLogger()
        n = notifier or TelegramNotifier.from_env(evidence_logger)
        audit_url = None
        if audit_url_template:
            audit_url = audit_url_template.replace("{date}", d.isoformat())
        post_digest(d, summary, audit_url, n)

    return summary


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arai-daily-report")
    parser.add_argument(
        "--date",
        required=True,
        help="ISO date YYYY-MM-DD (interpreted in America/Chicago).",
    )
    parser.add_argument(
        "--evidence-dir",
        default="evidence",
        help="Where to find orchestrator-*.jsonl (default: evidence).",
    )
    parser.add_argument(
        "--post-telegram",
        action="store_true",
        help="Also send the digest to the owner Telegram chat (uses env).",
    )
    parser.add_argument(
        "--audit-url-template",
        default=os.environ.get("ARAI_AUDIT_URL_TEMPLATE"),
        help='URL template for the audit page, e.g. "https://tunnel.example.com/audit/{date}".',
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )

    try:
        d = date_cls.fromisoformat(args.date)
    except ValueError as exc:
        parser.error(f"invalid --date: {exc}")
        return 2  # parser.error exits, but be explicit for static analysis

    base = Path(args.evidence_dir)
    generate_daily(
        d,
        base_dir=base,
        post_telegram=args.post_telegram,
        audit_url_template=args.audit_url_template,
    )
    return 0


if __name__ == "__main__":
    sys.exit(cli())
