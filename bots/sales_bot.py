"""Sales bot — dedicated Telegram chat for inbound channel operations.

This bot is **read-only** for the owner: it surfaces what the orchestrator's
sales agent has been doing on WhatsApp + Instagram, plus a few utility
commands. Actual replies to customers are handled by the orchestrator
calling `claude -p` in agents/sales/, NOT by this bot.

Slash commands:
    /start          — sanity check
    /menu           — show today's catalog
    /threads        — recent WhatsApp + IG threads
    /orders         — recent POS orders
    /pos            — POS summary

Run with:
    cd orchestrator && PYTHONPATH=.. .venv/bin/python -m bots.sales_bot
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


def _fmt(data: object, *, limit: int = 3500) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)[:limit]


@owner_only
async def cmd_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "🛍️ HappyCake Sales Bot online.\n\n"
        "Read-only view of what your sales agent is doing on customer channels.\n\n"
        "/menu — today's catalog\n"
        "/threads — recent WA + IG threads\n"
        "/orders — recent POS orders\n"
        "/pos — POS summary"
    )


@owner_only
async def cmd_menu(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        with _client() as c:
            data = c.call_tool("square_list_catalog", {})
    except MCPError as exc:
        await update.effective_message.reply_text(f"❌ {exc}")
        return
    await update.effective_message.reply_text(
        "🍰 *Catalog*\n```\n" + _fmt(data) + "\n```", parse_mode="Markdown"
    )


@owner_only
async def cmd_threads(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        with _client() as c:
            wa = c.call_tool("whatsapp_list_threads", {})
            ig = c.call_tool("instagram_list_dm_threads", {})
    except MCPError as exc:
        await update.effective_message.reply_text(f"❌ {exc}")
        return
    await update.effective_message.reply_text(
        f"💬 *WhatsApp*\n```\n{_fmt(wa, limit=1500)}\n```\n\n"
        f"📸 *Instagram*\n```\n{_fmt(ig, limit=1500)}\n```",
        parse_mode="Markdown",
    )


@owner_only
async def cmd_orders(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        with _client() as c:
            data = c.call_tool("square_recent_orders", {"limit": 10})
    except MCPError as exc:
        await update.effective_message.reply_text(f"❌ {exc}")
        return
    await update.effective_message.reply_text(
        "🧾 *Recent orders*\n```\n" + _fmt(data) + "\n```", parse_mode="Markdown"
    )


@owner_only
async def cmd_pos(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        with _client() as c:
            data = c.call_tool("square_get_pos_summary", {})
    except MCPError as exc:
        await update.effective_message.reply_text(f"❌ {exc}")
        return
    await update.effective_message.reply_text(
        "📊 *POS summary*\n```\n" + _fmt(data) + "\n```", parse_mode="Markdown"
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s | %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    app = build_app("TELEGRAM_BOT_TOKEN_SALES")
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("threads", cmd_threads))
    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(CommandHandler("pos", cmd_pos))
    run_polling(app)


if __name__ == "__main__":
    main()
