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
from .env import load_env
from .evidence import EvidenceLogger
from .mcp_client import MCPClient, MCPError
from .scenario import ScenarioRunner
from .telegram_bot import TelegramNotifier
from .webhook_server import serve_webhooks

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_env_local() -> None:
    """Best-effort env loader for repo-local and multi-worktree runs."""
    load_env(REPO_ROOT)


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
        # GMB / Google Business (sandbox uses both channel names)
        "gmb:review_received": handlers.gmb.handle,
        "gmb:*": handlers.gmb.handle,
        "gbusiness:review": handlers.gmb.handle,
        "gbusiness:*": handlers.gmb.handle,
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


def build_handler_context(client: MCPClient, evidence: EvidenceLogger) -> HandlerContext:
    """Build the shared handler dependency bag."""
    sales, ops, marketing = build_runners(evidence)
    notifier = TelegramNotifier.from_env(evidence)
    return HandlerContext(
        client=client,
        evidence=evidence,
        sales_runner=sales,
        ops_runner=ops,
        marketing_runner=marketing,
        telegram_notifier=notifier,
    )


def register_webhooks(client: MCPClient, evidence: EvidenceLogger, base_url: str) -> dict[str, Any]:
    """Register Cloudflare/ngrok webhook URLs with the sandbox MCP."""
    root = base_url.rstrip("/")
    targets = {
        "whatsapp_register_webhook": {"url": f"{root}/webhooks/whatsapp"},
        "instagram_register_webhook": {"url": f"{root}/webhooks/instagram"},
    }
    results: dict[str, Any] = {}
    for tool, args in targets.items():
        try:
            result = client.call_tool(tool, args)
        except MCPError as exc:
            evidence.mcp_call(tool, args=args, ok=False, error=str(exc))
            raise
        evidence.mcp_call(tool, args=args, result_summary=result)
        results[tool] = result
    return results


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arai-orchestrator")
    parser.add_argument("--scenario", default="launch-day-revenue-engine")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-events", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't connect to MCP — just exercise the wiring.")
    parser.add_argument("--list-scenarios", action="store_true")
    parser.add_argument("--webhook-server", action="store_true",
                        help="Serve local WhatsApp/Instagram webhook endpoints.")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Host for --webhook-server. Defaults to 127.0.0.1.")
    parser.add_argument("--port", type=int, default=8787,
                        help="Port for --webhook-server. Defaults to 8787.")
    parser.add_argument("--register-webhooks",
                        help="Register <base-url>/webhooks/* with the sandbox MCP.")
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

    if args.register_webhooks:
        try:
            results = register_webhooks(client, evidence, args.register_webhooks)
        except MCPError as exc:
            log.error("webhook registration failed: %s", exc)
            return 2
        print(json.dumps({"runId": evidence.run_id, "registered": results}, indent=2))
        return 0

    if args.list_scenarios:
        runner = ScenarioRunner(client, evidence, lambda _e: None)
        scenarios = runner.list_scenarios()
        print(json.dumps(scenarios, indent=2))
        return 0

    ctx = build_handler_context(client, evidence)
    dispatch = make_dispatcher(ctx, build_routing_table())

    if args.webhook_server:
        evidence.write(
            "webhook_server_start",
            host=args.host,
            port=args.port,
        )
        try:
            serve_webhooks(args.host, args.port, dispatch, evidence)
        except KeyboardInterrupt:
            log.info("webhook server interrupted")
        return 0

    runner = ScenarioRunner(client, evidence, dispatch)

    log.info("starting scenario %s", args.scenario)
    runner.start(args.scenario, seed=args.seed)
    ctx.telegram_notifier.notify(f"🍰 Arai orchestrator started — scenario: {args.scenario}")

    try:
        summary = runner.run(max_events=args.max_events)
    except KeyboardInterrupt:
        log.info("interrupted")
        summary = runner.summary()

    log.info("scenario summary: %s", summary)
    ctx.telegram_notifier.notify(
        "🍰 Arai orchestrator finished. Processed events: "
        f"{summary.get('processedEvents') or summary.get('deliveredEvents') or '?'}."
    )
    print(json.dumps({"runId": evidence.run_id, "summary": summary}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(cli())
