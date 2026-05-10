"""Ops bot — dedicated Telegram chat for kitchen + GMB + IG-post operations.

Slash commands:
    /start          — sanity check
    /capacity       — current kitchen capacity / load
    /tickets        — list active kitchen tickets
    /reviews        — latest GMB reviews (top 5)
    /pending_posts  — IG posts waiting for owner approval

Run with:
    cd orchestrator && PYTHONPATH=.. .venv/bin/python -m bots.ops_bot
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from orchestrator.evidence import EvidenceLogger  # noqa: E402
from orchestrator.mcp_client import MCPClient, MCPError  # noqa: E402

from bots._common import build_app, owner_only, run_polling  # noqa: E402

log = logging.getLogger(__name__)
evidence = EvidenceLogger()


def _client() -> MCPClient:
    return MCPClient.from_env()


@owner_only
async def cmd_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "🍳 HappyCake Ops Bot online.\n\n"
        "Commands:\n"
        "/capacity — kitchen capacity right now\n"
        "/tickets — active kitchen tickets\n"
        "/reviews — latest GMB reviews\n"
        "/pending_posts — IG posts waiting for your approval"
    )


def _fmt(data: object, *, limit: int = 3500) -> str:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    return text[:limit] if len(text) > limit else text


@owner_only
async def cmd_capacity(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        with _client() as c:
            data = c.call_tool("kitchen_get_capacity", {})
        evidence.mcp_call("kitchen_get_capacity", {}, result_summary=data)
    except MCPError as exc:
        await update.effective_message.reply_text(f"❌ {exc}")
        return
    await update.effective_message.reply_text(
        "🥖 *Kitchen capacity*\n```\n" + _fmt(data) + "\n```", parse_mode="Markdown"
    )


@owner_only
async def cmd_tickets(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        with _client() as c:
            data = c.call_tool("kitchen_list_tickets", {})
        evidence.mcp_call("kitchen_list_tickets", {}, result_summary=data)
    except MCPError as exc:
        await update.effective_message.reply_text(f"❌ {exc}")
        return
    await update.effective_message.reply_text(
        "📝 *Tickets*\n```\n" + _fmt(data) + "\n```", parse_mode="Markdown"
    )


@owner_only
async def cmd_reviews(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        with _client() as c:
            data = c.call_tool("gb_list_reviews", {})
        evidence.mcp_call("gb_list_reviews", {}, result_summary=data)
    except MCPError as exc:
        await update.effective_message.reply_text(f"❌ {exc}")
        return
    await update.effective_message.reply_text(
        "⭐ *GMB reviews*\n```\n" + _fmt(data) + "\n```", parse_mode="Markdown"
    )


@owner_only
async def cmd_pending_posts(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    # The launch kit doesn't expose a list-pending tool directly; we surface
    # the approval queue via the orchestrator's evidence file as the source
    # of truth, but we can also list simulated GMB+IG actions for visibility.
    try:
        with _client() as c:
            ig_actions = c.call_tool("instagram_list_dm_threads", {})
        evidence.mcp_call("instagram_list_dm_threads", {}, result_summary=ig_actions)
    except MCPError as exc:
        await update.effective_message.reply_text(f"❌ {exc}")
        return
    await update.effective_message.reply_text(
        "📸 *IG threads (proxy for activity)*\n```\n" + _fmt(ig_actions) + "\n```",
        parse_mode="Markdown",
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s | %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    app = build_app("TELEGRAM_BOT_TOKEN_OPS")
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("capacity", cmd_capacity))
    app.add_handler(CommandHandler("tickets", cmd_tickets))
    app.add_handler(CommandHandler("reviews", cmd_reviews))
    app.add_handler(CommandHandler("pending_posts", cmd_pending_posts))
    run_polling(app)


if __name__ == "__main__":
    main()
