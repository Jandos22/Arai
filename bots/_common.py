"""Shared Telegram bot scaffolding for dedicated per-agent bots.

Each agent (marketing, ops, sales) optionally exposes a dedicated bot so
the owner has one slash-command-driven chat per role. This is on top of
the orchestrator-attached owner bot (which only handles approvals).

The brief explicitly allows "one bot per agent" — multi-bot UI is a
nice-to-have for owner convenience, not core scoring.

Usage:
    from bots._common import build_app, run_polling, owner_only
"""
from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable
from functools import wraps
from pathlib import Path

# Lazy import so missing python-telegram-bot doesn't crash the whole repo.
try:
    from telegram import Update
    from telegram.ext import Application, ApplicationBuilder, ContextTypes
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "python-telegram-bot not installed. Run from orchestrator/.venv "
        "or `pip install python-telegram-bot>=21.6`."
    ) from exc

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_env_local() -> None:
    env = REPO_ROOT / ".env.local"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


_load_env_local()


def build_app(token_env: str) -> Application:
    token = os.environ.get(token_env)
    if not token:
        raise SystemExit(
            f"{token_env} missing from .env.local. Set it to a valid Telegram "
            "bot token (BotFather), then re-run."
        )
    return ApplicationBuilder().token(token).build()


def run_polling(app: Application) -> None:
    log.info("Starting polling for %s", app.bot.token[:8] + "...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


def owner_only(
    fn: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]:
    """Decorator: only respond if the chat_id matches TELEGRAM_OWNER_CHAT_ID."""

    @wraps(fn)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        owner = os.environ.get("TELEGRAM_OWNER_CHAT_ID")
        if owner and update.effective_chat and str(update.effective_chat.id) != str(owner):
            if update.effective_message:
                await update.effective_message.reply_text(
                    "This bot is private to the HappyCake owner."
                )
            return
        await fn(update, ctx)

    return wrapper
