"""Marketing bot — dedicated Telegram chat for the $500/mo demand engine.

Slash commands:
    /start          — sanity check
    /budget         — print this month's budget + target effect
    /campaigns      — list active simulated campaigns
    /report         — call marketing_report_to_owner and post the summary
    /run            — kick off the full demand-engine chain (long-running)

Runs the marketing Claude Code project in the background for /run; for
read-only commands it just calls the MCP directly via the orchestrator's
MCPClient.

Run with:
    cd orchestrator && PYTHONPATH=.. .venv/bin/python -m bots.marketing_bot
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

# orchestrator package available because pyproject.toml lives in orchestrator/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from orchestrator.claude_runner import ClaudeRunner  # noqa: E402
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
        "/report — fresh marketing_report_to_owner\n"
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


@owner_only
async def cmd_report(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        with _client() as c:
            report = c.call_tool("marketing_report_to_owner", {})
        evidence.mcp_call("marketing_report_to_owner", {}, result_summary=report)
    except MCPError as exc:
        await update.effective_message.reply_text(f"❌ MCP error: {exc}")
        return
    text = "📋 *Marketing report*\n\n" + json.dumps(report, indent=2)[:3500]
    await update.effective_message.reply_text(text, parse_mode="Markdown")


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
    app = build_app("TELEGRAM_BOT_TOKEN_MARKETING")
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("budget", cmd_budget))
    app.add_handler(CommandHandler("campaigns", cmd_campaigns))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("run", cmd_run))
    run_polling(app)


if __name__ == "__main__":
    main()
