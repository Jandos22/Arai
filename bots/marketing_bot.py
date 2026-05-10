"""Marketing bot — dedicated Telegram chat for the $500/mo demand engine.

Slash commands:
    /start          — sanity check
    /budget         — print this month's budget + target effect
    /campaigns      — list active simulated campaigns
    /report         — call marketing_report_to_owner and post the summary
                      (prefaced with yesterday's daily highlights/lowlights
                       if a daily report exists)
    /digest [date]  — show yesterday's (or any day's) daily report
    /run            — kick off the full demand-engine chain (long-running)

Runs the marketing Claude Code project in the background for /run; for
read-only commands it just calls the MCP directly via the orchestrator's
MCPClient.

Run with:
    cd orchestrator && PYTHONPATH=.. .venv/bin/python -m bots.marketing_bot
"""
from __future__ import annotations

import asyncio
import html
import json
import logging
import sys
from datetime import date as date_cls, datetime, timedelta
from pathlib import Path

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

# orchestrator package available because pyproject.toml lives in orchestrator/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from orchestrator.claude_runner import ClaudeRunner  # noqa: E402
from orchestrator.daily_report import daily_report_path  # noqa: E402
from orchestrator.evidence import EvidenceLogger  # noqa: E402
from orchestrator.mcp_client import MCPClient, MCPError  # noqa: E402

from bots._common import build_app, owner_only, run_polling  # noqa: E402

log = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETING_PROJECT = REPO_ROOT / "agents" / "marketing"

evidence = EvidenceLogger()


def _client() -> MCPClient:
    return MCPClient.from_env()


@owner_only
async def cmd_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "🍰 HappyCake Marketing Bot online.\n\n"
        "Commands:\n"
        "/budget — show the $500/mo constraint\n"
        "/campaigns — list active simulated campaigns\n"
        "/report — fresh marketing_report_to_owner (with yesterday's digest)\n"
        "/digest [date] — show a daily report (defaults to yesterday)\n"
        "/run — kick off full demand-engine chain"
    )


@owner_only
async def cmd_budget(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        with _client() as c:
            data = c.call_tool("marketing_get_budget", {})
        evidence.mcp_call("marketing_get_budget", {}, result_summary=data)
    except MCPError as exc:
        await update.effective_message.reply_text(f"❌ MCP error: {exc}")
        return
    text = (
        f"📊 *Marketing budget*\n\n"
        f"Monthly: ${data.get('monthlyBudgetUsd')}\n"
        f"Target effect: ${data.get('targetEffectUsd')}\n"
        f"Challenge: {data.get('challenge')}"
    )
    await update.effective_message.reply_text(text, parse_mode="Markdown")


@owner_only
async def cmd_campaigns(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        with _client() as c:
            data = c.call_tool("marketing_get_campaign_metrics", {})
        evidence.mcp_call("marketing_get_campaign_metrics", {}, result_summary=data)
    except MCPError as exc:
        await update.effective_message.reply_text(f"❌ MCP error: {exc}")
        return
    text = "📈 *Active campaigns*\n\n```\n" + json.dumps(data, indent=2)[:3500] + "\n```"
    await update.effective_message.reply_text(text, parse_mode="Markdown")


def _daily_preface(target: date_cls) -> str | None:
    """If yesterday's daily report exists, return a short preface block.

    The bot reads the same JSON file the audit endpoint serves — that's the
    "agent analytics layer" in action. No recomputation from raw JSONL.

    Output uses HTML parse mode (not Markdown) so LLM-generated content with
    underscores or asterisks (phone numbers, hashtags, etc.) renders cleanly
    instead of accidentally toggling Markdown italic/bold mode.
    """
    path = daily_report_path(target)
    if not path.exists():
        return None
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    highs = body.get("highlights") or []
    lows = body.get("lowlights") or []
    if not isinstance(highs, list):
        highs = []
    if not isinstance(lows, list):
        lows = []
    if not highs and not lows:
        return None
    lines = [f"<i>From the {html.escape(target.isoformat())} daily report</i>"]
    for h in highs[:3]:
        lines.append(f"✅ {html.escape(str(h))}")
    for low in lows[:3]:
        lines.append(f"⚠️ {html.escape(str(low))}")
    return "\n".join(lines)


@owner_only
async def cmd_report(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        with _client() as c:
            report = c.call_tool("marketing_report_to_owner", {})
        evidence.mcp_call("marketing_report_to_owner", {}, result_summary=report)
    except MCPError as exc:
        await update.effective_message.reply_text(f"❌ MCP error: {exc}")
        return
    yesterday = date_cls.today() - timedelta(days=1)
    preface = _daily_preface(yesterday) or _daily_preface(date_cls.today())
    chunks = []
    if preface:
        chunks.append(preface)
        chunks.append("")
    chunks.append("📋 <b>Marketing report</b>")
    chunks.append("<pre>")
    chunks.append(html.escape(json.dumps(report, indent=2)[:3200]))
    chunks.append("</pre>")
    await update.effective_message.reply_text("\n".join(chunks), parse_mode="HTML")


@owner_only
async def cmd_digest(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Show one day's daily report. ``/digest`` → yesterday; ``/digest 2026-05-09`` → that date."""
    args = ctx.args or []
    if args:
        try:
            target = date_cls.fromisoformat(args[0])
        except ValueError:
            await update.effective_message.reply_text(
                f"❌ Bad date: {args[0]!r}. Use YYYY-MM-DD."
            )
            return
    else:
        target = date_cls.today() - timedelta(days=1)

    path = daily_report_path(target)
    if not path.exists():
        # Fall back to today if yesterday isn't ready yet.
        today = date_cls.today()
        if not args and daily_report_path(today).exists():
            target = today
            path = daily_report_path(today)
        else:
            await update.effective_message.reply_text(
                f"❌ No daily report for {target.isoformat()} yet. "
                f"Run python -m orchestrator.daily_report --date {target.isoformat()} first."
            )
            return

    body = json.loads(path.read_text(encoding="utf-8"))
    highs = body.get("highlights") or []
    lows = body.get("lowlights") or []
    if not isinstance(highs, list):
        highs = []
    if not isinstance(lows, list):
        lows = []

    lines = [f"☀️ <b>Daily report — {html.escape(target.isoformat())}</b>"]
    if body.get("llmFallback"):
        reason = html.escape(str(body.get("fallbackReason") or "unknown"))
        lines.append(f"<i>⚠️ LLM fallback active: {reason}</i>")
    if highs:
        lines.append("")
        lines.append("<b>Highlights:</b>")
        for h in highs:
            lines.append(f"✅ {html.escape(str(h))}")
    if lows:
        lines.append("")
        lines.append("<b>Lowlights:</b>")
        for low in lows:
            lines.append(f"⚠️ {html.escape(str(low))}")
    metrics = body.get("metrics") or {}
    if isinstance(metrics, dict) and metrics.get("totalEvents") is not None:
        lines.append("")
        lines.append(f"<i>Events recorded: {metrics['totalEvents']}</i>")
    text = "\n".join(lines)
    await update.effective_message.reply_text(text[:4000], parse_mode="HTML")


@owner_only
async def cmd_run(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not MARKETING_PROJECT.exists():
        await update.effective_message.reply_text(
            "❌ agents/marketing/ not yet built. T-006 ships it."
        )
        return
    await update.effective_message.reply_text(
        "🍰 Kicking off the demand-engine chain. This takes a few minutes — "
        "I'll post the report when it's ready."
    )
    runner = ClaudeRunner(MARKETING_PROJECT, evidence, timeout=600.0)
    prompt = (
        "Run the full HappyCake demand-engine chain end-to-end against the "
        "happycake MCP. Read budget + sales history + margins, create 2–3 "
        "campaigns, launch, generate leads, route them, adjust, report to "
        "owner. Cite the data. End with a single concise paragraph for the "
        "owner."
    )

    def _run() -> str:
        return runner.run(prompt, label="bot_marketing_run")

    try:
        result = await asyncio.to_thread(_run)
    except Exception as exc:  # noqa: BLE001
        await update.effective_message.reply_text(f"❌ run failed: {exc}")
        return
    await update.effective_message.reply_text(
        "✅ Done.\n\n" + (result[:3500] if result else "(no output)")
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s | %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    app = build_app("TELEGRAM_BOT_TOKEN_MARKETING")
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("budget", cmd_budget))
    app.add_handler(CommandHandler("campaigns", cmd_campaigns))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("digest", cmd_digest))
    app.add_handler(CommandHandler("run", cmd_run))
    run_polling(app)


if __name__ == "__main__":
    main()
