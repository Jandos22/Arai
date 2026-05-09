"""World-scenario driver.

The launch kit ships a ``launch-day-revenue-engine`` scenario (480 sim-min,
seed 9100510) plus a ``weekend-capacity-crunch`` scenario. The evaluator
itself runs scenarios against our MCP audit log, so our orchestrator's
inner loop should be the same loop the eval drives.

Usage::

    runner = ScenarioRunner(client, evidence, dispatcher)
    runner.start("launch-day-revenue-engine")
    runner.run(max_events=200)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable

from .evidence import EvidenceLogger
from .mcp_client import MCPClient

log = logging.getLogger(__name__)

# How long to back off when world_next_event returns nothing yet.
NO_EVENT_SLEEP_S = 1.0
# Max consecutive empty polls before we declare the scenario finished.
EMPTY_POLL_LIMIT = 6


@dataclass
class ScenarioRunner:
    client: MCPClient
    evidence: EvidenceLogger
    dispatch: Callable[[dict[str, Any]], None]

    def list_scenarios(self) -> list[dict[str, Any]]:
        result = self.client.call_tool("world_get_scenarios", {})
        return result.get("scenarios", []) if isinstance(result, dict) else result

    def start(self, scenario_id: str, seed: int | None = None) -> dict[str, Any]:
        args: dict[str, Any] = {"scenarioId": scenario_id}
        if seed is not None:
            args["seed"] = seed
        result = self.client.call_tool("world_start_scenario", args)
        self.evidence.mcp_call("world_start_scenario", args, result_summary=result)
        log.info("Scenario %s started", scenario_id)
        return result if isinstance(result, dict) else {}

    def next_event(self) -> dict[str, Any] | None:
        result = self.client.call_tool("world_next_event", {})
        if not result:
            return None
        # Some MCP servers return ``{event: {...}}``, others return the event
        # at top level. Be liberal about what we accept.
        if isinstance(result, dict):
            if "event" in result and isinstance(result["event"], dict):
                return result["event"]
            if "type" in result or "channel" in result:
                return result
            if "events" in result and result["events"]:
                # If we ever get a batch, queue it implicitly via repeated calls.
                return result["events"][0]
        return None

    def summary(self) -> dict[str, Any]:
        result = self.client.call_tool("world_get_scenario_summary", {})
        return result if isinstance(result, dict) else {}

    def run(self, max_events: int = 200) -> dict[str, Any]:
        empty_streak = 0
        processed = 0
        for _ in range(max_events):
            event = self.next_event()
            if event is None:
                empty_streak += 1
                if empty_streak >= EMPTY_POLL_LIMIT:
                    log.info("No new events in %d polls — scenario complete", empty_streak)
                    break
                time.sleep(NO_EVENT_SLEEP_S)
                continue
            empty_streak = 0
            processed += 1
            self.evidence.event(
                source=event.get("channel", "world"),
                etype=event.get("type", "unknown"),
                payload=event,
            )
            try:
                self.dispatch(event)
            except Exception as exc:  # noqa: BLE001
                log.exception("dispatch failed: %s", exc)
                self.evidence.write(
                    "dispatch_error",
                    event=event,
                    error=str(exc),
                )
        summary = self.summary()
        self.evidence.write("scenario_summary", summary=summary, processed=processed)
        return summary
