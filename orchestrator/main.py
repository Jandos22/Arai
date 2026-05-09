"""Orchestrator entry point.

Usage::

    cd orchestrator
    uv run python -m orchestrator.main --scenario launch-day-revenue-engine
    uv run python -m orchestrator.main --dry-run    # no MCP, no Telegram

Reads ``.env.local`` from the repo root. Connects to the sandbox MCP, starts
a scenario, drains events, dispatches them, writes evidence, and prints a
summary at the end.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from . import handlers
from .claude_runner import ClaudeRunner
from .dispatcher import HandlerContext, Handler, make_dispatcher
from .evidence import EvidenceLogger
from .mcp_client import MCPClient, MCPError
from .scenario import ScenarioRunner
from .telegram_bot import TelegramNotifier

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_env_local() -> None:
    """Best-effort dotenv loader (no hard dep on python-dotenv at runtime)."""
    env_file = REPO_ROOT / ".env.local"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def build_routing_table() -> dict[str, Handler]:
    """Map ``channel:type`` keys to handler functions.

    The dispatcher also tries ``channel:*`` and ``*`` fallbacks.
    """
    return {
        # WhatsApp
        "whatsapp:inbound_message": handlers.whatsapp.handle,
        "whatsapp:message": handlers.whatsapp.handle,
        "whatsapp:*": handlers.whatsapp.handle,
        # Instagram
        "instagram:dm": handlers.instagram.handle,
        "instagram:comment": handlers.instagram.handle,
        "instagram:*": handlers.instagram.handle,
        # GMB
        "gmb:review_received": handlers.gmb.handle,
        "gmb:*": handlers.gmb.handle,
        # Kitchen
        "kitchen:ticket_pending_owner_approval": handlers.kitchen.handle,
        "kitchen:*": handlers.kitchen.handle,
        # Square / POS
        "square:walk_in_order": handlers.square.handle,
        "square:*": handlers.square.handle,
        # Marketing trigger
        "marketing:tick": handlers.marketing.handle,
        "marketing:*": handlers.marketing.handle,
    }


def build_runners(evidence: EvidenceLogger) -> tuple[ClaudeRunner | None, ClaudeRunner | None, ClaudeRunner | None]:
    """Construct per-agent ClaudeRunners if their project dirs exist."""
    sales_dir = REPO_ROOT / "agents" / "sales"
    ops_dir = REPO_ROOT / "agents" / "ops"
    marketing_dir = REPO_ROOT / "agents" / "marketing"
    sales = ClaudeRunner(sales_dir, evidence) if sales_dir.exists() else None
    ops = ClaudeRunner(ops_dir, evidence) if ops_dir.exists() else None
    marketing = ClaudeRunner(marketing_dir, evidence) if marketing_dir.exists() else None
    return sales, ops, marketing


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arai-orchestrator")
    parser.add_argument("--scenario", default="launch-day-revenue-engine")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-events", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't connect to MCP — just exercise the wiring.")
    parser.add_argument("--list-scenarios", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    load_env_local()

    evidence = EvidenceLogger()
    log.info("evidence file: %s", evidence.path)

    if args.dry_run:
        evidence.write("dry_run", note="orchestrator wiring loaded, no MCP/Telegram calls made")
        log.info("dry-run OK — wiring intact, no live calls")
        return 0

    try:
        client = MCPClient.from_env()
    except MCPError as exc:
        log.error("MCP client init failed: %s", exc)
        return 2

    if args.list_scenarios:
        runner = ScenarioRunner(client, evidence, lambda _e: None)
        scenarios = runner.list_scenarios()
        print(json.dumps(scenarios, indent=2))
        return 0

    sales, ops, marketing = build_runners(evidence)
    notifier = TelegramNotifier.from_env(evidence)
    ctx = HandlerContext(
        client=client,
        evidence=evidence,
        sales_runner=sales,
        ops_runner=ops,
        marketing_runner=marketing,
        telegram_notifier=notifier,
    )
    dispatch = make_dispatcher(ctx, build_routing_table())
    runner = ScenarioRunner(client, evidence, dispatch)

    log.info("starting scenario %s", args.scenario)
    runner.start(args.scenario, seed=args.seed)
    notifier.notify(f"🍰 Arai orchestrator started — scenario: {args.scenario}")

    try:
        summary = runner.run(max_events=args.max_events)
    except KeyboardInterrupt:
        log.info("interrupted")
        summary = runner.summary()

    log.info("scenario summary: %s", summary)
    notifier.notify(
        "🍰 Arai orchestrator finished. Processed events: "
        f"{summary.get('processedEvents') or summary.get('deliveredEvents') or '?'}."
    )
    print(json.dumps({"runId": evidence.run_id, "summary": summary}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(cli())
