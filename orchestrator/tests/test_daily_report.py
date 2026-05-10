"""Unit tests for ``orchestrator.daily_report``.

Covers paths 1-12 of the test plan
(``~/.gstack/projects/Jandos22-Arai/jandos-main-eng-review-test-plan-20260510-021302.md``)
plus the critical-gap 17th test (``claude -p`` returns non-JSON, fallback engages).

Audit-endpoint tests (paths 13-15) live in ``test_webhook_server.py``.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import date as date_cls, datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from orchestrator import daily_report as dr
from orchestrator.daily_report import (
    EVIDENCE_DIR,
    cli,
    daily_report_path,
    discover_evidence,
    format_digest,
    generate_daily,
    post_digest,
    summarize,
)
from orchestrator.evidence import EvidenceLogger
from orchestrator.telegram_bot import TelegramNotifier


# ---------------------------------------------------------------- helpers


def _mk_event(ts_utc: str, kind: str = "event", **extra: Any) -> str:
    """Build one JSONL row matching the orchestrator EvidenceLogger shape."""
    obj = {"ts": ts_utc, "runId": "run-test", "kind": kind, **extra}
    return json.dumps(obj, sort_keys=True) + "\n"


def _write_run_file(tmp_path: Path, name: str, lines: list[str]) -> Path:
    p = tmp_path / name
    p.write_text("".join(lines), encoding="utf-8")
    return p


@pytest.fixture
def evidence_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An isolated evidence/ directory per test, with cwd pointed at it."""
    base = tmp_path / "evidence"
    base.mkdir()
    monkeypatch.chdir(tmp_path)
    return base


# ---------------------------------------------------------------- daily_report_path


def test_daily_report_path_str_input() -> None:
    assert daily_report_path("2026-05-09") == Path("evidence/daily-2026-05-09.json")


def test_daily_report_path_date_input(tmp_path: Path) -> None:
    out = daily_report_path(date_cls(2026, 5, 9), base_dir=tmp_path)
    assert out == tmp_path / "daily-2026-05-09.json"


# ---------------------------------------------------------------- discover_evidence (paths 1-4)


def test_discover_empty_dir(evidence_dir: Path) -> None:
    """Path #1 — empty evidence dir returns []."""
    assert discover_evidence(date_cls(2026, 5, 9), base_dir=evidence_dir) == []


def test_discover_filters_by_ts_within_day_in_ct(evidence_dir: Path) -> None:
    """Path #2 — ts window is [d 00:00 CT, d 23:59:59 CT] translated to UTC.

    For 2026-05-09 in CT (UTC-5 during DST), the UTC window is
    2026-05-09T05:00Z ..  2026-05-10T04:59:59Z.
    """
    _write_run_file(
        evidence_dir,
        "orchestrator-run-a.jsonl",
        [
            _mk_event("2026-05-09T04:59:59Z", kind="too_early"),     # before CT window
            _mk_event("2026-05-09T05:00:00Z", kind="early_in_window"),  # CT 00:00
            _mk_event("2026-05-09T18:00:00Z", kind="midday"),
            _mk_event("2026-05-10T04:59:59Z", kind="late_in_window"),   # CT 23:59:59
            _mk_event("2026-05-10T05:00:00Z", kind="too_late"),         # next day
        ],
    )
    events = discover_evidence(date_cls(2026, 5, 9), base_dir=evidence_dir)
    kinds = [e["kind"] for e in events]
    assert kinds == ["early_in_window", "midday", "late_in_window"]


def test_discover_ignores_non_orchestrator_files(evidence_dir: Path) -> None:
    """Path #3 — e2e-smoke and self-eval files are not orchestrator-*.jsonl, skip them."""
    _write_run_file(
        evidence_dir,
        "orchestrator-run-real.jsonl",
        [_mk_event("2026-05-09T18:00:00Z", kind="real_event")],
    )
    (evidence_dir / "e2e-smoke-20260509T180000Z.json").write_text("{\"this\":\"json\"}\n")
    (evidence_dir / "self-eval-20260509T180000Z.json").write_text("{\"also\":\"json\"}\n")
    (evidence_dir / "evaluator-preview-20260509.json").write_text("{}\n")
    (evidence_dir / "daily-2026-05-08.json").write_text("{}\n")
    events = discover_evidence(date_cls(2026, 5, 9), base_dir=evidence_dir)
    assert [e["kind"] for e in events] == ["real_event"]


def test_discover_skips_malformed_jsonl_line(
    evidence_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Path #4 — one bad line doesn't tank the whole run."""
    _write_run_file(
        evidence_dir,
        "orchestrator-run-mixed.jsonl",
        [
            _mk_event("2026-05-09T18:00:00Z", kind="ok_before"),
            "{not valid json\n",
            _mk_event("2026-05-09T18:01:00Z", kind="ok_after"),
        ],
    )
    with caplog.at_level("WARNING"):
        events = discover_evidence(date_cls(2026, 5, 9), base_dir=evidence_dir)
    assert [e["kind"] for e in events] == ["ok_before", "ok_after"]
    assert any("orchestrator-run-mixed.jsonl" in r.message for r in caplog.records)


def test_discover_skips_event_with_invalid_ts(evidence_dir: Path) -> None:
    """Defensive: a row with a non-ISO ts is dropped, not crashed on."""
    _write_run_file(
        evidence_dir,
        "orchestrator-run-bad-ts.jsonl",
        [
            json.dumps({"ts": "not-a-timestamp", "kind": "junk"}) + "\n",
            json.dumps({"ts": 12345, "kind": "wrong_type"}) + "\n",
            _mk_event("2026-05-09T18:00:00Z", kind="ok"),
        ],
    )
    events = discover_evidence(date_cls(2026, 5, 9), base_dir=evidence_dir)
    assert [e["kind"] for e in events] == ["ok"]


# ---------------------------------------------------------------- summarize (paths 5-7 + critical gap)


def _fake_claude(stdout: str, returncode: int = 0, stderr: str = "") -> Any:
    """Build a stub for subprocess.run that returns canned output."""

    class _Result:
        def __init__(self) -> None:
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    def runner(*_args: Any, **_kwargs: Any) -> Any:
        return _Result()

    return runner


def test_summarize_empty_events_returns_deterministic() -> None:
    """Path #5 — empty events skip the LLM entirely and return a 'no events' summary."""
    out = summarize([])
    assert out["llmFallback"] is True
    assert out["lowlights"] == ["No orchestrator events recorded for this date"]
    assert out["metrics"] == {"totalEvents": 0, "byKind": {}}


def test_summarize_happy_path_with_claude_mock() -> None:
    """Path #6 — claude -p returns valid JSON, summarize parses it through."""
    canned = json.dumps(
        {
            "highlights": ["$847 sold across 12 orders"],
            "lowlights": ["3 messages waited >2h"],
            "metrics": {"totalEvents": 7, "byKind": {"event": 7}},
            "evidence_refs": [{"runId": "run-x", "kind": "event", "ts": "2026-05-09T18:00:00Z"}],
        }
    )
    events = [{"ts": "2026-05-09T18:00:00Z", "kind": "event", "runId": "run-x"}]
    with patch.object(subprocess, "run", _fake_claude(canned)):
        out = summarize(events, claude_binary="/fake/claude")
    assert out["highlights"] == ["$847 sold across 12 orders"]
    assert out["llmFallback"] is False


def test_summarize_strips_markdown_fence() -> None:
    """claude sometimes wraps JSON in ```json fences. We tolerate it."""
    canned = "```json\n{\"highlights\":[\"x\"],\"lowlights\":[],\"metrics\":{},\"evidence_refs\":[]}\n```\n"
    events = [{"ts": "2026-05-09T18:00:00Z", "kind": "event"}]
    with patch.object(subprocess, "run", _fake_claude(canned)):
        out = summarize(events, claude_binary="/fake/claude")
    assert out["highlights"] == ["x"]
    assert out["llmFallback"] is False


def test_summarize_claude_nonzero_exit_falls_back() -> None:
    """Path #7 — claude -p exits non-zero, deterministic summary kicks in."""
    events = [{"ts": "2026-05-09T18:00:00Z", "kind": "event"}]
    with patch.object(subprocess, "run", _fake_claude("", returncode=1, stderr="boom")):
        out = summarize(events, claude_binary="/fake/claude")
    assert out["llmFallback"] is True
    assert "exit 1" in out["fallbackReason"]
    assert out["metrics"]["totalEvents"] == 1


def test_summarize_claude_timeout_falls_back() -> None:
    """A timeout is the most realistic LLM failure mode."""
    events = [{"ts": "2026-05-09T18:00:00Z", "kind": "event"}]

    def _timeout(*_args: Any, **_kwargs: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd="claude", timeout=1)

    with patch.object(subprocess, "run", _timeout):
        out = summarize(events, claude_binary="/fake/claude", timeout_s=1)
    assert out["llmFallback"] is True
    assert "timed out" in out["fallbackReason"]


def test_summarize_claude_binary_missing_falls_back() -> None:
    """If the binary path doesn't exist, we still return a usable summary."""
    events = [{"ts": "2026-05-09T18:00:00Z", "kind": "event"}]

    def _missing(*_args: Any, **_kwargs: Any) -> Any:
        raise FileNotFoundError("claude")

    with patch.object(subprocess, "run", _missing):
        out = summarize(events, claude_binary="/no/such/claude")
    assert out["llmFallback"] is True
    assert "not found" in out["fallbackReason"]


def test_summarize_claude_returns_non_json_falls_back() -> None:
    """Path #17 (CRITICAL GAP) — LLM hallucinates non-JSON output. We must not crash."""
    events = [{"ts": "2026-05-09T18:00:00Z", "kind": "event"}]
    with patch.object(subprocess, "run", _fake_claude("Sure! Here's your report:\n- great day")):
        out = summarize(events, claude_binary="/fake/claude")
    assert out["llmFallback"] is True
    assert "non-JSON" in out["fallbackReason"]


def test_summarize_claude_returns_non_object_json_falls_back() -> None:
    """Defensive: claude returns a JSON list, not the expected object."""
    events = [{"ts": "2026-05-09T18:00:00Z", "kind": "event"}]
    with patch.object(subprocess, "run", _fake_claude("[1,2,3]")):
        out = summarize(events, claude_binary="/fake/claude")
    assert out["llmFallback"] is True
    assert "non-object" in out["fallbackReason"]


# ---------------------------------------------------------------- post_digest (paths 8-9)


@pytest.fixture
def evidence_logger(tmp_path: Path) -> EvidenceLogger:
    return EvidenceLogger(base_dir=tmp_path / "evidence")


def test_post_digest_no_telegram_env_logs_evidence_only(
    evidence_logger: EvidenceLogger,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Path #8 (revised) — when Telegram env vars are missing, notifier silently
    no-ops but evidence row is still written. (TelegramNotifier.from_env never
    returns None — see telegram_bot.py:55. Test plan path #8 originally said
    'exit 2'; that turned out to be wrong once we read the code.)
    """
    notifier = TelegramNotifier(token=None, chat_id=None, evidence=evidence_logger)
    summary = {"highlights": ["x"], "lowlights": [], "metrics": {}, "evidence_refs": []}
    with caplog.at_level("WARNING"):
        post_digest(date_cls(2026, 5, 9), summary, audit_url=None, notifier=notifier)
    assert any("telegram disabled" in r.message.lower() for r in caplog.records)
    # evidence row written
    body = evidence_logger.path.read_text(encoding="utf-8")
    assert "daily_report" in body


def test_post_digest_happy_path_calls_telegram(
    evidence_logger: EvidenceLogger,
) -> None:
    """Path #9 — token + chat_id present → ``_call('sendMessage', ...)`` fires
    with the expected payload, including the audit-URL inline keyboard."""
    notifier = TelegramNotifier(token="tok", chat_id="123", evidence=evidence_logger)
    summary = {
        "highlights": ["$847 sold"],
        "lowlights": ["slow IG replies"],
        "metrics": {"totalEvents": 7},
        "evidence_refs": [],
    }
    captured: dict[str, Any] = {}

    def _capture(method: str, payload: dict[str, Any]) -> dict[str, Any]:
        captured["method"] = method
        captured["payload"] = payload
        return {"ok": True}

    with patch.object(notifier, "_call", _capture):
        post_digest(
            date_cls(2026, 5, 9),
            summary,
            audit_url="https://tunnel.example/audit/2026-05-09",
            notifier=notifier,
        )

    assert captured["method"] == "sendMessage"
    assert captured["payload"]["chat_id"] == "123"
    assert "Daily report" in captured["payload"]["text"]
    assert "$847 sold" in captured["payload"]["text"]
    keyboard = captured["payload"]["reply_markup"]["inline_keyboard"]
    assert keyboard[0][0]["url"] == "https://tunnel.example/audit/2026-05-09"


# ---------------------------------------------------------------- format_digest


def test_format_digest_includes_highlights_and_lowlights() -> None:
    summary = {
        "highlights": ["a win"],
        "lowlights": ["a miss"],
        "metrics": {"totalEvents": 3},
    }
    out = format_digest(date_cls(2026, 5, 9), summary)
    assert "Daily report" in out
    assert "✅ a win" in out
    assert "⚠️ a miss" in out
    assert "Total events: 3" in out


def test_format_digest_flags_llm_fallback() -> None:
    summary = {
        "highlights": [],
        "lowlights": [],
        "metrics": {},
        "llmFallback": True,
        "fallbackReason": "timed out after 90s",
    }
    out = format_digest(date_cls(2026, 5, 9), summary)
    assert "LLM summary unavailable" in out
    assert "timed out" in out


# ---------------------------------------------------------------- cli (paths 10-12)


def test_cli_valid_date_returns_zero(
    evidence_dir: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Path #10 — clean CLI invocation writes the daily JSON and exits 0."""
    _write_run_file(
        evidence_dir,
        "orchestrator-run-cli.jsonl",
        [_mk_event("2026-05-09T18:00:00Z", kind="event")],
    )

    # Make summarize fast/deterministic by forcing the empty-events fallback path
    # (no claude binary available in test env).
    def _fast_summary(events: list[dict[str, Any]], **_kw: Any) -> dict[str, Any]:
        return {
            "highlights": ["test"],
            "lowlights": [],
            "metrics": {"totalEvents": len(events)},
            "evidence_refs": [],
            "llmFallback": False,
        }

    monkeypatch.setattr(dr, "summarize", _fast_summary)
    rc = cli(["--date", "2026-05-09", "--evidence-dir", str(evidence_dir)])
    assert rc == 0
    out_path = evidence_dir / "daily-2026-05-09.json"
    assert out_path.exists()
    body = json.loads(out_path.read_text())
    assert body["date"] == "2026-05-09"
    assert body["highlights"] == ["test"]


def test_cli_invalid_date_format_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    """Path #11 — invalid --date triggers argparse error → SystemExit(2)."""
    with pytest.raises(SystemExit) as exc:
        cli(["--date", "2026-13-99"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "invalid --date" in err


def test_cli_post_telegram_flag_routes_to_post_digest(
    evidence_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Path #12 — --post-telegram makes generate_daily call post_digest."""
    _write_run_file(
        evidence_dir,
        "orchestrator-run-x.jsonl",
        [_mk_event("2026-05-09T18:00:00Z", kind="event")],
    )

    def _fast_summary(events: list[dict[str, Any]], **_kw: Any) -> dict[str, Any]:
        return {
            "highlights": [],
            "lowlights": [],
            "metrics": {"totalEvents": len(events)},
            "evidence_refs": [],
            "llmFallback": False,
        }

    monkeypatch.setattr(dr, "summarize", _fast_summary)
    calls: list[tuple[Any, ...]] = []

    def _capture_post(d: date_cls, summary: dict[str, Any], audit_url: str | None, notifier: Any) -> None:
        calls.append((d, summary, audit_url))

    monkeypatch.setattr(dr, "post_digest", _capture_post)

    rc = cli(
        [
            "--date",
            "2026-05-09",
            "--evidence-dir",
            str(evidence_dir),
            "--post-telegram",
            "--audit-url-template",
            "https://tunnel.example/audit/{date}",
        ]
    )
    assert rc == 0
    assert len(calls) == 1
    assert calls[0][0] == date_cls(2026, 5, 9)
    assert calls[0][2] == "https://tunnel.example/audit/2026-05-09"


def test_cli_no_post_telegram_skips_telegram(
    evidence_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without --post-telegram, post_digest is never called."""
    _write_run_file(
        evidence_dir,
        "orchestrator-run-y.jsonl",
        [_mk_event("2026-05-09T18:00:00Z", kind="event")],
    )

    def _fast_summary(events: list[dict[str, Any]], **_kw: Any) -> dict[str, Any]:
        return {"highlights": [], "lowlights": [], "metrics": {}, "evidence_refs": [], "llmFallback": False}

    monkeypatch.setattr(dr, "summarize", _fast_summary)

    def _should_not_be_called(*_a: Any, **_kw: Any) -> None:
        raise AssertionError("post_digest called without --post-telegram")

    monkeypatch.setattr(dr, "post_digest", _should_not_be_called)
    rc = cli(["--date", "2026-05-09", "--evidence-dir", str(evidence_dir)])
    assert rc == 0


# ---------------------------------------------------------------- generate_daily integration


def test_generate_daily_writes_json_with_metadata(
    evidence_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_run_file(
        evidence_dir,
        "orchestrator-run-int.jsonl",
        [_mk_event("2026-05-09T18:00:00Z", kind="event")],
    )

    def _fast_summary(events: list[dict[str, Any]], **_kw: Any) -> dict[str, Any]:
        return {"highlights": ["x"], "lowlights": [], "metrics": {}, "evidence_refs": [], "llmFallback": False}

    monkeypatch.setattr(dr, "summarize", _fast_summary)
    summary = generate_daily(date_cls(2026, 5, 9), base_dir=evidence_dir)
    assert summary["date"] == "2026-05-09"
    assert "generatedAt" in summary
    out_path = daily_report_path("2026-05-09", base_dir=evidence_dir)
    assert out_path.exists()
